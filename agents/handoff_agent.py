import re
import logging
import oci_genai

log = logging.getLogger("HandoffAgent")

# SYSTEM PROMPT  (owned by this agent)

TECHNICIAN_SUMMARY_PROMPT = """You are a Technical Support Lead at PCB Apps. Your task is to summarize a troubleshooting conversation between a user and an AI support assistant into a high-quality, professional handoff report for a human technician.

Your summary MUST be structured into exactly these 5 sections using these exact headers:
1. **Original Issue**: Clearly define the user's initial technical problem.
2. **AI Troubleshooting Steps**: List specific steps, checks, or solutions the AI already suggested and the results of those attempts.
3. **User Feedback & Follow-ups**: Summarize any follow-up questions, clarifications, or extra details provided by the user during the chat.
4. **Current Blocker**: Explain why the issue remains unresolved (e.g., complex configuration match not found, hardware failure suspected, on-site authorization required, or specific technical protocol unavailable).
5. **Technician Action Required**: Describe the immediate next step for the technician (e.g., "Verify user permissions in AD", "Manually reset VPN profile", "Coordinate hardware replacement").

== RULES ==
- Be concise, technical, and objective.
- Use bullet points for steps.
- Do NOT use flowery language or greetings.
- Focus on "Where we are now" and "What is next".
- Total response length should be under 2,500 characters.

Output the summary first, then on the last three lines output:
SUBJECT: [A concise, technical, and descriptive subject for this issue]
TOPIC: [Topic Name]
PRIORITY: [Priority Name]
"""

# AGENT CLASS

class HandoffAgent:
    """
    Lightweight agent that produces technician handoff reports from
    issue snapshots.
    """

    def summarize(self, snapshot: dict) -> dict:
        """
        Generates a structured handoff summary from an issue snapshot.

        Parameters
        ----------
        snapshot : dict
            The issue snapshot, expected keys:
              subject, topic, original_issue, timeline (list of {role, content})

        Returns
        -------
        dict
            {
                "subject":                 str,
                "description":             str,   # full AI-generated summary
                "topic":                   str,
                "priority":                str,   # Added Priority extraction
                "conversation_history":    list,
                "troubleshooting_summary": str,
                "technician_action":       str
            }
        """
        import utils
        subject  = snapshot.get("subject", "Technical Support Request")
        topic    = snapshot.get("topic", "Other")
        original = snapshot.get("original_issue") or "Not captured."
        timeline = snapshot.get("timeline", [])

        log.info("Generating handoff summary for '%s' (timeline: %d msgs)",
                 subject, len(timeline))

        chat_log = ""
        for msg in timeline:
            role = "User" if msg["role"] == "user" else "AI Assistant"
            chat_log += f"{role}: {msg['content']}\n\n"

        valid_topics = ", ".join(utils.TICKET_TOPICS)
        valid_priorities = ", ".join(utils.SEVERITIES)

        prompt = f"""Conversation Log:
{chat_log}

---
Current Metadata:
- Initial Topic Suggestion: {topic}
- Initial Subject: {subject}

TASK:
1. Generate the technician handoff summary following the strict 5-section format.
2. Determine the most appropriate Department/Topic from this list: {valid_topics}
3. Determine the Priority (Severity) from this list: {valid_priorities} (Low, Medium, High, Critical) based on business impact and urgency mentioned in the log.

Output the summary first, then on the last three lines output:
SUBJECT: [A concise, technical, and descriptive subject for this issue]
TOPIC: [Topic Name]
PRIORITY: [Priority Name]
"""

        try:
            summary_content = oci_genai.get_chat_response(
                prompt=prompt,
                system_prompt=TECHNICIAN_SUMMARY_PROMPT,
                temperature=0.1,
                max_tokens=1500
            )

            # Extract structured fields from the summary
            tech_action = self._extract_technician_action(summary_content)
            ts_summary  = self._extract_troubleshooting_summary(summary_content)
            
            # Extract metadata fields
            extracted_subject = subject
            extracted_topic = topic
            extracted_priority = "Medium"

            subject_match = re.search(r"SUBJECT:\s*(.*)", summary_content)
            if subject_match:
                new_subject = subject_match.group(1).strip()
                # ONLY use new AI subject if it's more than just a few characters
                if len(new_subject) > 5:
                    extracted_subject = new_subject
                summary_content = summary_content.replace(subject_match.group(0), "").strip()

            topic_match = re.search(r"TOPIC:\s*(.*)", summary_content)
            if topic_match:
                extracted_topic = topic_match.group(1).strip()
                summary_content = summary_content.replace(topic_match.group(0), "").strip()
            
            priority_match = re.search(r"PRIORITY:\s*(.*)", summary_content)
            if priority_match:
                extracted_priority = priority_match.group(1).strip()
                summary_content = summary_content.replace(priority_match.group(0), "").strip()

            # Validate topic
            if extracted_topic not in utils.TICKET_TOPICS:
                # Try partial match or fallback
                found = False
                for t in utils.TICKET_TOPICS:
                    if t.lower() in extracted_topic.lower():
                        extracted_topic = t
                        found = True
                        break
                if not found: extracted_topic = topic

            # Validate priority
            if extracted_priority not in utils.SEVERITIES:
                found = False
                for p in utils.SEVERITIES:
                    if p.lower() in extracted_priority.lower():
                        extracted_priority = p
                        found = True
                        break
                if not found: extracted_priority = "Medium"

            log.info("Handoff summary generated: Subject='%s', Topic=%s, Priority=%s",
                     extracted_subject, extracted_topic, extracted_priority)

            return {
                "subject": extracted_subject,
                "description": summary_content,
                "topic": extracted_topic,
                "priority": extracted_priority,
                "conversation_history": timeline,
                "troubleshooting_summary": ts_summary,
                "technician_action": tech_action
            }

        except Exception as e:
            log.error("AI Summary failed, falling back to basic: %s", e)
            return self._build_fallback(subject, topic, original, timeline)

    # Private helpers

    @staticmethod
    def _extract_technician_action(summary: str) -> str:
        """Extracts the Technician Action Required section from the summary."""
        for header in [
            r"\*\*Technician Action Required\*\*:\s*(.*)",
            r"\*\*Next Steps for Technician\*\*:\s*(.*)",
        ]:
            match = re.search(header, summary)
            if match:
                return match.group(1).strip()
        return "Assistance required for resolution."

    @staticmethod
    def _extract_troubleshooting_summary(summary: str) -> str:
        """Extracts the AI Troubleshooting Steps section from the summary."""
        if "**AI Troubleshooting Steps**:" in summary:
            match = re.search(
                r"\*\*AI Troubleshooting Steps\*\*:(.*?)(?=\*\*|\Z)",
                summary, re.DOTALL
            )
            if match:
                lines = match.group(1).strip().split("\n")[:5]
                return "\n".join(lines)
        return "Technical review required."

    @staticmethod
    def _build_fallback(subject: str, topic: str, original: str,
                        timeline: list) -> dict:
        """Produces a basic fallback when AI summary generation fails."""
        description = (
            f"**Subject:** {subject}\n"
            f"**Topic:** {topic}\n\n"
            f"**Original Issue:**\n{original}\n\n"
            f"**Note:** AI Summary service unavailable. "
            f"Please review the chat timeline manually."
        )
        return {
            "subject": subject,
            "description": description,
            "topic": topic,
            "conversation_history": timeline,
            "troubleshooting_summary": "Manual review required.",
            "technician_action": "Refer to chat logs."
        }
