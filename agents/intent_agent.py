"""
Intent Agent — classifies user messages into actionable intents.

Responsibilities:
  • Uses OCI GenAI to classify intent (create_ticket, support_question, …).
  • Determines perceived urgency (low / medium / high).
  • Returns a one-sentence summary for internal logging.
"""

import json
import re
import logging
import oci_genai

log = logging.getLogger("IntentAgent")

# SYSTEM PROMPT  (kept here so the agent fully owns its classification logic)

INTENT_SYSTEM_PROMPT = """Classify the user's message into exactly ONE of these intents. 
Reply with ONLY the JSON object, no other text.

Intents:
- "create_ticket": User wants to open/submit/log a new support ticket
- "check_status": User is asking about the status of an existing ticket
- "support_question": User has a technical problem or question
- "escalate": User explicitly wants to speak to a human agent
- "file_analysis": User is asking about a file they attached
- "smalltalk": Greetings (hi, hello, etc.), thanks, how are you, or general conversation
- "followup": User is asking for clarification, explanation of a step, or help with a previous response given by the AI
- "other": Anything else that doesn't fit the above

Output format (JSON only):
{"intent": "<intent>", "urgency": "<low|medium|high>", "summary": "<one sentence summary of the request>"}
"""

# AGENT CLASS

class IntentAgent:
    """
    Lightweight agent that classifies user intent via OCI GenAI.
    """

    @staticmethod
    def detect_intent(user_message: str, history: list = None) -> dict:
        """
        Uses OCI GenAI to classify the user's intent.
        Returns dict: {intent, urgency, summary}
        """
        # Build context from recent history (last 4 turns)
        history_context = ""
        if history and len(history) > 1:
            recent = history[-4:]
            history_context = "Recent conversation:\n"
            for msg in recent:
                role = "User" if msg['role'] == 'user' else "AI"
                history_context += f"{role}: {msg['content'][:200]}\n"

        # Heuristic short-circuit for very short messages (greetings)
        msg_lower = user_message.lower().strip()
        if len(msg_lower) < 10 and msg_lower in [
            "hi", "hii", "hello", "hey", "test", "clear", "thanks", "thank you"
        ]:
            log.debug("Short-circuit → smalltalk (%s)", msg_lower)
            return {"intent": "smalltalk", "urgency": "low", "summary": "Greeting or thanks"}

        prompt = f"""{history_context}
Current user message: "{user_message}"

Classify the intent."""

        try:
            raw = oci_genai.get_chat_response(
                prompt=prompt,
                system_prompt=INTENT_SYSTEM_PROMPT,
                temperature=0.0,
                max_tokens=100
            )
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                result = json.loads(match.group())
                log.info(
                    "Intent detected → %s | urgency=%s | summary=%s",
                    result.get("intent"), result.get("urgency"),
                    result.get("summary", "")[:60]
                )
                return result
        except Exception as e:
            log.error("Intent detection failed: %s", e)

        # Fallback to 'other' to avoid aggressive ticketing
        log.warning("Falling back to intent=other")
        return {"intent": "other", "urgency": "low", "summary": user_message}
