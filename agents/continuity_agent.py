"""
Continuity Agent — owns conversation state and issue-session tracking.

Responsibilities:
  • Stores and retrieves per-user ConversationState (in-memory).
  • Decides if a follow-up message belongs to the SAME issue, a NEW issue,
    or is UNCERTAIN.
  • Builds enriched KB search queries from snapshot context.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

log = logging.getLogger("ContinuityAgent")

# DATA MODEL

@dataclass
class ConversationState:
    # Authoritative Lifecycle Stages
    STAGES = {
        "IDLE": "IDLE",
        "IDENTIFYING": "IDENTIFYING_ISSUE",
        "CLARIFYING": "AWAITING_CLARIFICATION",
        "TROUBLESHOOTING": "TROUBLESHOOTING",
        "CONFIRMING": "AWAITING_CONFIRMATION",
        "AUTOMATING": "AWAITING_AUTOMATION_CONFIRM",
        "CONTINUITY": "AWAITING_CONTINUITY_CONFIRMATION",
        "TICKET_READY": "READY_FOR_TICKET",
        "RESOLVED": "RESOLVED",
        "CLOSED": "CLOSED"
    }

    active_issue_id: Optional[str] = None
    state: str = "IDLE"  
    issue_snapshots: Dict[str, dict] = field(default_factory=dict)  # keyed by issue_id
    pending_automation: Optional[dict] = None  # stores pending automation action during confirmation

# Singleton in-memory store (keyed by email / user_id)
CONVERSATION_STATES: Dict[str, ConversationState] = {}

# AGENT CLASS

class ContinuityAgent:
    """
    Lightweight agent that tracks session continuity and issue snapshots.
    All methods are intentionally stateless on the class itself — state lives
    in the module-level CONVERSATION_STATES dict so that both the orchestrator
    and chatbot_engine can share the same store.
    """


    @staticmethod
    def get_state(email: str) -> ConversationState:
        """Return (or create) the ConversationState for a given user key."""
        if not email or email == "unknown":
            log.debug("Anonymous user — returning transient state")
            return ConversationState()
        if email not in CONVERSATION_STATES:
            CONVERSATION_STATES[email] = ConversationState()
            log.info("Created new ConversationState for %s", email)
        return CONVERSATION_STATES[email]


    @staticmethod
    def decide_continuity(user_message: str, state: ConversationState, snapshot: dict) -> str:
        """
        Heuristic to decide if a message is the SAME issue, a NEW issue, or UNCERTAIN.
        """
        msg_low = user_message.lower().strip()

        # Enforce lifecycle stages
        STAGES = {
            "CLARIFYING":  "AWAITING_CLARIFICATION",
            "TROUBLESHOOTING": "TROUBLESHOOTING"
        }

        if state.state == STAGES["CLARIFYING"]:
            log.info("Continuity → SAME_ISSUE (AWAITING_CLARIFICATION context)")
            return "SAME_ISSUE"

        # Clearly Related Phrases
        related_keywords = [
            "it didn't work", "it still doesn't work", "tried that", "it's still",
            "how do i", "can you clarify", "which one", "step", "what about",
            "thanks but", "still seeing", "another question about", "wait"
        ]
        if any(k in msg_low for k in related_keywords):
            log.debug("Continuity → SAME_ISSUE (related keyword match)")
            return "SAME_ISSUE"

        # Clearly Independent technical broad topics 
        subject = snapshot.get("subject", "").lower()
        tech_terms = [
            "vpn", "email", "password", "teams", "printer",
            "wi-fi", "laptop", "monitor", "software", "install", "sap"
        ]
        found_new_terms = [t for t in tech_terms if t in msg_low and t not in subject]

        if len(msg_low.split()) > 10 and len(found_new_terms) >= 2:
            log.info("Continuity → NEW_ISSUE (new tech terms: %s)", found_new_terms)
            return "NEW_ISSUE"

        # Short vague followups
        if len(msg_low.split()) < 5:
            log.debug("Continuity → SAME_ISSUE (short message)")
            return "SAME_ISSUE"

        # Ambiguous shifts
        uncertain_keywords = ["also", "another issue", "can you check this too", "one more thing"]
        if any(k in msg_low for k in uncertain_keywords):
            log.info("Continuity → UNCERTAIN (ambiguous keyword)")
            return "UNCERTAIN"

        log.debug("Continuity → SAME_ISSUE (default)")
        return "SAME_ISSUE"


    @staticmethod
    def build_kb_search_query(user_message: str, snapshot: dict) -> str:
        """
        Builds a rich query for KB retrieval using current issue context.
        Prioritizes locked domain and symptom from the snapshot.
        """
        query_parts = []
        
        locked_dom = snapshot.get("locked_domain")
        locked_sym = snapshot.get("locked_symptom")
        
        if locked_dom:
            query_parts.append(locked_dom.title())
        
        if locked_sym:
            query_parts.append(locked_sym)
        
        # If no locked symptom, use subject or extracted symptom
        if not locked_sym:
            subject = snapshot.get("subject", "")
            symptom = snapshot.get("symptom", "")
            if symptom and symptom != "not_working":
                query_parts.append(symptom.replace("_", " "))
            elif subject:
                query_parts.append(subject)

        # But only if it's not a short clarification answer (handled by engine)
        if len(user_message.split()) > 3:
            query_parts.append(user_message)

        err = snapshot.get("error_code")
        if err:
            query_parts.append(f"error {err}")

        query = " ".join(query_parts).strip()
        
        # Fallback to user message if for some reason we have no context
        if not query:
            return user_message
            
        log.info("Built snapshot-aware KB query: '%s'", query)
        return query
