import re
import json
import logging
import oci_genai
from typing import Optional

log = logging.getLogger("IssueUnderstandingAgent")

# DOMAIN KNOWLEDGE — systems, apps, symptoms, issue types

# Known systems / applications the ITSM supports
KNOWN_SYSTEMS = {
    "windows", "active directory", "ad", "azure ad", "entra id",
    "linux", "macos", "citrix", "vmware",
}

KNOWN_APPLICATIONS = {
    "sap", "sap gui", "sap fiori", "sap hana",
    "outlook", "microsoft outlook", "outlook web",
    "teams", "microsoft teams",
    "vpn", "cisco anyconnect", "anyconnect", "globalprotect",
    "sharepoint", "onedrive", "excel", "word", "powerpoint",
    "oracle", "jira", "servicenow", "salesforce",
    "chrome", "edge", "firefox", "browser",
    "zoom", "slack", "skype",
    "printer", "scanner",
    "data analytics", "data analytics software", "powerbi", "tableau",
}

KNOWN_DEVICES = {
    "laptop", "desktop", "phone", "mobile", "tablet", "ipad",
    "monitor", "keyboard", "mouse", "headset", "docking station",
    "server", "vm", "virtual machine",
}

# Issue-type classification patterns
ISSUE_TYPE_PATTERNS = {
    "access_or_login": [
        r"lock(ed)?\s*(out)?", r"can'?t\s*(log\s*in|login|sign\s*in|access)",
        r"access\s*denied", r"permission\s*denied", r"unauthorized",
        r"authentication\s*fail", r"credential", r"password",
        r"account\s*(disabled|expired|locked|suspended)",
        r"login\s*(fail|error|issue|problem)", r"sign\s*in\s*(fail|error)",
        r"mfa\s*(fail|issue|error|not\s*working)", r"two.?factor",
    ],
    "performance": [
        r"slow", r"lagg?(ing)?", r"freeze", r"frozen", r"hang(ing|s)?",
        r"takes?\s*(too\s*)?long", r"not\s*respond", r"unresponsive",
        r"performance\s*(issue|problem|degraded)",
    ],
    "error_or_crash": [
        r"error", r"crash(ed|ing|es)?", r"blue\s*screen", r"bsod",
        r"exception", r"fail(ed|ure|ing)?", r"not\s*working",
        r"broken", r"stopped?\s*working", r"won'?t\s*(open|start|launch)",
        r"unable\s*to", r"can'?t\s*(open|start|launch|run|use)",
        r"memory", r"out\s*of\s*mem", r"allocation\s*fail",
    ],
    "installation": [
        r"install", r"setup", r"deploy", r"upgrade", r"update",
        r"need\s*(to\s*)?(install|setup|get)", r"how\s*to\s*install",
    ],
    "network_connectivity": [
        r"network", r"internet", r"wifi", r"wi-?fi", r"ethernet",
        r"dns", r"proxy", r"firewall", r"connect(ion|ivity)?",
        r"disconnect", r"no\s*(internet|network|connection)",
    ],
    "email_calendar": [
        r"email", r"mail", r"calendar", r"meeting\s*invite",
        r"inbox", r"mailbox", r"send(ing)?\s*fail",
        r"receiv(e|ing)\s*(fail|error)", r"attachment",
    ],
    "hardware": [
        r"hardware", r"screen", r"display", r"keyboard", r"mouse",
        r"battery", r"charger", r"port", r"usb", r"hdmi",
        r"speaker", r"microphone", r"webcam", r"camera",
    ],
    "data_or_storage": [
        r"storage", r"disk\s*(full|space)", r"quota",
        r"file\s*(missing|deleted|corrupt)", r"data\s*loss",
        r"backup", r"restore",
    ],
}

# Symptom keywords (mapped to canonical symptom names)
SYMPTOM_MAP = {
    "account_locked":    [r"lock(ed)?\s*(out)?", r"account\s*locked"],
    "access_denied":     [r"access\s*denied", r"permission\s*denied", r"unauthorized"],
    "password_issue":    [r"password", r"forgot\s*password", r"password\s*expired"],
    "slow_performance":  [r"slow", r"lagg?(ing)?", r"performance"],
    "crash":             [r"crash", r"blue\s*screen", r"bsod"],
    "not_working":       [r"not\s*working", r"broken", r"stopped?\s*working", r"won'?t"],
    "error_displayed":   [r"error", r"error\s*(code|message)"],
    "cannot_open":       [r"can'?t\s*(open|start|launch)", r"won'?t\s*(open|start|launch)"],
    "disconnected":      [r"disconnect", r"dropped", r"lost\s*connection"],
    "installation_issue":[r"install\s*(fail|error|issue)", r"can'?t\s*install"],
    "memory_issue":      [r"out\s*of\s*memory", r"memory\s*failed", r"allocation\s*failed", r"low\s*memory"],
}

# Patterns that signal generic / ambiguous references
AMBIGUITY_PATTERNS = {
    "generic_account_reference": [r"^my\s*account", r"^account\s*(is\s*)?lock"],
    "generic_login_reference":   [r"^(i\s*)?can'?t\s*(log\s*in|login|sign\s*in)$"],
    "generic_error_reference":   [r"^(i\s*)?(got|have|see)\s*(an?\s*)?error$", r"^error$"],
    "generic_app_reference":     [r"^(the\s*)?(app|application|system)\s*(is\s*)?(not\s*working|broken|slow|crashed)"],
    "generic_it_reference":      [r"^it'?s?\s*(not\s*working|broken|slow|down)"],
    "vague_complaint":           [r"^(something|things?)\s*(is\s*)?(wrong|broken|off|weird)"],
}

# Patterns for situational context (actions, environment, business urgency)
SITUATIONAL_CONTEXT_PATTERNS = {
    "action_attempted": [
        r"after\s+(?:i\s+)?reset\s+(?:my\s+)?password", r"password\s+reset",
        r"after\s+restart", r"reboot", r"cleared\s+cache", r"tried\s+to\s+login",
        r"incorrect\s+password", r"too\s+many\s+attempts",
    ],
    "environmental_context": [
        r"new\s+laptop", r"new\s+system", r"home\s+network", r"public\s+wifi",
        r"in\s+(?:the\s+)?browser", r"web\s+version", r"mobile\s+app",
        r"citrix", r"remote\s+desktop", r"rdp",
    ],
    "business_context": [
        r"during\s+(?:a\s+)?meeting", r"urgent", r"deadline",
        r"presentation", r"on\s+a\s+call", r"critical\s+process",
    ],
}

# Short clarification response patterns — indicates user is answering a
# clarification question, not starting a new issue
CLARIFICATION_RESPONSE_PATTERNS = [
    # Single-word app/system names
    r"^(windows|sap|outlook|vpn|teams|sharepoint|onedrive|excel|"
    r"chrome|edge|firefox|oracle|jira|salesforce|citrix|zoom|slack|"
    r"printer|laptop|desktop|phone|mobile|email|browser|active\s*directory)$",
    # Short responses like "my laptop", "the VPN", "SAP GUI"
    r"^(my|the|it'?s?|its?)\s+(windows|sap|outlook|vpn|teams|laptop|"
    r"desktop|email|phone|browser|printer)(\s+\w+)?$",
    # Error code patterns
    r"^(error\s*)?(code\s*)?[A-Z0-9\-]{3,15}$",
    # "it says ..." / "the error is ..."
    r"^(it\s+says?|the\s+error\s+(is|says?|reads?))\s+",
    # "error code 500", "code 0x800..."
    r"^(error\s*)?code\s*[:=]?\s*\w+",
    # Multi-word symptom answers (e.g. "keeps disconnecting", "can't connect at all")
    r"^([a-z']+\s+){1,5}[a-z']+$",
]


# MAIN CLASS

class IssueUnderstandingAgent:
    """
    Extracts structured issue data from user messages and detects ambiguity.
    All methods are stateless — state is passed in / out as dicts.
    """

    # Public: extract_issue_fields

    def extract_issue_fields(self, message: str, snapshot: dict = None, history: list = None) -> dict:
        """
        Analyze the user message and return a structured issue dict.
        Combines deterministic regex for speed with semantic LLM for flexibility.
        """
        msg = message.strip()
        msg_low = msg.lower()
        snapshot = snapshot or {}

        # 1. Start with high-speed deterministic extraction
        issue = {
            "issue_type": self._detect_issue_type(msg_low),
            "symptom": self._detect_symptom(msg_low),
            "system": self._extract_from_set(msg_low, KNOWN_SYSTEMS),
            "application": self._extract_from_set(msg_low, KNOWN_APPLICATIONS),
            "device": self._extract_from_set(msg_low, KNOWN_DEVICES),
            "error_code": self._extract_error_code(msg),
            "action_attempted": self._detect_pattern(msg_low, SITUATIONAL_CONTEXT_PATTERNS["action_attempted"]),
            "environmental_context": self._detect_pattern(msg_low, SITUATIONAL_CONTEXT_PATTERNS["environmental_context"]),
            "business_context": self._detect_pattern(msg_low, SITUATIONAL_CONTEXT_PATTERNS["business_context"]),
            "ambiguity_flags": self._detect_ambiguity(msg_low),
            "missing_slots": [],
            "confidence": 0.0,
            "raw_message": msg,
        }

        # 2. Compute initial confidence
        issue["missing_slots"] = self._detect_missing_slots(issue)
        issue["confidence"] = self._calculate_confidence(issue)

        # 3. If confidence is low, trigger Semantic Overlay (Phase 2: Flexibility)
        if issue["confidence"] < 0.65 or "system_or_application" in issue["missing_slots"]:
            log.info("Rigid confidence low (%.2f). Using Semantic Extraction...", issue["confidence"])
            semantic = self.semantic_extract_issue_fields(msg, history)
            if semantic:
                # Overlay semantic findings onto the structured issue
                for key in ["issue_type", "symptom", "system", "application", "error_code"]:
                    if semantic.get(key) and not issue.get(key):
                        issue[key] = semantic[key]
                
                # Re-calculate missing slots and confidence
                issue["missing_slots"] = self._detect_missing_slots(issue)
                issue["confidence"] = self._calculate_confidence(issue)
                log.info("Semantic overlay complete. New confidence: %.2f", issue["confidence"])

        return issue

    # Public: semantic_extract_issue_fields (LLM Powered)

    def semantic_extract_issue_fields(self, message: str, history: list = None) -> dict:
        """
        Uses OCI GenAI to semantically extract issue fields.
        """
        history_context = ""
        if history:
            for msg in history[-4:]:
                role = "User" if msg['role'] == 'user' else "AI"
                history_context += f"{role}: {msg['content'][:200]}\n"

        system_prompt = """You are an Issue Extraction Agent. 
Extract technical support details into the following JSON format:
{
  "issue_type": "access_or_login | performance | error_or_crash | installation | network_connectivity | email_calendar | hardware | data_or_storage | other",
  "symptom": "short canonical description of the problem",
  "system": "the name of the system or application (e.g. SAP, Windows, VPN, Outlook, Ticket Website)",
  "error_code": "any specific error codes detected",
  "missing_slots": ["list any critical missing info like 'system' if not clear"]
}

RULES:
- If you see a screenshot description about ticket quotas/limits, the system is "Ticketing Application".
- Be specific. If the symptom is vague like 'not working', try to find a better description from context.
- Return ONLY JSON.
"""
        prompt = f"{history_context}\nCurrent Message: {message}\n\nExtract fields:"

        try:
            raw = oci_genai.get_chat_response(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.0
            )
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                extracted = json.loads(match.group())
                # Default empty lists for consistency
                if "missing_slots" not in extracted: extracted["missing_slots"] = []
                log.info("Semantic extraction successful: %s", extracted.get("system"))
                return extracted
        except Exception as e:
            log.error("Semantic extraction failed: %s", e)
        
        return {}


    # Public: merge_issue_context

    def merge_issue_context(self, current_fields: dict, snapshot: dict) -> dict:
        """
        Merge previously known context from the issue snapshot into current
        fields.  Does NOT overwrite strong prior context with weaker guesses.

        Priority rules:
          - If current field is not None → keep it (user just provided it).
          - If current field is None but snapshot has it → inherit from snapshot.
          - After merge, recalculate missing_slots, ambiguity_flags, confidence.
        """
        if not snapshot:
            return current_fields

        merged = dict(current_fields)

        # Fields that can be inherited from snapshot
        inheritable = {
            "system":      snapshot.get("locked_domain") or snapshot.get("system"),
            "application": snapshot.get("locked_domain") or snapshot.get("application"),
            "device":      snapshot.get("clarification_context", {}).get("device")
                           or snapshot.get("device"),
            "error_code":  snapshot.get("clarification_context", {}).get("error_code")
                           or snapshot.get("error_code"),
            "issue_type":  snapshot.get("clarification_context", {}).get("issue_type")
                           or snapshot.get("issue_type"),
            "symptom":     snapshot.get("locked_symptom") or snapshot.get("symptom"),
            "action_attempted": snapshot.get("clarification_context", {}).get("action_attempted")
                           or snapshot.get("action_attempted"),
            "environmental_context": snapshot.get("clarification_context", {}).get("environmental_context")
                           or snapshot.get("environmental_context"),
        }

        for field_name, snapshot_value in inheritable.items():
            if merged.get(field_name) is None and snapshot_value:
                merged[field_name] = snapshot_value
                log.debug("Inherited %s=%s from snapshot", field_name, snapshot_value)

        # Recalculate dependent fields
        merged["missing_slots"] = self._detect_missing_slots(merged)
        merged["ambiguity_flags"] = self._detect_ambiguity(
            merged.get("raw_message", "").lower()
        )
        # If we inherited system/app, remove corresponding ambiguity flags
        if merged.get("system") or merged.get("application"):
            merged["ambiguity_flags"] = [
                f for f in merged["ambiguity_flags"]
                if f not in ("generic_account_reference", "generic_login_reference",
                             "generic_app_reference", "generic_it_reference")
            ]
        merged["confidence"] = self._calculate_confidence(merged)

        log.info(
            "After merge: system=%s app=%s missing=%s confidence=%.2f",
            merged["system"], merged["application"],
            merged["missing_slots"], merged["confidence"],
        )
        return merged

    # Public: is_clarification_response

    def is_clarification_response(self, message: str, snapshot: dict) -> bool:
        """
        Returns True if the message looks like a short answer to a
        clarification question (e.g. "Windows", "SAP", "error code 500").
        """
        if not snapshot:
            return False

        # Must be in clarification state
        clarification_status = snapshot.get("clarification_status")
        if clarification_status != "AWAITING_CLARIFICATION":
            return False

        msg_low = message.strip().lower()

        # Heuristic short-circuit for social intents during clarification
        # We don't want a "hi" to be treated as a technical symptom
        greetings = ["hi", "hii", "hello", "hey", "how are you", "what's up", "good morning", "good afternoon"]
        if any(g == msg_low or msg_low.startswith(g + " ") for g in greetings):
            log.debug("Social greeting detected during clarification — NOT a technical response")
            return False

        # Check against known patterns
        for pattern in CLARIFICATION_RESPONSE_PATTERNS:
            if re.match(pattern, msg_low, re.IGNORECASE):
                log.info("Message matches clarification response pattern: '%s'", msg_low)
                return True

        # Also match if the message is ≤ 5 words (very short)
        if len(msg_low.split()) <= 5:
            # Check if it mentions any known system/app/device
            if (self._extract_from_set(msg_low, KNOWN_SYSTEMS)
                    or self._extract_from_set(msg_low, KNOWN_APPLICATIONS)
                    or self._extract_from_set(msg_low, KNOWN_DEVICES)):
                log.info("Short message with known entity — treating as clarification response")
                return True

        return False

    # Private: detection helpers

    @staticmethod
    def _detect_issue_type(msg_low: str) -> Optional[str]:
        for issue_type, patterns in ISSUE_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, msg_low):
                    return issue_type
        return None

    @staticmethod
    def _detect_symptom(msg_low: str) -> Optional[str]:
        for symptom_name, patterns in SYMPTOM_MAP.items():
            for pattern in patterns:
                if re.search(pattern, msg_low):
                    return symptom_name
        return None

    @staticmethod
    def _extract_from_set(msg_low: str, known_set: set) -> Optional[str]:
        """Finds the longest matching item from the known set in the message."""
        matches = []
        for item in known_set:
            # Use word-boundary aware matching for items > 2 chars
            if len(item) <= 2:
                # Very short items (e.g. "ad") need word boundary
                if re.search(r'\b' + re.escape(item) + r'\b', msg_low):
                    matches.append(item)
            else:
                if item in msg_low:
                    matches.append(item)
        if not matches:
            return None
        # Return the longest match (more specific)
        return max(matches, key=len)

    @staticmethod
    def _extract_error_code(message: str) -> Optional[str]:
        """Extracts error codes like 0x80070005, ERR_1234, HTTP 500, etc."""
        patterns = [
            r'0x[0-9A-Fa-f]{4,}',           # Hex codes
            r'[A-Z]{2,}_\d{3,}',             # e.g. ERR_1234
            r'error\s*(?:code\s*)?[:=]?\s*(\w{3,})',  # "error code: XYZ"
            r'(?:HTTP|http)\s*(\d{3})',       # HTTP status codes
            r'\b\d{3,5}\b(?=\s*error)',       # "500 error"
        ]
        for p in patterns:
            m = re.search(p, message, re.IGNORECASE)
            if m:
                return m.group(0) if not m.groups() else m.group(1)
        return None

    @staticmethod
    def _detect_pattern(msg_low: str, patterns: list) -> Optional[str]:
        """Returns the first matching pattern string or None."""
        for p in patterns:
            if re.search(p, msg_low):
                # Return a cleaned up version of the match or the pattern itself
                return p.replace(r"\s+", " ").replace(r"(?:i\s+)?", "").replace(r"(?:my\s+)?", "")
        return None

    @staticmethod
    def _detect_ambiguity(msg_low: str) -> list:
        flags = []
        for flag_name, patterns in AMBIGUITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, msg_low):
                    flags.append(flag_name)
                    break  # one match per flag is enough
        return flags

    @staticmethod
    def _detect_missing_slots(issue: dict) -> list:
        """
        Determines which critical slots are missing for safe troubleshooting.
        """
        missing = []

        issue_type = issue.get("issue_type")

        # System/application is almost always needed
        if not issue.get("system") and not issue.get("application"):
            # Exception: if issue_type clearly implies a system (e.g. network→network)
            # we still want to know which specific system/app
            missing.append("system_or_application")

        # For error issues, error code/detail is helpful ONLY if symptom is still vague
        if issue_type in ("error_or_crash",) and not issue.get("error_code"):
            # If we already have a specific symptom (like memory_issue), don't flag as missing error_detail
            if issue.get("symptom") in (None, "not_working", "error_displayed"):
                missing.append("error_detail")

        # For performance issues, we want to know what is slow
        if issue_type == "performance":
            if not issue.get("application") and not issue.get("system"):
                missing.append("affected_component")

        return missing

    @staticmethod
    def _calculate_confidence(issue: dict) -> float:
        """
        Calculates a 0.0–1.0 confidence score based on how well the issue
        is understood.
        """
        score = 0.0

        # Base: having an issue type gives 0.15
        if issue.get("issue_type"):
            score += 0.15

        # Having a symptom gives 0.15
        if issue.get("symptom"):
            score += 0.15

        # Having system OR application gives 0.30
        if issue.get("system") or issue.get("application"):
            score += 0.30

        # Having BOTH system and application gives extra 0.10
        if issue.get("system") and issue.get("application"):
            score += 0.10

        # Having a device gives 0.05
        if issue.get("device"):
            score += 0.05

        # Having an error code gives 0.15
        if issue.get("error_code"):
            score += 0.15

        # Penalty: each ambiguity flag reduces confidence by 0.08
        ambiguity_count = len(issue.get("ambiguity_flags", []))
        score -= ambiguity_count * 0.08

        # Penalty: each missing slot reduces confidence by 0.12
        missing_count = len(issue.get("missing_slots", []))
        score -= missing_count * 0.12

        # Clamp
        return round(max(0.0, min(1.0, score)), 2)
