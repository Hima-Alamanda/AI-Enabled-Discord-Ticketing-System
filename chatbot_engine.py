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
import tools 

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

== ANALYTICS & VISUALIZATION CAPABILITIES ==
You are equipped with advanced data analysis and visualization tools:
1. **Interactive Analysis**: If a user provides numerical data (e.g., "Usage: Jan 10, Feb 20") or technical metrics, you can visualize them. You MUST parse the labels and values yourself and call the `visualize_data` tool.
2. **Ticket Insights**: If a user asks about their ticket trends or status distribution, call the `generate_ticket_insights` tool to show them a professional dashboard.
3. **Ticket Management**: You can list all tickets for a user using `list_user_tickets`. Use this when they ask "Show me my tickets" or "What is my ticket status?".

== RESPONSE STYLE ==
To provide a premium and professional "Support Expert" experience, you should follow this structure:

1. **Warm Greeting**: Always start with "Hi [First Name]," when available.
2. **Technical Context & Empathy**: Begin with a brief paragraph (2-3 sentences) identifying the problem and explaining the technical context or likely cause in a conversational but professional way.
3. **Structured Resolution**: Provide clear, numbered steps for the resolution. Use **bold** for buttons, applications, and navigation paths.
4. **Closing**: Finish with a one-sentence closing that offers further help or provides a clear next step if the fix does not work.

== FORMATTING RULES ==
- NO bold section headers like "**Issue Analysis**" or "**Resolution Steps**".
- Use **bold** for technical terms, buttons, and system names.
- Provide a natural flow between explanation and instruction.
- KEEP IT CONCISE. Minimize redundant filler but maintain a professional rapport.

== EXAMPLE TECHNICAL RESPONSE ==
Hi Himanth,

I understand you're experiencing sync errors in your Outlook client. This typically occurs when your stored login credentials in the Windows Credential Manager have become stale or are conflicting with a recent password update.

To resolve this, please follow these steps:

1. Close all your **Office** applications completely.
2. Open the Windows **Control Panel** and navigate to **Credential Manager**.
3. Select **Windows Credentials** and remove all entries beginning with **MicrosoftOffice16**.
4. Restart your **Outlook** and sign in when prompted to re-establish the connection.

If the synchronization issue persists after these steps, please let me know and I can escalate this to the Infrastructure team to reset your profile. Would you like me to proceed?

== GUIDELINES ==
- DIRECT RESOLUTION: Always provide technical solutions directly. Do not narrate where you found the information.
- ROLEPLAY: Act as a support engineer who already knows the solution. Never say "I checked the Knowledge Base" or "According to the documentation."
- ESCALATION REASONING: If a manual fix is not immediately available, provide a professional technical assessment of why the issue requires a human specialist.
- ACTION SIGNALS: 
  - TICKET CREATION: Suggest or output ACTION:CREATE_TICKET ONLY if the user has explicitly confirmed it.
  - RESOLUTION OVER ACTION: Solve the issue directly first before suggesting a ticket.
  - VISUALIZATION: When you call a visualization tool, simply explain what the chart shows in your response. The bot will handle the image upload automatically.
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
    usage_data = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
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

    return {
        "subject": user_message[:60] if user_message else "Technical Support Inquiry",
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
    uploaded_file=None,
    system_prompt_override: str = None
) -> dict:
    """
    Main entry point for the chatbot.
    discord_bot.py calls this and expects: content, sources, confidence,
    action, ticket_id, ticket_data, file_info, intent, issue_id, state.
    """
    # Reset global token counter at the start of each request
    oci_genai.reset_usage()

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

        # Use full_query (msg + OCR) for extraction — now handles its own semantic fallback logic
        current_issue = issue_understanding_agent.extract_issue_fields(full_query, snapshot, history)

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
            else:
                result["content"] = f"I couldn't find ticket **{ticket_id}** in the system."
        else:
            result["content"] = "Please share the ticket ID and I'll look it up for you."
        return result

    # Handle Ticket Listing
    if decision["message_type"] == "list_tickets":
        # Extract email or use current user email
        email = user_context.get('email', 'unknown')
        status_filter = None
        if "open" in user_message.lower(): status_filter = "Open"
        elif "closed" in user_message.lower(): status_filter = "Closed"
        
        tool_res = tools.list_user_tickets(email, status_filter)
        if "tickets" in tool_res and tool_res["tickets"]:
            t_list = tool_res["tickets"]
            text = f"Hi {first_name}, I found **{len(t_list)}** tickets for you:\n\n"
            for t in t_list[:5]: # Top 5
                text += f"- **{t['ticket_id']}**: {t['subject']} ({t['status']})\n"
            if len(t_list) > 5:
                text += f"\n...and {len(t_list)-5} more."
            result["content"] = text
        else:
            result["content"] = tool_res.get("message", "I couldn't find any tickets for your account.")
        return result

    # Handle Visualization & Analytics
    if decision["message_type"] == "visualization":
        # We need the AI to parse the data first.
        # We will use a special system prompt for data extraction.
        data_extractor_prompt = f"""Extract visualization data from this request.
USER: {user_message}

If the user gives data, output JSON for 'visualize_data':
{{ "type": "interactive", "labels": ["Jan", "Feb"], "values": [10, 20], "chart_type": "bar", "title": "My Data" }}

If the user asks for ticket insights (trends, priority, status), output JSON:
{{ "type": "insights", "insight_type": "status" }}

Only return JSON.
"""
        try:
            raw_json = oci_genai.get_chat_response(prompt=data_extractor_prompt, temperature=0.1)
            match = re.search(r'\{.*\}', raw_json, re.DOTALL)
            if match:
                data = json.loads(match.group())
                if data.get("type") == "interactive":
                    v_res = tools.visualize_data(data['labels'], data['values'], data['title'], data.get('chart_type', 'bar'))
                    result["content"] = f"I've generated the **{data.get('chart_type', 'bar')} chart** based on the data you provided."
                    result["image_path"] = v_res.get("image_path")
                else:
                    v_res = tools.generate_ticket_insights(data.get("insight_type", "status"))
                    result["content"] = f"Here is the **{data.get('insight_type', 'status')} analytics** dashboard summarizing your current tickets."
                    result["image_path"] = v_res.get("image_path")
            else:
                result["content"] = "I couldn't understand the data structure for the visualization. Could you please specify labels and values clearly?"
        except Exception as e:
            result["content"] = f"Failed to generate visualization. {e}"
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
            system_prompt=system_prompt_override or CHATBOT_SYSTEM_PROMPT,
            include_usage=False # Usage is now tracked globally
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
1. START with a personalized greeting: "Hi [First Name],".
2. TECHNICAL SUPPORT:
   - Provide a natural, technical context first (Why it is happening).
   - Use a numbered list for resolution steps.
   - Use **bold** for buttons and navigation.
   - NO bold headers (e.g. **Issue Analysis**).
3. If they specifically request escalation: Output ACTION:ESCALATE.
4. If GREETING/CLOSING only: Respond warmly and extremely briefly.

Goal: Provide a natural, empathetic, and structured technical response like the example in the system prompt.
"""
    try:
        raw_response = oci_genai.get_chat_response(
            prompt=final_prompt,
            system_prompt=system_prompt_override or CHATBOT_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=2500,
            include_usage=False # Usage is now tracked globally
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

    # --- TOOL INTERCEPTION LAYER ---
    # Catch cases where the LLM narrates calling a visualization tool
    content_lower = result["content"].lower()
    
    # 1. Insights Interceptor
    if any(x in content_lower for x in ["visualize.generate_ticket_insights", "visualizations.generate_ticket_insights", "generate_ticket_insights"]):
        v_type = "status"
        if "priority" in user_message.lower(): v_type = "priority"
        elif "trend" in user_message.lower() or "volume" in user_message.lower(): v_type = "trends"
        
        try:
            v_res = tools.generate_ticket_insights(v_type)
            if v_res.get("image_path"):
                result["image_path"] = v_res.get("image_path")
                # Clean text: remove tool narration blocks
                result["content"] = re.sub(r'\[calling tool .*?\]', '', result["content"], flags=re.IGNORECASE)
                result["content"] = re.sub(r'<tool_code>.*?</tool_code>', '', result["content"], flags=re.DOTALL | re.IGNORECASE)
                result["content"] = re.sub(r'\[ACTION\].*?\n', '', result["content"], flags=re.IGNORECASE)
        except Exception as ve:
            log.warning(f"Interception tool call failed: {ve}")

    # 2. Interactive Data Interceptor (Fix for User Data multi-line issues)
    elif "visualize_data" in result["content"] or "execute_tool" in result["content"]:
        try:
            # Look for execute_tool block first, then raw python-style call
            tool_block = re.search(r'<execute_tool>(.*?)</execute_tool>', result["content"], re.DOTALL | re.IGNORECASE)
            code = tool_block.group(1).strip() if tool_block else result["content"]
            
            # Use a more flexible parameter extraction
            def get_param(name, text):
                m = re.search(fr"{name}\s*=\s*(['\"](.*?)['\"]|\[.*?\])", text, re.DOTALL)
                return m.group(1).strip("'\"") if m else None

            labels_str = get_param("labels", code)
            values_str = get_param("values", code)
            title = get_param("title", code) or "Data Visualization"
            c_type = get_param("chart_type", code) or "bar"
            
            if labels_str and values_str:
                labels = eval(labels_str)
                values = eval(values_str)
                v_res = tools.visualize_data(labels, values, title, c_type)
                if v_res.get("image_path"):
                    result["image_path"] = v_res.get("image_path")
                    # Clean AND remove the block from user view
                    result["content"] = re.sub(r'<execute_tool>.*?</execute_tool>', '', result["content"], flags=re.DOTALL | re.IGNORECASE)
                    result["content"] = re.sub(r'visualize_data\(.*?\)', '', result["content"], flags=re.DOTALL | re.IGNORECASE)
                    # Also remove any leftover "Here is the chart" text that narrate the error
                    result["content"] = result["content"].replace("```python", "").replace("```", "").strip()
        except Exception as e:
            log.warning(f"Interactive Interceptor failed: {e}")

    # --- AUTOMATED QUALITY EVALUATION (ADMIN TESTING) ---
    eval_metrics = {
        "correctness": 0,
        "faithfulness": 0,
        "actionability": 0,
        "reasoning": "Self-evaluation skipped.",
        "kb_sources": kb_data.get("sources", []) if 'kb_data' in locals() else []
    }
    
    if result["content"]:
        try:
            # We evaluate even if KB wasn't used
            kb_context = kb_data.get("context_text", "") if 'kb_data' in locals() else ""
            eval_result = _perform_self_evaluation(
                user_query=user_message,
                ai_response=result["content"],
                kb_context=kb_context
            )
            eval_metrics.update(eval_result)
        except Exception as eval_err:
            log.warning(f"Self-evaluation failed: {eval_err}")

    result["eval_metrics"] = eval_metrics
    
    log.info("== Response complete: intent=%s action=%s confidence=%s correctness=%s ==",
             result["intent"], result["action"], result["confidence"], eval_metrics.get("correctness"))
    return result

def _perform_self_evaluation(user_query: str, ai_response: str, kb_context: str) -> dict:

    system_prompt = """You are a Quality Assurance Auditor for an AI Support Bot.
Evaluate the AI's response against the user message, context, and ground truth.

Assign a score from 1 (Failure) to 5 (Excellent) for each metric:
- 5 | Excellent: Perfectly correct, clear, and follows all PCB style rules.
- 4 | Good: Correct and helpful; minor wording, tone, or bolding issues.
- 3 | Acceptable: Mostly correct but lacks some detail or professional "polish."
- 2 | Poor: Contains important mistakes, unclear steps, or ignored some instructions.
- 1 | Failure: Incorrect info, misleading advice, or failed to address the query.

Categories:
- Correctness: Technically accurate and follows the 'KB Answer'?
- Faithfulness: Grounded strictly in KB/Context? (No hallucinations)
- Actionability: Clear, easy, numbered steps provided?

Output ONLY a raw JSON object string. Do NOT use markdown code blocks.

Expected Format:
{"correctness": 0, "faithfulness": 0, "actionability": 0}
"""
    prompt = f"QUERY: {user_query}\nKB CONTEXT: {kb_context[:1000]}\nAI RESPONSE: {ai_response}\n\nStrict Evaluation JSON:"

    try:
        raw = oci_genai.get_chat_response(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=800
        )
        # Debugging
        print(f"DEBUG: Judge Response: {raw}")
        
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        log.error(f"Judge evaluation failed: {e}")
    
    return {}

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
