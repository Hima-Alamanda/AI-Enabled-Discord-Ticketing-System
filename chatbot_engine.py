"""
Central brain for the AI Support Chatbot.

Capabilities:
  1. Human-like multi-turn conversation with intent understanding
  2. Reads screenshots, logs, PDFs inline in chat
  3. Searches KB vectors + past tickets before responding
  4. Confidence-based escalation when unsure
  5. Auto ticket creation from conversation context

"""

import json
import re
import uuid
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import database
import oci_genai
import controller
import utils

from document_processor import extract_text_from_any

from orchestrator import SupportOrchestrator
from agents.continuity_agent import ContinuityAgent, ConversationState
from agents.knowledge_agent import KnowledgeAgent
from agents.handoff_agent import HandoffAgent
from agents.automation_agent import AutomationAgent
from agents.issue_understanding_agent import IssueUnderstandingAgent
from agents.retrieval_manager import RetrievalManager
from agents.clarification_engine import ClarificationEngine

# Authoritative lifecycle stages
STAGES = ConversationState.STAGES

log = logging.getLogger("ChatbotEngine")

# CONSTANTS

CHATBOT_SYSTEM_PROMPT = """You are "PCB Support AI", a Senior IT Support Engineer for PCB Apps.
You are a highly skilled, empathetic, and professional technical expert. Your goal is to provide accurate, helpful, and context-aware support.

== YOUR PERSONALITY ==
- Professional, efficient, and technical IT Support specialist.
- PCB stands for PCB Apps (an IT solutions provider), NOT Printed Circuit Boards.
- You focused EXCLUSIVELY on ITSM (IT Service Management) and internal technical support.
- Call the user by their first name when available.
- Be context-aware: match your response length and complexity to the user's query.

== ADAPTIVE RESPONSE STYLE ==
To provide a "Pro" experience, you must decide the best way to respond:

1. **Concise Answers**: For simple questions, status updates, or quick queries, give a direct and clear answer immediately. Do not use sections or headers if they are unnecessary.
2. **Structured Analysis**: ONLY for complex technical issues, troubleshooting requests, or error log analysis, use the following structure:
   - **Issue Analysis**: Explain your understanding of the technical problem.
   - **Cause**: List the likely technical reasons for the issue.
   - **Resolution Steps**: Provide clear, numbered instructions from your technical expertise.
   - **Next Steps**: Explain what to do if the steps fail or offer escalation.

== CAPABILITIES ==
- Deep technical expertise across PCB Apps systems and infrastructure.
- Ability to analyze logs, images, and configuration patterns to provide resolutions.
- Direct management of ticket creation and escalation to senior technicians.

== FORMATTING RULES ==
- Use **bold** for technical terms, buttons, and error codes.
- Do NOT use backticks (`` ` ``).
- Keep formatting clean and professional.

== GUIDELINES ==
- DIRECT RESOLUTION: Always provide technical solutions directly. Do not narrate where you found the information.
- ROLEPLAY: Act as a support engineer who already knows the solution. Never say "I checked the Knowledge Base" or "According to the documentation."
- ESCALATION REASONING: If a manual fix is not immediately available, provide a professional technical assessment of why the issue requires a human specialist (e.g., "This scenario requires administrator-level analysis to resolve" or "This issue typically requires specialized team investigation"). DO NOT say "I'm not seeing a fix", "I couldn't find a solution", or "I'm not seeing a confirmed fix".
- HYPOTHETICAL REASONING: If a specific documented protocol is missing but the technical context is clear (e.g., a ticket quantity limit or a specific error code), use your technical reasoning to suggest a "Likely Root Cause." Explain the technical logic behind your guess clearly to the user.
- CONTEXT ISOLATION: If the user shifts to a new, unrelated technical problem, ignore previous history and focus exclusively on the latest message.
- NO HALLUCINATIONS: If you don't know a detail, state it clearly.
- ACTION SIGNALS: 
  - TICKET CREATION: Suggest or output ACTION:CREATE_TICKET ONLY if the issue requires specialized team investigation AND the user has explicitly confirmed they want a ticket created.
  - ESCALATION: Suggest or output ACTION:ESCALATE ONLY if the issue is critically beyond standard self-service protocols OR if the primary solution fails to resolve the issue for the user.
  - RESOLUTION OVER ACTION: Your first priority is to solve the issue today. If a solution exists, provide it clearly first before suggesting a ticket.
  - CONVERSATIONAL: If the user says "it works", "thanks", "fixed", etc., simply acknowledge it warmly and ask if they need anything else.
"""

orchestrator      = SupportOrchestrator()
continuity_agent  = ContinuityAgent()
knowledge_agent   = KnowledgeAgent()
handoff_agent     = HandoffAgent()
automation_agent  = AutomationAgent()
issue_understanding_agent = IssueUnderstandingAgent()
retrieval_manager = RetrievalManager()
clarification_engine = ClarificationEngine()



def extract_ticket_data(user_message: str, history: list = None) -> dict:
    """
    Uses AI to extract Subject, Description, Topic, Impact and Assessment from conversation context.
    Returns JSON: {"subject": str, "description": str, "topic": str, "impact": str, "assessment": str}
    """
    try:
        history_context = ""
        if history:
            for msg in history[-4:]:
                role = "User" if msg['role'] == 'user' else "AI"
                history_context += f"{role}: {msg['content'][:300]}\n"

        system_prompt = f"""You are a Ticket Analyzer. Extract support ticket details from the conversation.
Valid Topics: {", ".join(utils.TICKET_TOPICS)}
Valid Priorities: {", ".join(utils.SEVERITIES)}

RULES:
1. SUBJECT: Extract the core technical issue or error message.
2. DESCRIPTION: Summarize the user's problem.
3. TOPIC: Select the most relevant department from the Valid Topics list.
4. PRIORITY: Determine the severity (Low, Medium, High, Critical) from the Valid Priorities list.
5. IMPACT: Describe why this affects the user or business.
6. ASSESSMENT: Provide a brief technical hypothesis of the likely cause.

Output ONLY a JSON object:
{{
  "subject": "...", 
  "description": "...", 
  "topic": "...", 
  "priority": "...",
  "impact": "...", 
  "assessment": "..."
}}
"""

        prompt = f"""{history_context}
Latest message/context: {user_message}

Extract the ticket details accurately including impact and assessment logic based on the full conversation context."""

        raw = oci_genai.get_chat_response(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1
        )
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            extracted = json.loads(match.group())
            if not extracted.get("subject") or len(extracted["subject"]) < 5:
                extracted["subject"] = user_message[:50] + "..." if len(user_message) > 50 else user_message
            return extracted
    except Exception as e:
        log.error("Ticket extraction failed: %s", e)

    # Robust fallback if extraction fails
    error_match = re.search(r'([A-Z][a-z]+Error:.*)', user_message)
    subject = error_match.group(1)[:60] if error_match else user_message[:60]
    
    return {
        "subject": subject or "Technical Support Inquiry",
        "description": user_message or "Ticket created from conversation context.",
        "topic": "Other (Custom...)",
        "impact": "User productivity affected.",
        "assessment": "Issue requires technician review."
    }




# FILE PROCESSING

def process_uploaded_file(uploaded_file) -> dict:
    """
    Extracts text/content from an uploaded file.
    Returns {'text': str, 'filename': str, 'is_image': bool, 'bytes': bytes}
    """
    if uploaded_file is None:
        return {}

    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)

    result = {
        "filename": uploaded_file.name,
        "is_image": uploaded_file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')),
        "bytes": file_bytes,
        "text": ""
    }

    extracted = extract_text_from_any(uploaded_file)
    result["text"] = extracted or ""

    if result["is_image"] and not result["text"]:
        result["text"] = "[Screenshot attached — analyzing visual content]"

    return result


def get_chatbot_response(
    user_message: str,
    history: list,
    user_context: dict,
    uploaded_file=None
) -> dict:
    """
    Main entry point for the chatbot.
    discord_bot.py calls this and expects: content, sources, confidence,
    action, ticket_id, ticket_data, file_info, intent, issue_id, state.
    """
    user_id   = user_context.get('user_id', 'unknown')
    user_name = user_context.get('name', 'there')
    user_email = user_context.get('email', 'unknown')
    first_name = user_name.split()[0] if user_name and user_name != 'unknown' else 'there'

    state_key = user_email if user_email != 'unknown' else user_id
    state = continuity_agent.get_state(state_key)
    log.info("== New request from %s | state=%s | active_issue=%s ==",
             first_name, state.state, state.active_issue_id)

    result = {
        "content": "",
        "sources": [],
        "confidence": "high",
        "action": None,
        "ticket_id": None,
        "ticket_data": None,
        "file_info": None,
        "intent": "support_question",
        "issue_id": state.active_issue_id,
        "state": state.state
    }

    has_file = (uploaded_file is not None)
    decision = orchestrator.plan_next_step(user_message, history, state, has_file)
    log.info("Orchestrator decision: type=%s mode=%s continuity=%s",
             decision["message_type"], decision["response_mode"], decision.get("continuity"))

    file_context = ""
    file_info = None
    if uploaded_file is not None:
        file_info = process_uploaded_file(uploaded_file)
        result["file_info"] = file_info
        if file_info.get("text"):
            file_context = f"\n\n=== USER UPLOADED FILE: {file_info['filename']} ===\n{file_info['text'][:3000]}"

    full_query = user_message + file_context

    intent  = decision["intent"]
    urgency = decision["urgency"]
    log.info("Orchestrator intent=%s urgency=%s", intent, urgency)

    # Initialize KB context container
    kb_data = {"context_text": "", "sources": [], "confidence": "low"}

    S = state.STAGES

    if decision["message_type"] in ["technical", "followup", "escalate_request", "clarification_response"]:
        if state.active_issue_id is None or decision.get("continuity") == "NEW_ISSUE":
            state.active_issue_id = str(uuid.uuid4())
            state.state = S["IDENTIFYING"]
            result["issue_id"] = state.active_issue_id
            result["state"] = state.state
            log.info("New issue session: %s (Stage: %s)", state.active_issue_id, state.state)

        snapshot = state.issue_snapshots.get(state.active_issue_id, {})
        # Initialize essential snapshot fields if new
        snapshot.setdefault("stage", S["IDENTIFYING"])
        snapshot.setdefault("locked_domain", None)
        snapshot.setdefault("locked_symptom", None)
        snapshot.setdefault("bot_guidance", [])
        snapshot.setdefault("troubleshooting_steps", [])
        snapshot.setdefault("timeline", [])
        
        # Track timeline including OCR evidence
        snapshot["timeline"].append({"role": "user", "content": full_query})
        snapshot.update({
            "issue_id": state.active_issue_id,
            "attachment_info": file_info or snapshot.get("attachment_info"),
            "created_at": snapshot.get("created_at", datetime.now().isoformat())
        })

        if decision["message_type"] == "clarification_response":
            snapshot = clarification_engine.process_clarification_response(user_message, snapshot)
            snapshot["stage"] = S["TROUBLESHOOTING"]
            state.state = S["TROUBLESHOOTING"]

        # Use full_query (msg + OCR) for extraction
        current_issue = issue_understanding_agent.extract_issue_fields(full_query, snapshot)
        
        # If rule-based is not confident or missing system, use LLM logic
        if current_issue.get("confidence", 0) < 0.5 or "system_or_application" in current_issue.get("missing_slots", []):
            log.info("Rule-based understanding low (conf=%s). Triggering semantic extraction...", current_issue.get("confidence"))
            semantic_fields = issue_understanding_agent.semantic_extract_issue_fields(full_query, history)
            if semantic_fields:
                log.info("Semantic overlay found: %s", semantic_fields.get("system"))
                # Overlay semantic results onto current issue
                for k, v in semantic_fields.items():
                    if v and k != "missing_slots":
                        current_issue[k] = v
                
                # Re-calculate missing slots and confidence with new fields
                current_issue["missing_slots"] = issue_understanding_agent._detect_missing_slots(current_issue)
                current_issue["confidence"] = issue_understanding_agent._calculate_confidence(current_issue)

        issue = issue_understanding_agent.merge_issue_context(current_issue, snapshot)
        
        if snapshot.get("locked_domain"):
            ld = snapshot["locked_domain"]
            if ld in ["sap", "outlook", "vpn", "teams"]:
                issue["application"] = ld
            else:
                issue["system"] = ld
        
        if snapshot.get("locked_symptom"):
            issue["symptom"] = snapshot["locked_symptom"]

        # Update snapshot with latest technical understanding
        snapshot.update({
            "issue_type": issue["issue_type"],
            "symptom": issue["symptom"],
            "system": issue["system"],
            "application": issue["application"],
            "device": issue["device"],
            "error_code": issue["error_code"],
            "missing_slots": issue["missing_slots"],
            "ambiguity_flags": issue["ambiguity_flags"]
        })

        # Use ContinuityAgent's robust builder instead of basic refined query
        search_query = continuity_agent.build_kb_search_query(user_message, snapshot)
        
        pref_domain = issue.get("application") or issue.get("system")
        is_locked = bool(snapshot.get("locked_domain"))
        is_troubleshooting = snapshot["stage"] == S["TROUBLESHOOTING"]
        
        retrieval_analysis = retrieval_manager.retrieve_and_analyze(
            search_query, 
            preferred_domain=pref_domain, 
            strict_domain=(is_locked or is_troubleshooting)
        )
        
        result["sources"] = list(set(r["source"] for r in retrieval_analysis["candidates"]))
        result["confidence"] = retrieval_analysis["kb_confidence"]

        decision_step = clarification_engine.decide_next_step(issue, retrieval_analysis, snapshot)
        log.info("Lifecycle Decision: %s (Stage: %s)", decision_step, snapshot["stage"])

        if decision_step == "CLARIFY":
            package = clarification_engine.get_clarification_package(issue, retrieval_analysis, history)
            question = package.get("question", "Could you provide more details?")
            options = package.get("options", ["Other"])
            
            clarification_engine.update_snapshot_with_clarification(snapshot, issue, retrieval_analysis, question, options)
            
            snapshot["stage"] = S["CLARIFYING"]
            state.state = S["CLARIFYING"]
            
            result["content"] = question
            result["state"] = state.state
            result["clarification_options"] = options 
            state.issue_snapshots[state.active_issue_id] = snapshot
            return result

        elif decision_step == "ESCALATE":
            escalation_result = _handle_escalation(user_message, user_email, history, first_name, {})
            result.update(escalation_result)
            state.state = S["IDLE"]
            state.active_issue_id = None
            result["state"] = state.state
            result["issue_id"] = None
            return result

        # Search for relevant past tickets using the same snapshot-aware query
        tickets = knowledge_agent._search_past_tickets(search_query)
        scored_tickets = knowledge_agent._score_past_tickets(tickets, search_query)
        
        kb_data["context_text"] = KnowledgeAgent._build_context_text(
            retrieval_analysis["candidates"], scored_tickets, retrieval_analysis["kb_confidence"]
        )
        kb_data["confidence"] = retrieval_analysis["kb_confidence"]
        kb_data["sources"] = result["sources"]
        kb_data["kb_results"] = retrieval_analysis["candidates"] # For snapshot persistence lower down
        
        # Persist snapshot
        state.issue_snapshots[state.active_issue_id] = snapshot

    result["intent"] = intent
    automation_result = {"eligible": False}
    if decision["message_type"] in ("technical", "followup"):
        automation_result = automation_agent.evaluate(
            user_message, intent, kb_data.get("confidence", "low"), state
        )
        if automation_result["eligible"]:
            log.info("AutomationAgent: action=%s attempted=%s confirm=%s",
                     automation_result["action_type"],
                     automation_result["attempted"],
                     automation_result["requires_confirmation"])

            if automation_result.get("next_step") in ("confirm", "declined"):
                result["content"] = automation_result["message"]
                result["state"] = state.state
                log.info("Returning deterministic automation message (next_step=%s)",
                         automation_result["next_step"])
                return result

    # Handle direct status check if requested via ID
    if decision["message_type"] == "status_check":
        tid_match = re.search(r'\b(AI\d{14}|\d{14})\b', user_message)
        if tid_match:
            ticket_id = tid_match.group(1)
            ticket = controller.get_ticket_by_id(ticket_id)
            if ticket:
                upd = ticket.get('updated_at')
                upd_str = str(upd)[:19] if upd else "N/A"
                result["content"] = (
                    f"**Ticket {ticket_id}**\n\n"
                    f"- **Subject:** {ticket.get('subject', 'N/A')}\n"
                    f"- **Status:** {ticket.get('status', 'Unknown')}\n"
                    f"- **Priority:** {ticket.get('priority', 'Medium')}\n"
                    f"- **Last Updated:** {upd_str}\n\n"
                    f"Is there anything else I can help you with?"
                )
                return result
            else:
                result["content"] = f"I couldn't find ticket **{ticket_id}** in the system."
        else:
            result["content"] = "Please share the ticket ID and I'll look it up for you."
        return result

    # Handle simple smalltalk bypassing RAG
    if decision["message_type"] in ["greeting", "closure", "general", "continuity_check"]:
        if decision["message_type"] == "continuity_check":
            state.state = S["CONTINUITY"]
            result["state"] = state.state
            result["content"] = "I want to track this correctly. Is this related to your current issue, or would you like to start a new one?"
            return result
            
        response = oci_genai.get_chat_response(
            prompt=f"User: {user_message}\nRespond warmly and briefly.",
            system_prompt=CHATBOT_SYSTEM_PROMPT,
        )
        result["content"] = response
        return result
    history_str = _format_history_for_prompt(history)
    user_info_str = f"User: {user_name} | Email: {user_email} | Urgency: {urgency}"

    ticket_draft_str = ""
    if result.get("ticket_data"):
        td = result["ticket_data"]
        ticket_draft_str = f"=== DRAFT TICKET DATA ===\nSubject: {td.get('subject')}\nTopic: {td.get('topic')}\n"

    attempted_str = ""
    if state.active_issue_id:
        snapshot = state.issue_snapshots.get(state.active_issue_id, {})
        attempted = snapshot.get("attempted_steps", [])
        if attempted:
            attempted_str = f"=== PREVIOUSLY ADVISED/ATTEMPTED ===\n" + "\n".join([f"- {s}" for s in attempted]) + "\n"

    automation_context = ""
    if automation_result.get("eligible") and automation_result.get("attempted"):
        automation_context = f"""
=== AUTOMATION RESULT ===
Action: {automation_result['action_type']}
Result: {'Completed successfully' if automation_result.get('success') else 'Failed'}
Message: {automation_result['message']}
Details: {automation_result.get('details', 'N/A')}

IMPORTANT: An automated action was just executed. Inform the user of the result above.
If it succeeded, ask if they need anything else.
If it failed, offer to create a ticket or try KB guidance.
"""

    final_prompt = f"""
{user_info_str}

{history_str}
Intent: {intent} (Urgency: {urgency})

{ticket_draft_str}
{attempted_str}
{automation_context}

=== TECHNICAL CONTEXT & PROCEDURES ===
{kb_data['context_text']}

=== CURRENT USER MESSAGE ===
{full_query}

=== INSTRUCTIONS ===
1. If the user is GREETING you or CLOSING the chat: Respond briefly and warmly.
2. If TECHNICAL:
   - Provide the solution directly as a Senior Support Engineer.
   - NEVER mention words like "Knowledge Base", "KB", "documentation", "article", or "I checked our files."
   - DO NOT say "I'm not seeing a fix", "I couldn't find a solution", or narrate your search results.
   - If Intent is "followup": 
     - Address the specific feedback. Do NOT repeat failed steps. Use the context to find alternatives.
   - If confidence is HIGH:
     - Provide the solution steps clearly and authoritatively.
   - If confidence is MEDIUM or LOW:
     - Provide a professional technical assessment of why the issue requires a human specialist (e.g., "This scenario moves beyond standard self-service protocols and requires senior administrator analysis.")
     - Mention that you have prepared a ticket (Subject and Topic from DRAFT TICKET DATA) to escalate to the support team for this investigation.
     - ASK the user if they would like to submit this ticket now.
   - DO NOT output ACTION:CREATE_TICKET yet (wait for user confirmation).
3. If they specifically request a ticket/human: Output ACTION:CREATE_TICKET or ACTION:ESCALATE.

Primary goal: Resolve the issue directly and naturally.
"""
    try:
        raw_response = oci_genai.get_chat_response(
            prompt=final_prompt,
            system_prompt=CHATBOT_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=2500
        )
    except Exception as e:
        raw_response = f"I'm experiencing connectivity issues. Please try again. (Error: {e})"
    action_taken = None
    ticket_id_created = None

    if "ACTION:CREATE_TICKET" in raw_response:
        raw_response = raw_response.replace("ACTION:CREATE_TICKET", "").strip()
        action_taken = "create_ticket"
        
        if state.active_issue_id:
            snapshot = state.issue_snapshots.get(state.active_issue_id)
            if snapshot:
                snapshot["bot_guidance"].append(raw_response)
                snapshot["timeline"].append({"role": "assistant", "content": raw_response})
                result["ticket_data"] = handoff_agent.summarize(snapshot)
        
        if not result.get("ticket_data"):
             result["ticket_data"] = extract_ticket_data(full_query, history)

    elif "ACTION:ESCALATE" in raw_response:
        raw_response = raw_response.replace("ACTION:ESCALATE", "").strip()
        escalation_result = _handle_escalation(user_message, user_email, history, first_name, {})
        raw_response = escalation_result["content"]
        action_taken = "escalate"
        ticket_id_created = escalation_result.get("ticket_id")
        
        # Clear session state on escalation
        state.state = S["IDLE"]
        state.active_issue_id = None

    result["content"] = raw_response
    result["action"] = action_taken
    result["ticket_id"] = ticket_id_created
    if state.active_issue_id:
        if decision["message_type"] in ["technical", "followup", "escalate_request", "clarification_response"]:
            state.state = "AWAITING_CONFIRMATION"
    
    result["state"] = state.state
    result["issue_id"] = state.active_issue_id

    if state.active_issue_id:
        snapshot = state.issue_snapshots.get(state.active_issue_id)
        if snapshot:
            snapshot["confidence"] = result["confidence"]
            snapshot["bot_guidance"].append(result["content"])
            snapshot["timeline"].append({"role": "assistant", "content": result["content"]})
            
            if result["confidence"] == "high" and "kb_data" in locals():
                best_hit = kb_data.get("kb_results", [{}])[0]
                title = best_hit.get("title", "")
                if title and title not in snapshot["troubleshooting_steps"]:
                    snapshot["troubleshooting_steps"].append(title)

    log.info("== Response complete: intent=%s action=%s confidence=%s ==",
             result["intent"], result["action"], result["confidence"])
    return result

def close_issue_session(email_or_id: str, issue_id: str):
    """Closes an issue session and clears state."""
    state = continuity_agent.get_state(email_or_id)
    if state.active_issue_id == issue_id:
        state.active_issue_id = None
        state.state = "IDLE"
        state.pending_automation = None
        log.info("Issue session closed: %s for %s", issue_id, email_or_id)

def get_issue_snapshot(email_or_id: str, issue_id: str) -> Optional[dict]:
    """Retrieves the snapshot for a specific issue ID."""
    state = continuity_agent.get_state(email_or_id)
    return state.issue_snapshots.get(issue_id)

def _handle_escalation(user_message: str, user_email: str, history: list, first_name: str, result: dict) -> dict:
    """Handles escalation to a human agent."""
    result = dict(result)  # copy

    if user_email and user_email != 'unknown':
        try:
            from tools import escalate_to_human
            esc_result = escalate_to_human(
                reason=user_message,
                email=user_email,
                chat_history=history
            )
            ticket_id = esc_result.get("ticket_id", "N/A")
            result["content"] = (
                f"I've escalated this to a human technician, {first_name}.\n\n"
                f"**Escalation Reference:** {ticket_id}\n\n"
                f"A support agent will review your case and reach out to you at **{user_email}** shortly. "
                f"You can also check your ticket status using the ID above."
            )
            result["action"] = "escalate"
            result["ticket_id"] = ticket_id
        except Exception as e:
            result["content"] = (
                f"I wasn't able to escalate automatically right now (error: {e}). "
                f"Please use the **Submit Ticket** form and a technician will help you shortly."
            )
    else:
        result["content"] = (
            f"I'd like to escalate this for you, {first_name}, but I don't have your contact email. "
            f"Please use the **Submit Ticket** form or log in to continue."
        )
    return result

def _format_history_for_prompt(history: list, max_turns: int = 6) -> str:
    """Formats recent chat history into a string for the prompt."""
    if not history:
        return ""
    recent = history[-max_turns * 2:]  # last N full turns
    lines = []
    for msg in recent:
        role = "User" if msg['role'] == 'user' else "Assistant"
        content = msg['content'][:400]  # Truncate long messages
        lines.append(f"{role}: {content}")
    return "CONVERSATION HISTORY\n" + "\n".join(lines)
