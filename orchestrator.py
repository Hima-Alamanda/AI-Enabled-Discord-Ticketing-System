import re
import logging
from agents.continuity_agent import ContinuityAgent
from agents.intent_agent import IntentAgent
from agents.issue_understanding_agent import IssueUnderstandingAgent
from agents.clarification_engine import ClarificationEngine

log = logging.getLogger("Orchestrator")


class SupportOrchestrator:
    """
    Central orchestrator that coordinates between the Continuity and Intent agents.
    """

    def __init__(self):
        self.continuity_agent = ContinuityAgent()
        self.intent_agent = IntentAgent()
        self.issue_understanding_agent = IssueUnderstandingAgent()
        self.clarification_engine = ClarificationEngine()
        log.info("SupportOrchestrator initialised")

    def plan_next_step(self, user_message: str, history: list, state, has_file: bool) -> dict:
        """
        Lightweight decision logic with state awareness.
        """
        msg_low = user_message.lower().strip()

        # baseline decision
        decision = {
            "message_type":        "technical",
            "should_search_kb":    True,
            "should_use_history":  True,
            "should_offer_ticket": False,
            "should_create_ticket":False,
            "should_escalate":     False,
            "kb_query":            user_message,
            "response_mode":       "rag",
            "continuity":          "SAME_ISSUE",
            "intent":              "support_question",
            "urgency":             "low",
            "summary":             "",
        }

        # Precise word-boundary check for greetings to avoid matching names like 'Himanth'
        is_greeting = any(re.search(fr"\b{re.escape(x)}\b", msg_low) for x in ["hi", "hello", "hey", "good morning", "good afternoon"])
        is_closure      = any(x in msg_low for x in ["it works", "it's working", "its working", "resolved", "fixed", "thanks", "thank you", "worked"])
        is_general      = any(x in msg_low for x in ["how are you", "what are you doing", "who are you"])
        is_status       = bool(re.search(r'\b(AI\d{14}|\d{14})\b', user_message))
        is_ticket_req   = any(x in msg_low for x in ["create ticket", "open ticket", "log ticket", "raise ticket"])
        is_escalate_req = any(x in msg_low for x in ["human", "agent", "call me", "escalate", "technician"])
        
        # FIX: "report" and "summary" are too ambiguous for technical support (e.g. "reporting errors").
        # We only trigger visualization for explicit chart/graph/dashboard keywords or specific ticket reports.
        is_visualization = any(x in msg_low for x in ["visualiz", "graph", "chart", "plot", "dashboard", "insight", "analytics", "stats", "visualis"])
        is_report_request = "report" in msg_low and any(y in msg_low for y in ["ticket", "trend", "status", "distribution", "analysis"])
        is_visualization = is_visualization or is_report_request
        
        # BLOCK: If there is technical error context, we only allow visualization IF explicitly requested.
        is_technical_context = any(x in msg_low for x in ["error", "fail", "issue", "problem", "broken", "message", "sync", "amount"])
        has_explicit_chart_word = any(x in msg_low for x in ["chart", "graph", "plot", "visualize"])
        
        if is_technical_context and not has_explicit_chart_word:
            is_visualization = False

        is_list_tickets  = any(x in msg_low for x in ["show my tickets", "list my tickets", "my tickets status", "my open tickets", "my tickets"])

        # Social intent takes precedence ONLY if it's a short, pure social message.
        # If it's long, it's likely a technical request starting with a greeting.
        if is_greeting and len(msg_low.split()) < 5:
            decision.update({
                "message_type": "greeting", "should_search_kb": False,
                "response_mode": "chat",
                "intent": "smalltalk", "urgency": "low",
            })
            log.info("Routed → greeting (Social Priority)")
            return decision

        if is_closure:
            decision.update({
                "message_type": "closure", "should_search_kb": False,
                "response_mode": "chat",
                "intent": "smalltalk", "urgency": "low",
            })
            state.state = "IDLE"
            state.active_issue_id = None
            log.info("Routed → closure (Social Priority)")
            return decision

        if is_general:
            decision.update({
                "message_type": "general", "should_search_kb": False,
                "response_mode": "chat",
                "intent": "smalltalk", "urgency": "low",
            })
            log.info("Routed → general smalltalk (Social Priority)")
            return decision

        S = state.STAGES
        if state.state == S["CLARIFYING"]:
            # Check if this is a valid response to the clarification question
            snapshot = state.issue_snapshots.get(state.active_issue_id, {})
            if self.issue_understanding_agent.is_clarification_response(user_message, snapshot):
                log.info("Detected clarification response (Stage: %s)", S["CLARIFYING"])
                decision.update({
                    "message_type": "clarification_response",
                    "continuity": "SAME_ISSUE",
                    "intent": "followup"
                })
                # We want to perform a full KB search after incorporating the new info
                decision["should_search_kb"] = True
                return decision

        if state.state == S["CONFIRMING"]:
            if is_closure: # Redundant but safe
                 state.state = "IDLE"
                 state.active_issue_id = None
                 return decision

        if is_status:
            decision.update({
                "message_type": "status_check", "should_search_kb": False,
                "response_mode": "status",
                "intent": "check_status", "urgency": "low",
            })
            log.info("Routed → status_check")
            return decision

        if is_visualization:
            decision.update({
                "message_type": "visualization", "should_search_kb": False,
                "response_mode": "analytics",
                "intent": "visualize", "urgency": "low",
            })
            log.info("Routed → visualization")
            return decision

        if is_list_tickets:
            decision.update({
                "message_type": "list_tickets", "should_search_kb": False,
                "response_mode": "tickets",
                "intent": "list_tickets", "urgency": "low",
            })
            log.info("Routed → list_tickets")
            return decision

        if is_escalate_req:
            decision.update({
                "message_type": "escalate_request", "should_search_kb": True,
                "response_mode": "rag",
                "intent": "escalate", "urgency": "high",
            })
            log.info("Routed → escalate_request")
            return decision

        if is_ticket_req:
            decision.update({
                "message_type": "ticket_request", "should_search_kb": False,
                "should_offer_ticket": True, "response_mode": "rag",
                "intent": "create_ticket", "urgency": "medium",
            })
            log.info("Routed → ticket_request")

        elif state.active_issue_id:
            snapshot = state.issue_snapshots.get(state.active_issue_id, {})
            continuity = self.continuity_agent.decide_continuity(user_message, state, snapshot)
            decision["continuity"] = continuity

            if continuity == "SAME_ISSUE":
                decision["message_type"] = "followup"
                decision["kb_query"] = self.continuity_agent.build_kb_search_query(user_message, snapshot)
                log.info("ContinuityAgent → SAME_ISSUE (followup)")
            elif continuity == "NEW_ISSUE":
                decision["message_type"] = "technical"
                decision["kb_query"] = user_message
                log.info("ContinuityAgent → NEW_ISSUE")
            elif continuity == "UNCERTAIN":
                decision.update({
                    "message_type": "continuity_check",
                    "should_search_kb": False,
                    "response_mode": "chat",
                    "intent": "followup", "urgency": "low",
                })
                log.info("ContinuityAgent → UNCERTAIN")
        else:
            log.info("Routed → technical (default, no active issue)")

        # file attachment always forces technical + KB search
        if has_file:
            decision["message_type"] = "technical"
            decision["should_search_kb"] = True
            log.info("File attached → forcing technical + KB search")

        # Only invoke the LLM classifier when we actually need fine-grained
        # intent + urgency (i.e. KB-path messages).  All simple routes above
        # already have intent/urgency set via heuristics.
        if decision["message_type"] in ("technical", "followup", "escalate_request"):
            intent_data = self.intent_agent.detect_intent(user_message, history)
            decision["intent"]   = intent_data.get("intent", "support_question")
            decision["urgency"]  = intent_data.get("urgency", "low")
            decision["summary"]  = intent_data.get("summary", "")
            log.info("IntentAgent → intent=%s urgency=%s", decision["intent"], decision["urgency"])

        log.debug("Final decision: %s", decision)
        return decision
