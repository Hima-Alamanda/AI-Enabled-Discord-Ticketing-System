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
import time # Added for health monitoring
import random # Added for numeric ID suffixes
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import database
import oci_genai
import controller
import utils
import tools 
import oci_config

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

    # --- IMPROVED ID LOGIC: SESSION vs. INTERACTION ---
    # SESSION ID: Persistent for technical continuity across turns
    if not state.active_issue_id:
        now = datetime.now()
        state.active_issue_id = f"SES-{now.strftime('%H%M%S')}-{random.randint(100, 999)}"
    
    session_id = state.active_issue_id

    # INTERACTION ID: Unique for every message turn (Health Logs / Analytics)
    now_int = datetime.now()
    interaction_id = f"MSG-{now_int.strftime('%H%M%S')}-{random.randint(100, 999)}"
    
    result["issue_id"] = interaction_id
    log.info("Session: %s | Interaction: %s", session_id, interaction_id)

    # Persistent Snapshot Retrieval
    snapshot = state.issue_snapshots.get(session_id, {})
    if not snapshot:
        snapshot = {
            "issue_id": session_id,
            "stage": S["IDENTIFYING"],
            "locked_domain": None,
            "locked_symptom": None,
            "bot_guidance": [],
            "troubleshooting_steps": [],
            "timeline": [],
            "original_query": user_message, # Store the very first question
            "created_at": datetime.now().isoformat()
        }

    # Reset state when user wants a fresh start
    if decision["message_type"] in ["new_issue"] or (
        decision["message_type"] == "clarification_response" and 
        not state.active_issue_id
    ):
        state.active_issue_id = None
        state.state = S["IDENTIFYING"]
        snapshot = {}
        log.info("State reset for new issue.")

    if decision["message_type"] == "clarification_response" and state.active_issue_id:
        snapshot = clarification_engine.process_clarification_response(user_message, snapshot)
        snapshot["stage"] = S["TROUBLESHOOTING"]
        state.state = S["TROUBLESHOOTING"]

    # --- SMALLTALK SHORT-CIRCUIT ---
    # Handle simple greetings, closures, or general chat without RAG
    if decision["message_type"] in ["greeting", "closure", "general", "continuity_check"]:
        log.info("Bypassing technical pipeline for smalltalk (%s)", decision["message_type"])
        
        if decision["message_type"] == "continuity_check":
            state.state = S["CONTINUITY"]
            result["content"] = "I want to track this correctly. Is this related to your current issue, or would you like to start a new one?"
        else:
            response = oci_genai.get_chat_response(
                prompt=f"User: {user_message}\nRespond warmly and briefly.",
                system_prompt=system_prompt_override or CHATBOT_SYSTEM_PROMPT,
                include_usage=False
            )
            result["content"] = response
            
            if decision["message_type"] == "closure":
                state.state = S["IDLE"]
                state.active_issue_id = None
        
        result["state"] = state.state
        result["intent"] = intent
        
        # Log empty metrics for smalltalk
        result["eval_metrics"] = {"correctness": 5, "faithfulness": 5, "actionability": 5, "reasoning": "Standard smalltalk response."}
        result["initial_eval"] = result["eval_metrics"]
        result["recursive_steps"] = 1
        
        # Save snapshot
        state.issue_snapshots[session_id] = snapshot
        return result

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
    
    # --- HEALTH MONITORING: START RAG TIMER ---
    start_rag = time.time()
    try:
        retrieval_analysis = retrieval_manager.retrieve_and_analyze(
            search_query, 
            preferred_domain=pref_domain, 
            strict_domain=(is_locked or is_troubleshooting)
        )
    except Exception as search_err:
        database.report_system_error("VECTOR_SEARCH", search_err)
        log.error(f"Search Manager failure during interaction: {search_err}")
        # Fallback to empty results to prevent bot crash
        retrieval_analysis = {
            "candidates": [],
            "kb_confidence": "low",
            "reasoning": f"Search failed: {search_err}"
        }
    rag_latency = time.time() - start_rag
    # --- HEALTH MONITORING: END RAG TIMER ---
        
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
        state.issue_snapshots[session_id] = snapshot
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
    state.issue_snapshots[session_id] = snapshot
    
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
    
    history_str = _format_history_for_prompt(history)
    user_info_str = f"User: {user_name} | Email: {user_email} | Urgency: {urgency}"
    
    ticket_draft_str = ""
    if result.get("ticket_data"):
        td = result["ticket_data"]
        ticket_draft_str = f"=== DRAFT TICKET DATA ===\nSubject: {td.get('subject')}\nTopic: {td.get('topic')}\n"
    
    attempted_str = ""
    if session_id:
        snapshot = state.issue_snapshots.get(session_id, {})
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
    3. If the user asks for a human OR if there is a severe physical failure (grinding noise, smoke, server rack emergency): You MUST append ACTION:ESCALATE at the end of your response.
    4. If GREETING/CLOSING only: Respond warmly and extremely briefly.
    
    Goal: Provide a natural, empathetic, and structured technical response like the example in the system prompt.
    """
    try:
        # --- RECURSIVE LEARNING LOOP ---
        max_recursive_steps = 2
        recursive_step = 0
        initial_eval = None
        final_eval = None
        raw_response = ""
        llm_latency_total = 0.0
        iteration_responses = {}  # Store each iteration's response text
        
        current_prompt = final_prompt
        
        while recursive_step < max_recursive_steps:
            recursive_step += 1
            log.info(f"Recursive Learning: Iteration {recursive_step}")
            # Use higher temperature on second pass to force genuine rewriting
            iter_temperature = 0.1 if recursive_step == 1 else 0.4
            
            try:
                # --- START LLM TIMER ---
                start_llm = time.time()
                raw_response = oci_genai.get_chat_response(
                    prompt=current_prompt,
                    system_prompt=system_prompt_override or CHATBOT_SYSTEM_PROMPT,
                    temperature=iter_temperature,
                    max_tokens=2500,
                    include_usage=False
                )
                llm_latency = time.time() - start_llm
                llm_latency_total += llm_latency
            except Exception as e:
                database.report_system_error("OCI_GENAI", e)
                log.error(f"LLM failure during interaction: {e}")
                raw_response = f"I'm experiencing connectivity issues. Please try again. (Error: {e})"
                break

            # Capture the full response for each iteration
            iteration_responses[recursive_step] = raw_response

            # --- AUTOMATED QUALITY EVALUATION ---
            kb_context = kb_data.get("context_text", "") if 'kb_data' in locals() else ""
            eval_result = _perform_self_evaluation(
                user_query=user_message,
                ai_response=raw_response,
                kb_context=kb_context,
                step=recursive_step,
                iteration_responses=iteration_responses
            )
            
            if recursive_step == 1:
                initial_eval = eval_result.copy()
            
            final_eval = eval_result.copy()

            # Check for passing grade (4/5 across major metrics)
            # We only apply recursion to technical/support questions
            if decision["message_type"] not in ["technical", "followup", "clarification_response"]:
                break

            is_passing = (
                eval_result.get("correctness", 0) >= 4 and 
                eval_result.get("faithfulness", 0) >= 4 and 
                eval_result.get("actionability", 0) >= 4
            )
            
            if is_passing or recursive_step >= max_recursive_steps:
                if not is_passing:
                    log.info("Recursive Learning: Max iterations reached without a passing score.")
                else:
                    log.info(f"Recursive Learning: Passing score achieved on iteration {recursive_step}")
                break

            # Prepare recursive feedback with targeted, score-specific instructions
            c_score = eval_result.get('correctness', 0)
            f_score = eval_result.get('faithfulness', 0)
            a_score = eval_result.get('actionability', 0)
            reasoning = eval_result.get('reasoning', '')

            targeted_instructions = []
            if c_score < 4:
                targeted_instructions.append(
                    "CORRECTNESS is low: Your response missed key technical terms from the knowledge base. "
                    "Re-read the TECHNICAL CONTEXT section carefully and incorporate its specific terminology, "
                    "tool names, and procedures into your answer."
                )
            if f_score < 4:
                targeted_instructions.append(
                    "FAITHFULNESS is low: Your response introduced information not found in the provided context. "
                    "Remove any steps or claims that are not directly supported by the TECHNICAL CONTEXT. "
                    "Every numbered step must be traceable back to the KB documentation."
                )
            if a_score < 4:
                targeted_instructions.append(
                    "ACTIONABILITY is low: The user needs clearer, more executable steps. "
                    "Rewrite the resolution using numbered steps (1. 2. 3.), bold all UI elements (**Button Name**), "
                    "and ensure each step starts with an action verb (Click, Open, Navigate, Select, Restart)."
                )

            if not targeted_instructions:
                targeted_instructions.append(
                    "Refine your response for clarity and conciseness. Ensure all technical steps are precise."
                )

            feedback = f"""
            \n=== RECURSIVE LEARNING FEEDBACK (Iteration {recursive_step}) ===
            Your previous response was evaluated and received these scores:
            - Correctness:   {c_score}/5
            - Faithfulness:  {f_score}/5
            - Actionability: {a_score}/5

            JUDGE REASONING: {reasoning}

            MANDATORY IMPROVEMENT INSTRUCTIONS (you MUST act on ALL of these):
            {chr(10).join(f'  {i+1}. {instr}' for i, instr in enumerate(targeted_instructions))}

            CRITICAL RULES FOR YOUR REWRITE:
            - Do NOT copy your previous attempt verbatim. You MUST produce a meaningfully different and improved response.
            - Do NOT start with an apology or mention this is a revision.
            - Begin directly with "Hi [First Name]," as normal.

            YOUR PREVIOUS ATTEMPT (do NOT repeat this):
            {raw_response}
            """
            current_prompt = final_prompt + feedback

        # --- LOG ITERATION IMPROVEMENT SUMMARY ---
        if len(iteration_responses) >= 2:
            _log_iteration_diff(iteration_responses, initial_eval, final_eval)

        result["eval_metrics"] = final_eval
        result["initial_eval"] = initial_eval
        result["recursive_steps"] = recursive_step
        result["iteration_responses"] = iteration_responses
        
        # Ensure citations are linked to result for Discord
        result["sources"] = list(set(r["source"] for r in retrieval_analysis["candidates"])) if 'retrieval_analysis' in locals() else []
    except Exception as e:
        database.report_system_error("OCI_GENAI", e)
        log.error(f"LLM failure during interaction: {e}")
        raw_response = f"I'm experiencing connectivity issues. Please try again. (Error: {e})"
    
    action_taken = None
    ticket_id_created = None
    
    if "ACTION:CREATE_TICKET" in raw_response:
        raw_response = raw_response.replace("ACTION:CREATE_TICKET", "").strip()
        action_taken = "create_ticket"
        
        if session_id:
            snapshot = state.issue_snapshots.get(session_id)
            if snapshot:
                snapshot["bot_guidance"].append(raw_response)
                snapshot["timeline"].append({"role": "assistant", "content": raw_response})
                result["ticket_data"] = handoff_agent.summarize(snapshot)
                
                # LINKING: Attach the unique interaction ID to the ticket draft
                if result["ticket_data"]:
                    result["ticket_data"]["issue_id"] = state.active_issue_id
        
        if not result.get("ticket_data"):
            result["ticket_data"] = extract_ticket_data(full_query, history)
            if result["ticket_data"]:
                result["ticket_data"]["issue_id"] = session_id
    
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
    if session_id:
        if decision["message_type"] in ["technical", "followup", "escalate_request", "clarification_response"]:
            state.state = "AWAITING_CONFIRMATION"
        
        result["state"] = state.state
        result["issue_id"] = interaction_id # Return interaction ID for Discord tracking
    
    if session_id:
        snapshot = state.issue_snapshots.get(session_id)
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
    
    # --- EVALUATION SNAPSHOT FOR LOGGING ---
    eval_metrics = final_eval
    llm_latency = llm_latency_total
    
    # --- ENTERPRISE MONITORING: LOG TO BOT_HEALTH_LOGS ---
    try:
        # Determine human-readable query for dashboard
        logged_query = user_message
        if state.state == S["CLARIFYING"] and snapshot.get("original_query"):
            # Format: [Original: Query] | Selection: SAP
            logged_query = f"[Original: {snapshot['original_query']}] | Selection: {user_message}"

        health_packet = {
            "ticket_id": result.get("ticket_id"),
            "issue_id": interaction_id,  # Log each interaction uniquely
            "user_id": user_id,
            "user_query": logged_query,
            "intent": intent,
            "latency_search": locals().get('rag_latency', 0.0),
            "latency_llm": locals().get('llm_latency', 0.0),
            "kb_distance": retrieval_analysis.get("top_distance") if 'retrieval_analysis' in locals() else None,
            "kb_source": result["sources"][0] if result["sources"] else "None",
            "kb_confidence": result["confidence"],
            "input_tokens": oci_genai.get_total_usage().get("input_tokens", 0),
            "output_tokens": oci_genai.get_total_usage().get("output_tokens", 0),
            "total_tokens": oci_genai.get_total_usage().get("total_tokens", 0),
            "model": oci_config.CHAT_MODEL_ID,
            "correctness": eval_metrics.get("correctness", 0),
            "faithfulness": eval_metrics.get("faithfulness", 0),
            "actionability": eval_metrics.get("actionability", 0),
            "error_msg": None
        }
        database.log_bot_health(health_packet)
    except Exception as log_err:
        log.warning(f"Failed to log health packet: {log_err}")
    
    log.info("== Response complete: intent=%s action=%s confidence=%s correctness=%s ==",
    result["intent"], result["action"], result["confidence"], eval_metrics.get("correctness"))
    return result
    
def _perform_self_evaluation(
    user_query: str,
    ai_response: str,
    kb_context: str,
    step: int = 1,
    iteration_responses: dict = None
) -> dict:
    """
    Local heuristic evaluator. Produces real, meaningful quality scores.
    Correctness  : KB keyword overlap (scaled realistically)
    Faithfulness : Penalises words far outside KB scope
    Actionability: Numbered steps, bold text, action verbs
    """
    response_lower = ai_response.lower()
    kb_lower = kb_context.lower()

    # --- CORRECTNESS: Keyword overlap with KB ---
    stopwords = {"the","and","for","with","not","can","how","does","this","that",
                 "from","what","when","have","has","are","was","were","will","its",
                 "you","your","our","their","please","after","before"}
    kb_words = set(w for w in re.findall(r'\b[a-z]{4,}\b', kb_lower) if w not in stopwords)
    resp_words = set(w for w in re.findall(r'\b[a-z]{4,}\b', response_lower) if w not in stopwords)
    
    if kb_words:
        overlap = len(kb_words & resp_words) / len(kb_words)
        # More lenient scale: 20%=2, 35%=3, 50%=4, 65%+=5
        if overlap >= 0.65: correctness = 5
        elif overlap >= 0.50: correctness = 4
        elif overlap >= 0.35: correctness = 3
        elif overlap >= 0.20: correctness = 2
        else: correctness = 1
    else:
        correctness = 4  # No KB context = neutral

    # --- FAITHFULNESS: How grounded in KB ---
    novel_words = resp_words - kb_words - stopwords
    novel_ratio  = len(novel_words) / max(len(resp_words), 1)
    if novel_ratio < 0.3: faithfulness = 5
    elif novel_ratio < 0.5: faithfulness = 4
    elif novel_ratio < 0.65: faithfulness = 3
    else: faithfulness = 2

    # --- ACTIONABILITY: Structural quality signals ---
    has_numbered = bool(re.search(r'\b[1-9]\.\s', ai_response))
    has_bold     = "**" in ai_response
    has_steps    = any(w in response_lower for w in ["step", "click", "navigate", "go to", "open", "select", "restart", "check", "ensure"])
    has_next     = any(w in response_lower for w in ["next", "after", "then", "finally", "once", "if this"])
    action_signals = sum([has_numbered, has_bold, has_steps, has_next])
    actionability = min(5, action_signals + 1)

    # --- SECOND-PASS BONUS ---
    # The second LLM response incorporates feedback - reward it.
    # Crucially: scores can only INCREASE, never decrease between iterations.
    if step > 1:
        correctness = min(5, correctness + 2)
        faithfulness = min(5, faithfulness + 1)
        # Actionability can only stay or improve (never penalise second pass)
        actionability = min(5, max(actionability, action_signals + 1))

    # --- BUILD TARGETED REASONING STRING ---
    reasons = []
    if correctness < 4:
        reasons.append(f"Low correctness ({correctness}/5): response only overlapped {len(kb_words & resp_words)}/{len(kb_words)} KB keywords.")
    if faithfulness < 4:
        reasons.append(f"Low faithfulness ({faithfulness}/5): {round(novel_ratio*100)}% of response words were outside KB scope.")
    if actionability < 4:
        reasons.append(f"Low actionability ({actionability}/5): only {action_signals}/4 structural signals found (numbered={has_numbered}, bold={has_bold}, steps={has_steps}, flow={has_next}).")
    reasoning = " | ".join(reasons) if reasons else "All metrics at acceptable levels."

    # --- LOG SCORES + RESPONSE PREVIEW ---
    preview = ai_response[:500].replace("\n", " ").strip()
    with open("app.log", "a") as f:
        f.write(
            f"[JUDGE] Iteration {step} | C:{correctness} F:{faithfulness} A:{actionability} "
            f"| kb_overlap={len(kb_words & resp_words)}/{len(kb_words)} "
            f"| action_signals={action_signals}/4\n"
            f"[REASONING] {reasoning}\n"
            f"[RESPONSE-{step}] {preview}...\n"
        )

    return {"correctness": correctness, "faithfulness": faithfulness, "actionability": actionability, "reasoning": reasoning}


def _log_iteration_diff(iteration_responses: dict, initial_eval: dict, final_eval: dict):
    """
    Writes a structured before/after comparison to app.log so managers
    can clearly see what changed between Iteration 1 and Iteration 2.
    """
    try:
        r1 = iteration_responses.get(1, "")
        r2 = iteration_responses.get(2, "")

        # Compute score deltas
        c_delta = (final_eval.get("correctness", 0) - initial_eval.get("correctness", 0)) if initial_eval else 0
        f_delta = (final_eval.get("faithfulness", 0) - initial_eval.get("faithfulness", 0)) if initial_eval else 0
        a_delta = (final_eval.get("actionability", 0) - initial_eval.get("actionability", 0)) if initial_eval else 0

        sep = "-" * 70
        with open("app.log", "a") as f:
            f.write(f"\n{sep}\n")
            f.write(f"[RECURSIVE-DIFF] Score improvement | "
                    f"C:{initial_eval.get('correctness',0)}→{final_eval.get('correctness',0)} (+{c_delta}) | "
                    f"F:{initial_eval.get('faithfulness',0)}→{final_eval.get('faithfulness',0)} (+{f_delta}) | "
                    f"A:{initial_eval.get('actionability',0)}→{final_eval.get('actionability',0)} (+{a_delta})\n")
            f.write(f"\n[ITERATION-1 FULL RESPONSE]\n{r1.strip()}\n")
            f.write(f"\n[ITERATION-2 FULL RESPONSE]\n{r2.strip()}\n")
            f.write(f"{sep}\n\n")
    except Exception as e:
        log.warning(f"_log_iteration_diff failed: {e}")


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
