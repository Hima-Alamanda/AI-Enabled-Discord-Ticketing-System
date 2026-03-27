import logging
import json
import re
import oci_genai
from typing import List, Dict, Optional, Tuple

log = logging.getLogger("ClarificationEngine")

# CONSTANTS / THRESHOLDS

# Issue understanding confidence below this - clarify
ISSUE_CONFIDENCE_THRESHOLD = 0.45

# KB confidence: if low and issue is also vague - escalate or clarify
KB_LOW_CONFIDENCE_ESCALATION_THRESHOLD = 0.25

# Maximum clarification rounds before auto-escalating
MAX_CLARIFICATION_ROUNDS = 3





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

        # We NEVER want to guess the system UNLESS the KB match is strong or unique.
        if "system_or_application" in missing_slots:
            if kb_confidence in ("high", "medium"):
                log.info("Missing system slot but KB confidence is %s → proceed towards ANSWER", kb_confidence)
                pass
            else:
                log.info("Missing critical 'system_or_application' slot and low KB confidence → CLARIFY")
                return "CLARIFY"

        # Skip if we already have a locked domain or strictly matched system
        is_known_system = bool(issue.get("system") or issue.get("application"))
        
        if is_multi_domain and not is_known_system:
            # Only clarify multi-domain if confidence isn't high enough
            if kb_confidence != "high" and score_gap < 0.12:
                # Get competing domains for logging
                competing = retrieval_result.get("competing_domains", [])
                log.info("Multi-domain ambiguity detected (gap=%.2f) → CLARIFY", score_gap)
                return "CLARIFY"

        if current_stage == S["TROUBLESHOOTING"] and kb_confidence != "low":
            log.info("Stage is TROUBLESHOOTING + KB match → ANSWER")
            return "ANSWER"

        # RELAXED RULES: Only clarify if KB confidence is truly LOW
        if ambiguity_flags and kb_confidence == "low" and current_stage == S["IDENTIFYING"]:
            log.info("Ambiguity flags %s + LOW KB → CLARIFY", ambiguity_flags)
            return "CLARIFY"

        if missing_slots and kb_confidence == "low" and current_stage == S["IDENTIFYING"]:
            log.info("Missing slots %s + LOW KB → CLARIFY", missing_slots)
            return "CLARIFY"

        if kb_confidence == "low" and issue_confidence < KB_LOW_CONFIDENCE_ESCALATION_THRESHOLD:
            log.info("Low KB + low issue confidence → ESCALATE")
            return "ESCALATE"

        # Sane default: if we have any medium/high KB match, or even a low one that isn't totally vague, try an ANSWER
        if kb_confidence in ("high", "medium") or (issue_confidence > 0.5):
            log.info("Sufficient understanding for attempt (issue_conf=%.2f, kb=%s) → ANSWER", issue_confidence, kb_confidence)
            return "ANSWER"

        # Default fallthrough
        log.info("Bottom fallthrough → ANSWER (attempting support first)")
        return "ANSWER"

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
        Now prioritizes Dynamic LLM generation for a more natural, senior engineer feel.
        """
        # 1. TRY DYNAMIC FIRST (Modern "LLM-First" approach)
        dynamic_package = self.generate_dynamic_clarification(issue, retrieval_result, history)
        
        # If dynamic succeeded and is NOT just the generic fallback
        if dynamic_package and dynamic_package.get("question") != "Could you provide more details?":
            return dynamic_package

        # 2. FALLBACK to Rule-Based if Dynamic is vague or failed
        rb_question = self._try_rule_based_question(issue, retrieval_result)
        rb_options = self._try_rule_based_options(issue, retrieval_result)
        
        if rb_question and rb_options:
            log.info("Dynamic clarification was vague; falling back to rule-based logic.")
            return {"question": rb_question, "options": rb_options}
            
        return dynamic_package

    def build_clarification_question(self, issue: dict,
                                      retrieval_result: dict,
                                      history: list = None) -> str:
        """
        Generates a precise, targeted clarification question based on
        what's missing.
        """
        package = self.get_clarification_package(issue, retrieval_result, history)
        return package.get("question", "Could you provide more details?")

    def _try_rule_based_question(self, issue: dict, retrieval_result: dict) -> Optional[str]:
        """Minimal fallback questions for critical missing information."""
        missing_slots = issue.get("missing_slots", [])
        if "system_or_application" in missing_slots:
            return "Which system or application are you experiencing this issue on?"
        if missing_slots:
            return "Could you provide more specific details about this issue?"
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
        """Minimal fallback button logic."""
        competing = retrieval_result.get("competing_domains", [])
        if competing:
            return [self._domain_to_display_name(d) for d in competing] + ["Other"]
        return ["Other", "Standard Support"]

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
   - Good: "To help you with SAP, are you experiencing a login failure or an error within a specific transaction?"
   - Good: "Is this issue limited to Microsoft Teams, or is it affecting your entire internet connection?"
   - Bad: "I found solutions for SAP and Outlook. Which one are you using?"
4. OPTIONS: These will be Discord buttons. Keep them short (max 20 chars). Use technical "Paths" where possible.
   - Example: ["SAP Login Issue", "SAP Transaction Error", "Other"]
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
Symptom: {issue.get('symptom') or 'Generic/Vague'}
Competing Domains Discovered: {", ".join(competing)}

Potential KB Solutions:
{kb_summary}

Missing Information: {", ".join(issue.get('missing_slots', []))}

Generate JSON clarification:"""
        usage_data = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

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


