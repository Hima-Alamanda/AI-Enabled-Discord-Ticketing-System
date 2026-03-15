"""
Clarification Engine — decides when to clarify and generates targeted questions.

Responsibilities:
  • Determines if the current issue understanding warrants clarification,
    answering, or escalation (CLARIFY / ANSWER / ESCALATE).
  • Generates precise, narrowing clarification questions based on what
    is specifically missing (not generic "can you provide more details").
  • Builds clarification option lists from candidate domains.
  • Stores clarification context in the snapshot for session continuity.

This engine uses NO LLM calls — it is fully rule-based for speed and
determinism.
"""

import logging
import json
import re
import oci_genai
from typing import List, Dict, Optional, Tuple

log = logging.getLogger("ClarificationEngine")

# CONSTANTS / THRESHOLDS

# Issue understanding confidence below this → clarify
ISSUE_CONFIDENCE_THRESHOLD = 0.45

# KB confidence: if low and issue is also vague → escalate or clarify
KB_LOW_CONFIDENCE_ESCALATION_THRESHOLD = 0.25

# Maximum clarification rounds before auto-escalating
MAX_CLARIFICATION_ROUNDS = 3

# CLARIFICATION QUESTION TEMPLATES (by missing slot)

SLOT_QUESTIONS = {
    "system_or_application": {
        "default": "Which system or application is affected?",
        "access_or_login": (
            "Which account are you trying to access: "
            "**Windows login**, **SAP**, **VPN**, **Outlook**, or another application?"
        ),
        "performance": (
            "Which application or system is running slow? "
            "For example: **SAP**, **Outlook**, **your laptop**, **VPN**, or **a browser**?"
        ),
        "error_or_crash": (
            "Which application is showing the error or crashing? "
            "For example: **SAP**, **Outlook**, **Teams**, **a browser**, or another application?"
        ),
        "network_connectivity": (
            "Is this a **VPN connection issue**, **Wi-Fi/Ethernet** problem, "
            "or affecting a specific **application**?"
        ),
        "email_calendar": (
            "Is this related to **Outlook desktop**, **Outlook Web (OWA)**, "
            "or another email application?"
        ),
        "installation": (
            "Which software are you trying to install? "
            "Please share the application name."
        ),
    },
    "error_detail": {
        "default": (
            "What is the exact error message or error code you're seeing? "
            "This will help me find the right solution."
        ),
    },
    "affected_component": {
        "default": (
            "Is this happening on your **laptop/desktop**, inside a **browser**, "
            "within a **business application (SAP, Oracle, etc.)**, or on your **VPN**?"
        ),
    },
}

# Additional narrowing questions for known applications with vague symptoms
APP_NARROWING_QUESTIONS = {
    "sap": (
        "To help you with SAP, could you tell me more specifically what's happening? "
        "For example:\n"
        "• **Login/access issue** (can't log in, account locked)\n"
        "• **Transaction error** (specific error in a transaction)\n"
        "• **GUI not launching** (SAP GUI won't open)\n"
        "• **Performance issue** (SAP is slow or freezing)"
    ),
    "outlook": (
        "To help you with Outlook, could you describe what's happening more specifically?\n"
        "• **Can't open/launch Outlook**\n"
        "• **Sending/receiving errors**\n"
        "• **Mailbox full or storage issue**\n"
        "• **Calendar or meeting problems**\n"
        "• **Performance (slow, freezing)**"
    ),
    "vpn": (
        "To help with VPN, could you tell me:\n"
        "• **Can't connect at all**\n"
        "• **Keeps disconnecting**\n"
        "• **Connected but can't access resources**\n"
        "• **Slow when connected**\n"
        "• **Getting a specific error message** (if so, what does it say?)"
    ),
    "teams": (
        "I can help with Microsoft Teams. What specifically is failing?\n"
        "• **Audio/video issue** (mic/camera not working)\n"
        "• **Meeting connection** (can't join or host)\n"
        "• **Sign-in error** (modern auth or cache issue)\n"
        "• **Screen sharing** (blocked or black screen)\n"
        "• **Chat/Presence** (status not updating)"
    ),
    "printer": (
        "To troubleshoot your printer, please select the symptom:\n"
        "• **Paper jam or hardware error**\n"
        "• **Offline / can't find printer**\n"
        "• **Print quality / streaks**\n"
        "• **Blank pages / stuck in queue**"
    ),
    "hardware": (
        "I see this is a hardware-related issue. What is affected?\n"
        "• **Blue screen / system crash**\n"
        "• **Battery / power won't start**\n"
        "• **Docking station / monitors**\n"
        "• **Keyboard or mouse unresponsive**"
    ),
    "mfa": (
        "For Multi-Factor Authentication (MFA) issues, please specify:\n"
        "• **Not receiving push / SMS**\n"
        "• **New phone / reset needed**\n"
        "• **App won't open / error code**\n"
        "• **Bypass code request**"
    ),
}


# MAIN CLASS

class ClarificationEngine:
    """
    Rule-based engine that decides ANSWER/CLARIFY/ESCALATE and generates
    targeted clarification questions.
    """

    # Public: decide_next_step

    def decide_next_step(self, issue: dict, retrieval_result: dict,
                         snapshot: dict) -> str:
        """
        Decides the next action: "ANSWER", "CLARIFY", or "ESCALATE".

        Parameters
        ----------
        issue : dict
            Structured issue fields from IssueUnderstandingAgent.
        retrieval_result : dict
            Multi-candidate analysis from RetrievalManager.
        snapshot : dict
            Current issue snapshot for session context.

        Returns
        -------
        str — "ANSWER", "CLARIFY", or "ESCALATE"
        """
        missing_slots = issue.get("missing_slots", [])
        ambiguity_flags = issue.get("ambiguity_flags", [])
        issue_confidence = issue.get("confidence", 0.0)
        kb_confidence = retrieval_result.get("kb_confidence", "low")
        is_multi_domain = retrieval_result.get("is_multi_domain", False)
        top_distance = retrieval_result.get("top_distance")
        score_gap = retrieval_result.get("score_gap", 0)
        candidates = retrieval_result.get("candidates", [])

        # Stage Constants from ContinuityAgent
        from agents.continuity_agent import ConversationState
        S = ConversationState.STAGES
        current_stage = snapshot.get("stage", S["IDENTIFYING"])

        # Track clarification rounds to avoid infinite loops
        clarification_rounds = snapshot.get("clarification_rounds", 0)
        if clarification_rounds >= MAX_CLARIFICATION_ROUNDS:
            log.info("Max clarification rounds (%d) reached → ESCALATE",
                     MAX_CLARIFICATION_ROUNDS)
            return "ESCALATE"

        # If we don't have it in the KB, asking more questions is a waste of time.
        if not candidates:
            log.info("No KB candidates found for this query → ESCALATE (avoiding interrogation loop)")
            return "ESCALATE"

        # We NEVER want to guess the system UNLESS the KB match is exceptionally strong.
        if "system_or_application" in missing_slots:
            if kb_confidence == "high":
                log.info("Missing system slot but KB confidence is HIGH and unique → proceed towards ANSWER")
                # Do not return CLARIFY here, let it fall through to Rule 7
                pass
            else:
                log.info("Missing critical 'system_or_application' slot → CLARIFY")
                return "CLARIFY"

        # Skip if we already have a locked domain or strictly matched system
        is_known_system = bool(issue.get("system") or issue.get("application"))
        
        if is_multi_domain and not is_known_system:
            # Even if gap is okay, if it's multiple domains we clarify for safety
            # unless the confidence is exceptionally high and unambiguous.
            if kb_confidence != "high" or score_gap < 0.15:
                # Get competing domains for logging
                competing = retrieval_result.get("competing_domains", [])
                log.info("Multi-domain ambiguity detected (competing: %s) → CLARIFY", competing)
                return "CLARIFY"

        if current_stage == S["TROUBLESHOOTING"] and kb_confidence != "low":
            log.info("Stage is TROUBLESHOOTING + KB match → ANSWER")
            return "ANSWER"

        if ambiguity_flags and kb_confidence != "high" and current_stage == S["IDENTIFYING"]:
            log.info("Ambiguity flags %s + IDENTIFYING → CLARIFY", ambiguity_flags)
            return "CLARIFY"

        if missing_slots and kb_confidence != "high" and current_stage == S["IDENTIFYING"]:
            log.info("Missing slots %s + IDENTIFYING → CLARIFY", missing_slots)
            return "CLARIFY"

        if kb_confidence == "low" and issue_confidence < KB_LOW_CONFIDENCE_ESCALATION_THRESHOLD:
            log.info("Low KB + low issue confidence → ESCALATE")
            return "ESCALATE"

        # Requires system/app to be known (verified by Rule 2)
        if kb_confidence in ("high", "medium") or (issue_confidence > 0.7 and kb_confidence != "low"):
            log.info("Sufficient understanding (issue_conf=%s) + %s KB confidence → ANSWER", issue_confidence, kb_confidence)
            return "ANSWER"

        if current_stage == S["TROUBLESHOOTING"] or clarification_rounds >= 2:
            log.info("Already TROUBLESHOOTING or multiple rounds reached with low KB confidence → ESCALATE")
            return "ESCALATE"

        # Default fallthrough
        log.info("Default fallthrough (confidence=%s) → CLARIFY", kb_confidence)
        return "CLARIFY"

    # Public: needs_clarification (convenience)

    def needs_clarification(self, issue: dict, retrieval_result: dict,
                            snapshot: dict) -> bool:   
        """Convenience method: returns True if decision is CLARIFY."""
        return self.decide_next_step(issue, retrieval_result, snapshot) == "CLARIFY"

    # Public: build_clarification_question

    def get_clarification_package(self, issue: dict,
                                  retrieval_result: dict,
                                  history: list = None) -> dict:
        """
        Returns a dictionary containing both 'question' and 'options'.
        Tries rule-based logic first, then falls back to dynamic LLM.
        """
        # Try Rule-Based
        rb_question = self._try_rule_based_question(issue, retrieval_result)
        rb_options = self._try_rule_based_options(issue, retrieval_result)
        
        if rb_question and rb_options:
            return {"question": rb_question, "options": rb_options}
            
        # Fallback to Dynamic
        return self.generate_dynamic_clarification(issue, retrieval_result, history)

    def build_clarification_question(self, issue: dict,
                                      retrieval_result: dict,
                                      history: list = None) -> str:
        """
        Generates a precise, targeted clarification question based on
        what's missing.
        """
        # Note: In chatbot_engine, we usually call get_clarification_package directly
        # for efficiency, but we keep these for backward compatibility.
        package = self.get_clarification_package(issue, retrieval_result, history)
        return package.get("question", "Could you provide more details?")

    def _try_rule_based_question(self, issue: dict, retrieval_result: dict) -> Optional[str]:
        """Existing rule-based logic for specific apps."""
        missing_slots = issue.get("missing_slots", [])
        issue_type = issue.get("issue_type")
        application = issue.get("application")
        system = issue.get("system")
        symptom = issue.get("symptom")
        competing_domains = retrieval_result.get("competing_domains", [])

        error_code = issue.get("error_code")
        if error_code and (not application and not system):
            return (
                f"I detected error code **{error_code}**. "
                f"Which application or system were you using when this appeared?"
            )

        # ONLY if we still have ambiguous flags or very generic symptom
        is_vague = not symptom or symptom in ("not_working", "error_displayed")
        
        if (application or system) and (not missing_slots or is_vague):
            known = (application or system or "").lower()
            for app_key, question in APP_NARROWING_QUESTIONS.items():
                if app_key in known:
                    # Logic check: if user already provided one of the bullet points, don't ask again
                    if symptom and any(kw in symptom.lower() for kw in ["disconnect", "connect", "access", "slow", "error"]):
                        # They already gave a specific symptom, skip narrowing question
                        continue
                    return question
            # No specific rule-based narrowing for this app -> Fall back to dynamic LLM
            return None

        ifCompeting = retrieval_result.get("competing_domains", [])
        if ifCompeting and len(ifCompeting) > 1 and not (application or system):
            domain_list = self._format_domain_list(ifCompeting)
            return f"I see possible matches for {domain_list}. Which one are you having trouble with?"

        if missing_slots:
            slot = missing_slots[0]
            # Custom questions based on issue_type
            if slot == "system_or_application":
                if issue_type == "access_or_login":
                    return SLOT_QUESTIONS["system_or_application"]["access_or_login"]
                return SLOT_QUESTIONS["system_or_application"]["default"]
            
            if slot == "error_detail":
                # Removed hardcoded default question to allow dynamic fallback
                return None
                
            if slot == "affected_component":
                return SLOT_QUESTIONS["affected_component"]["default"]

        return None

    # Public: build_clarification_options

    def build_clarification_options(self, issue: dict,
                                     retrieval_result: dict,
                                     history: list = None) -> list:
        """
        Builds a list of option strings for the clarification question.
        """
        package = self.get_clarification_package(issue, retrieval_result, history)
        return package.get("options", ["Other"])

    def _try_rule_based_options(self, issue: dict, retrieval_result: dict) -> Optional[list]:
        """Existing rule-based button logic."""
        options = []
        missing_slots = issue.get("missing_slots", [])
        competing = retrieval_result.get("competing_domains", [])
        application = issue.get("application")
        system = issue.get("system")
        issue_type = issue.get("issue_type")

        # Determine target slot the same way build_clarification_question does
        target_slot = None
        if missing_slots:
            target_slot = missing_slots[0]

        is_vague = not issue.get("symptom") or issue.get("symptom") in ("not_working", "error_displayed")
        if (application or system) and (not missing_slots or is_vague):
            # Narrowing down symptom for a known app
            known_app = (application or system).lower()
            for app_key, question in APP_NARROWING_QUESTIONS.items():
                if app_key in known_app:
                    import re
                    bullets = re.findall(r'•\s*\*\*?([^*]+)\*\*?', question)
                    if bullets:
                        options.extend([b.strip() for b in bullets])
                    break

        if target_slot == "system_or_application":
            # Suggest competing domains from KB first
            if competing:
                for domain in competing:
                    options.append(self._domain_to_display_name(domain))
            
            # Pad with common apps ONLY if no other context exists at all
            if not options and not (application or system):
                for d in ["Windows login", "SAP", "VPN", "Outlook"]:
                    options.append(d)

        elif target_slot == "error_detail":
            # Removed hardcoded buttons to force dynamic AI-based options
            return None

        elif target_slot == "affected_component":
            options.extend(["Internal Network", "External Website", "Physical Hardware"])

        if not options and competing and len(competing) > 1:
            for domain in competing:
                options.append(self._domain_to_display_name(domain))

        if not options and issue.get("error_code"):
            options.extend(["Technical troubleshooting", "Permissions check", "System check"])

        # Always add "Other" as last option if we have candidates
        return options if options else None

    # Public: generate_dynamic_clarification (The Universal Brain)

    def generate_dynamic_clarification(self, issue: dict, retrieval_result: dict, history: list = None) -> dict:
        """
        Uses LLM to generate targeted questions and buttons based on KB candidates
        and user context. This makes the bot "Universal".
        """
        candidates = retrieval_result.get("candidates", [])[:3]
        kb_summary = ""
        competing = retrieval_result.get("competing_domains", [])
        
        for i, c in enumerate(candidates):
            domain_name = self._domain_to_display_name(c.get('_domain', 'unknown'))
            kb_summary += f"Option {i+1} ({domain_name}): {c.get('title', 'Unknown Solution')}\n"

        history_context = ""
        if history:
            for msg in history[-3:]:
                role = "User" if msg['role'] == 'user' else "Assistant"
                history_context += f"{role}: {msg['content'][:150]}\n"

        system_prompt = """SYSTEM: You are a Senior Support Engineer.
The user's query is ambiguous. Your job is to generate a helpful question and a set of 3-5 buttons to narrow down the issue.

RULES:
1. QUESTION: Be brief, professional, and DIRECT. Sound like an engineer who is narrowing down the problem.
2. NO NARRATION: NEVER say "I found solutions for...", "I checked the Knowledge Base", or "I found matches."
3. EXAMPLES: 
   - Good: "Which system is affected: SAP or Outlook?"
   - Bad: "I found solutions for SAP and Outlook. Which one are you using?"
4. OPTIONS: These will be Discord buttons. Keep them short (max 20 chars).
5. TARGET: Help the user identify the correct technical path.

Return ONLY JSON:
{
  "question": "Which specific system are you experiencing this issue on?",
  "options": ["System A", "System B", "Other"]
}
"""
        prompt = f"""
{history_context}
User Issue: {issue.get('raw_message', 'Unknown')}
Identified System: {issue.get('system') or issue.get('application') or 'Unknown'}
Competing Domains Discovered: {", ".join(competing)}

Potential KB Solutions:
{kb_summary}

Generate JSON clarification:"""

        try:
            # We use a cached response if we already generated it in this turn
            # (In a real production environment, you'd store this in the retrieval_result or snapshot)
            raw = oci_genai.get_chat_response(prompt=prompt, system_prompt=system_prompt, temperature=0.0)
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                log.info("Dynamic clarification generated: %s", data.get("question"))
                return data
        except Exception as e:
            log.error("Dynamic clarification failed: %s", e)

        return {
            "question": "Could you provide more details about the issue you're experiencing?",
            "options": ["Other"]
        }

    # Public: update_snapshot_with_clarification

    @staticmethod
    def update_snapshot_with_clarification(snapshot: dict, issue: dict,
                                            retrieval_result: dict,
                                            question: str,
                                            options: list) -> dict:
        """
        Updates the issue snapshot with clarification state for session
        continuity.
        """
        snapshot["clarification_status"] = "AWAITING_CLARIFICATION"
        snapshot["clarification_question"] = question
        snapshot["clarification_options"] = options
        snapshot["missing_slots"] = issue.get("missing_slots", [])
        snapshot["ambiguity_flags"] = issue.get("ambiguity_flags", [])
        snapshot["candidate_topics"] = retrieval_result.get("competing_domains", [])
        snapshot["issue_type"] = issue.get("issue_type")
        snapshot["symptom"] = issue.get("symptom")
        snapshot["clarification_rounds"] = snapshot.get("clarification_rounds", 0) + 1

        # Store current interpretation for context carry-forward
        snapshot["clarification_context"] = {
            "issue_type": issue.get("issue_type"),
            "symptom": issue.get("symptom"),
            "system": issue.get("system"),
            "application": issue.get("application"),
            "device": issue.get("device"),
            "error_code": issue.get("error_code"),
        }

        log.info(
            "Snapshot updated for clarification: status=%s round=%d question='%s'",
            snapshot["clarification_status"],
            snapshot["clarification_rounds"],
            question[:80],
        )
        return snapshot

    # Public: process_clarification_response

    def process_clarification_response(self, message: str,
                                        snapshot: dict) -> dict:
        """
        Processes a clarification response from the user.
        Normalizes the response into canonical values if possible.
        Updates the snapshot with the newly provided information and
        locks the context for the TROUBLESHOOTING stage.
        """
        msg_low = message.strip().lower()

        # Import here to avoid circular imports at module level
        from agents.issue_understanding_agent import (
            KNOWN_SYSTEMS, KNOWN_APPLICATIONS, KNOWN_DEVICES,
        )

        found_system = None
        found_app = None
        found_sym = None
        found_err = None

        # Check if user provided/selected a known system
        for sys_name in KNOWN_SYSTEMS:
            if sys_name in msg_low:
                found_system = sys_name
                break

        # Check if user provided/selected an application
        for app_name in KNOWN_APPLICATIONS:
            if app_name in msg_low:
                found_app = app_name
                break

        # Check for error codes
        import re
        error_patterns = [
            r'0x[0-9A-Fa-f]{4,}',
            r'[A-Z]{2,}_\d{3,}',
            r'error\s*(?:code\s*)?[:=]?\s*(\w{3,})',
        ]
        for p in error_patterns:
            m = re.search(p, message, re.IGNORECASE)
            if m:
                found_err = m.group(0)
                break

        # This handles button clicks that map to template strings
        last_options = snapshot.get("clarification_options", [])
        for opt in last_options:
            if opt.lower() == msg_low:
                found_sym = opt.lower()
                break
        
        if not found_sym:
            found_sym = message if len(message.split()) < 10 else "complex_symptom"

        if found_system: snapshot["system"] = found_system
        if found_app:    snapshot["application"] = found_app
        if found_sym:    snapshot["symptom"] = found_sym
        if found_err:    snapshot["error_code"] = found_err

        if found_app:
            snapshot["locked_domain"] = found_app
        elif found_system:
            snapshot["locked_domain"] = found_system
        
        snapshot["locked_symptom"] = found_sym

        # Clear awaiting state
        snapshot["clarification_status"] = "RESOLVED"
        
        # Remove slots from missing list
        missing = snapshot.get("missing_slots", [])
        if found_system or found_app:
            missing = [s for s in missing if s != "system_or_application"]
        if found_err:
            missing = [s for s in missing if s != "error_detail"]
        snapshot["missing_slots"] = missing

        log.info(
            "Clarification response processed. Canonical results: system=%s app=%s symptom=%s err=%s. Domain LOCKED.",
            found_system, found_app, found_sym, found_err
        )
        return snapshot

    # Private helpers

    @staticmethod
    def _format_domain_list(domains: list) -> str:
        """Formats domain names into a readable list."""
        if not domains:
            return ""
        display_names = []
        for d in domains:
            name = ClarificationEngine._domain_to_display_name(d)
            display_names.append(f"**{name}**")
        if len(display_names) == 1:
            return display_names[0]
        return ", ".join(display_names[:-1]) + f" and {display_names[-1]}"

    @staticmethod
    def _domain_to_display_name(domain: str) -> str:
        """Converts a domain key to a user-friendly display name."""
        display_map = {
            "windows": "Windows",
            "sap": "SAP",
            "outlook": "Outlook / Email",
            "vpn": "VPN",
            "teams": "Microsoft Teams",
            "sharepoint": "SharePoint / OneDrive",
            "network": "Network",
            "hardware": "Hardware",
            "oracle": "Oracle",
            "browser": "Browser",
            "office": "Microsoft Office",
            "citrix": "Citrix",
            "storage": "Storage / File Server",
            "unknown": "Other",
        }
        return display_map.get(domain, domain.title())


