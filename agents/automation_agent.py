"""
Automation Agent — detects and executes demo-safe automation actions.

Responsibilities:
  • Detects automation-eligible support requests via keyword matching.
  • Classifies actions as auto-execute (read-only) or confirmation-required
    (system-changing).
  • Executes simulated/mock automation functions.
  • Returns structured results for chatbot_engine to present to the user.
  • Manages the AWAITING_AUTOMATION_CONFIRM state lifecycle.

All actions in Phase 5A are MOCK (simulated).  To add real APIs later,
replace only the _mock_* methods — no other files need to change.
"""

import logging
import time
from datetime import datetime

log = logging.getLogger("AutomationAgent")

# CONSTANTS

# Actions that change system state → require user confirmation
CONFIRMATION_REQUIRED = {"account_unlock", "password_reset"}

# Actions that are read-only → auto-execute immediately
AUTO_EXECUTE = {"software_check"}

# Affirmative / negative responses for confirmation handling
AFFIRMATIVE_WORDS = {"yes", "yeah", "yep", "sure", "ok", "okay", "go ahead",
                     "proceed", "do it", "please", "confirm", "y"}
NEGATIVE_WORDS = {"no", "nah", "nope", "cancel", "don't", "dont", "stop",
                  "never mind", "nevermind", "skip", "n"}

# MOCK SOFTWARE CATALOG (for software_check demo)

MOCK_SOFTWARE_CATALOG = {
    "cisco anyconnect": {"available": True,  "version": "4.10.07061", "method": "Software Center"},
    "anyconnect":       {"available": True,  "version": "4.10.07061", "method": "Software Center"},
    "vpn":              {"available": True,  "version": "4.10.07061", "method": "Software Center (Cisco AnyConnect)"},
    "microsoft teams":  {"available": True,  "version": "24.1.0",    "method": "Pre-installed / Microsoft 365 Portal"},
    "teams":            {"available": True,  "version": "24.1.0",    "method": "Pre-installed / Microsoft 365 Portal"},
    "zoom":             {"available": True,  "version": "6.0.1",     "method": "Software Center"},
    "slack":            {"available": False, "version": None,        "method": "Not approved — use Microsoft Teams"},
    "visual studio code": {"available": True, "version": "1.92.0",  "method": "Software Center"},
    "vscode":           {"available": True,  "version": "1.92.0",    "method": "Software Center"},
    "adobe acrobat":    {"available": True,  "version": "24.002",    "method": "Software Center"},
    "autocad":          {"available": False, "version": None,        "method": "Request via IT ticket — license required"},
    "python":           {"available": True,  "version": "3.11.9",    "method": "Software Center"},
    "notepad++":        {"available": True,  "version": "8.6.7",     "method": "Software Center"},
    "7zip":             {"available": True,  "version": "24.06",     "method": "Software Center"},
}


class AutomationAgent:
    """
    Lightweight agent that detects and runs demo-safe automation actions.
    """

    # Public API

    def evaluate(self, user_message: str, intent: str,
                 kb_confidence: str, state) -> dict:
        """
        Main entry point.  Determines if the request is automation-eligible,
        handles confirmation flow, and executes mock actions.

        Parameters
        ----------
        user_message  : str   — raw user message
        intent        : str   — from IntentAgent
        kb_confidence : str   — "high", "medium", "low"
        state         : ConversationState

        Returns
        -------
        dict — AutomationResult (see _not_eligible() for shape)
        """

        S = state.STAGES
        if state.state == S["AUTOMATING"] and state.pending_automation:
            return self._handle_confirmation(user_message, state)

        action_type = self._detect_action_type(user_message)
        if not action_type:
            return self._not_eligible()

        log.info("Automation detected: action=%s", action_type)

        if action_type in CONFIRMATION_REQUIRED:
            return self._request_confirmation(action_type, user_message, state)
        else:
            # Auto-execute (read-only)
            return self._execute_action(action_type, user_message)

    # Confirmation lifecycle

    def _request_confirmation(self, action_type: str, user_message: str,
                              state) -> dict:
        """
        Sets state to AUTOMATING and returns a result
        that tells chatbot_engine to show a deterministic confirmation
        message (NOT via LLM prompt injection).
        """
        S = state.STAGES
        action_label = action_type.replace("_", " ")

        state.state = S["AUTOMATING"]
        state.pending_automation = {
            "action_type": action_type,
            "original_message": user_message,
        }

        log.info("Requesting confirmation for %s (State: %s)", action_type, S["AUTOMATING"])

        return {
            "eligible": True,
            "requires_confirmation": True,
            "attempted": False,
            "action_type": action_type,
            "success": None,
            "message": (
                f"I can attempt an automated **{action_label}** for you. "
                f"Would you like me to proceed? Reply **yes** or **no**."
            ),
            "details": {"target_system": self._get_target_system(action_type)},
            "next_step": "confirm",
            "fallback": "offer_ticket",
        }

    def _handle_confirmation(self, user_message: str, state) -> dict:
        """
        Handles the user's response while in AUTOMATING.

        Rules:
          • "yes" → execute the pending action
          • "no"  → clear pending, continue normal flow
          • new topic / unrelated message → clear pending, continue normal flow
          • ambiguous → re-prompt briefly
        """
        S = state.STAGES
        pending = state.pending_automation
        action_type = pending["action_type"]
        msg_low = user_message.lower().strip()

        if self._is_affirmative(msg_low):
            log.info("User confirmed %s — executing", action_type)
            state.state = S["TROUBLESHOOTING"]
            state.pending_automation = None
            return self._execute_action(action_type, pending["original_message"])

        if self._is_negative(msg_low):
            log.info("User declined %s — clearing", action_type)
            state.state = S["TROUBLESHOOTING"]
            state.pending_automation = None
            action_label = action_type.replace("_", " ")
            return {
                "eligible": True,
                "requires_confirmation": False,
                "attempted": False,
                "action_type": action_type,
                "success": None,
                "message": (
                    f"No problem — I've cancelled the {action_label}. "
                    f"Let me continue helping you with your issue."
                ),
                "details": None,
                "next_step": "declined",
                "fallback": "kb_guidance",
            }

        if self._is_topic_change(msg_low, pending):
            log.info("Topic change detected during %s confirmation — clearing",
                     action_type)
            state.state = S["TROUBLESHOOTING"]
            state.pending_automation = None
            return self._not_eligible()

        action_label = action_type.replace("_", " ")
        log.info("Ambiguous confirmation response for %s — re-prompting",
                 action_type)
        return {
            "eligible": True,
            "requires_confirmation": True,
            "attempted": False,
            "action_type": action_type,
            "success": None,
            "message": (
                f"I still have the **{action_label}** ready to go. "
                f"Would you like me to proceed? Reply **yes** or **no**."
            ),
            "details": pending.get("details"),
            "next_step": "confirm",
            "fallback": "offer_ticket",
        }

    # Action detection

    @staticmethod
    def _detect_action_type(message: str):
        """
        Detects automation-eligible action from user message.
        Returns action_type string or None.
        """
        msg = message.lower()

        # Account unlock
        account_keywords = []
        if any(kw in msg for kw in account_keywords):
            return "account_unlock"

        # Password reset
        password_keywords = []
        if any(kw in msg for kw in password_keywords):
            return "password_reset"

        # Software availability check
        software_keywords = [
            "install ", "is ", "do we have ", "do you have ",
            "software center", "can i get ", "need to install",
            "how to install", "how do i install",
        ]
        if any(kw in msg for kw in software_keywords):
            # Only trigger if a known software name appears
            for sw_name in MOCK_SOFTWARE_CATALOG:
                if sw_name in msg:
                    return "software_check"

        return None

    # Action execution (MOCK)

    def _execute_action(self, action_type: str, user_message: str) -> dict:
        """Routes to the appropriate mock action handler."""
        handlers = {
            "account_unlock": self._mock_account_unlock,
            "password_reset": self._mock_password_reset,
            "software_check": self._mock_software_check,
        }
        handler = handlers.get(action_type)
        if not handler:
            log.warning("No handler for action_type=%s", action_type)
            return self._not_eligible()

        return handler(user_message)

    def _mock_account_unlock(self, user_message: str) -> dict:
        """Simulates an Active Directory account unlock."""
        log.info("MOCK: Executing account unlock")
        time.sleep(0.3)  # Simulate brief processing delay

        return {
            "eligible": True,
            "requires_confirmation": False,
            "attempted": True,
            "action_type": "account_unlock",
            "success": True,
            "message": (
                "**Account unlock completed successfully.**\n\n"
                "Your Active Directory account has been unlocked. "
                "Please try logging in again. If the issue persists, "
                "your account may need a password reset as well."
            ),
            "details": {
                "target_system": "Active Directory",
                "action_taken": "Account unlocked",
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            },
            "next_step": "done",
            "fallback": None,
        }

    def _mock_password_reset(self, user_message: str) -> dict:
        """Simulates a password reset routing request."""
        log.info("MOCK: Executing password reset routing")
        time.sleep(0.3)

        return {
            "eligible": True,
            "requires_confirmation": False,
            "attempted": True,
            "action_type": "password_reset",
            "success": True,
            "message": (
                "**Password reset initiated.**\n\n"
                "A temporary password has been sent to your registered email address. "
                "Please check your inbox (and spam folder) and follow the instructions "
                "to set a new password. The link expires in 15 minutes."
            ),
            "details": {
                "target_system": "Active Directory",
                "action_taken": "Password reset email sent",
                "expiry": "15 minutes",
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            },
            "next_step": "done",
            "fallback": None,
        }

    def _mock_software_check(self, user_message: str) -> dict:
        """Simulates a software availability check against the catalog."""
        log.info("MOCK: Executing software availability check")
        msg = user_message.lower()

        # Find the matching software
        matched_name = None
        matched_info = None
        for sw_name, info in MOCK_SOFTWARE_CATALOG.items():
            if sw_name in msg:
                matched_name = sw_name
                matched_info = info
                break

        if not matched_info:
            return {
                "eligible": True,
                "requires_confirmation": False,
                "attempted": True,
                "action_type": "software_check",
                "success": True,
                "message": (
                    "I checked the software catalog but couldn't identify "
                    "the specific software you're looking for. Could you "
                    "provide the exact name?"
                ),
                "details": {"software": "unknown", "available": False},
                "next_step": "done",
                "fallback": "kb_guidance",
            }

        if matched_info["available"]:
            msg_text = (
                f"**{matched_name.title()}** is available for installation.\n\n"
                f"• **Version:** {matched_info['version']}\n"
                f"• **How to install:** {matched_info['method']}"
            )
        else:
            msg_text = (
                f"**{matched_name.title()}** is not currently available.\n\n"
                f"• **Reason:** {matched_info['method']}"
            )

        return {
            "eligible": True,
            "requires_confirmation": False,
            "attempted": True,
            "action_type": "software_check",
            "success": True,
            "message": msg_text,
            "details": {
                "software": matched_name.title(),
                "available": matched_info["available"],
                "version": matched_info["version"],
                "deployment_method": matched_info["method"],
            },
            "next_step": "done",
            "fallback": None if matched_info["available"] else "offer_ticket",
        }

    # Helpers

    @staticmethod
    def _not_eligible() -> dict:
        """Returns a no-op result for non-automation-eligible messages."""
        return {
            "eligible": False,
            "requires_confirmation": False,
            "attempted": False,
            "action_type": None,
            "success": None,
            "message": "",
            "details": None,
            "next_step": None,
            "fallback": None,
        }

    @staticmethod
    def _is_affirmative(msg: str) -> bool:
        """Checks if the message is an affirmative response."""
        words = set(msg.replace(",", "").replace(".", "").split())
        return bool(words & AFFIRMATIVE_WORDS)

    @staticmethod
    def _is_negative(msg: str) -> bool:
        """Checks if the message is a negative response."""
        words = set(msg.replace(",", "").replace(".", "").split())
        return bool(words & NEGATIVE_WORDS)

    @staticmethod
    def _is_topic_change(msg: str, pending: dict) -> bool:
        """
        Simple heuristic: if the message is long (>40 chars) and doesn't
        mention any keywords related to the pending action, treat it as
        a topic change.
        """
        if len(msg) < 40:
            return False

        action_type = pending.get("action_type", "")
        related_words = {
            "account_unlock": {"account", "locked", "unlock", "login"},
            "password_reset": {"password", "reset", "forgot"},
            "software_check": {"install", "software"},
        }
        keywords = related_words.get(action_type, set())
        msg_words = set(msg.split())
        return not bool(msg_words & keywords)

    @staticmethod
    def _get_target_system(action_type: str) -> str:
        """Returns the target system name for a given action type."""
        systems = {
            "account_unlock": "Active Directory",
            "password_reset": "Active Directory",
            "software_check": "Software Center",
        }
        return systems.get(action_type, "Unknown")
