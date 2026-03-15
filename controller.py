
import database
import uuid
import pandas as pd
from auto_tagging import predict_topic, predict_severity
from sla_manager import get_sla_status
from datetime import datetime
import agent_manager

def create_ticket(description, user_id, email, priority="Medium", topic=None, instance=None, ticket_type="Standard"):
    """
    Creates a new ticket with auto-tagging.
    Returns the created ticket dictionary.
    """
    # Auto-tagging if not provided
    if not topic:
        topic = predict_topic(description)
        
    predicted_priority = predict_severity(description)
    final_priority = predicted_priority if predicted_priority else priority
    
    # Generate ID based on source
    # Format: AIYYYYMMDDHHMM (for AI/Chat) or YYYYMMDDHHMM (for Standard)
    now_str = datetime.now().strftime('%Y%m%d%H%M%S') # precise datetime
    
    if ticket_type == "Live Chat" or ticket_type == "AI Assessment":
        # Format: AI<datetime> (as requested)
        ticket_id = f"AI{now_str}"
    else:
        # Format: <datetime> (as requested)
        ticket_id = f"{now_str}"
    
    # Check for duplicate (unlikely with seconds, but good practice) or add suffix if needed
    # ticket_id += f"-{uuid.uuid4().hex[:4].upper()}" # Remove UUID suffix to strictly follow request?
    # User asked for "datetime" ID. Let's keep it simple but adding a small random suffix prevents collision if 2 tickets in 1 sec.
    # User request: "like AIdatetime... if ticket is submitted the ticket id be datetime"
    # I will stick to the request but maybe add a small random suffix if collision control is needed, but for now exact request.
    # Actually, adding a random digit is safer.
    # But let's stick to the request: "AIdatetime" / "datetime"
    pass
    
    # SLA calculation (mock for now, usually done on retrieval or background job)
    resolution_time = "24 Hours" # Default
    
    ticket_data = {
        "ticket_id": ticket_id,
        "description": description,
        "topic": topic,
        "priority": final_priority,
        "status": "Open",
        "resolution_time": resolution_time,
        "user_id": user_id,
        "email": email,
        "instance": instance,
        "ticket_type": ticket_type,
        "created_at": datetime.now().isoformat(' ', 'seconds'),
        "updated_at": datetime.now().isoformat(' ', 'seconds')
    }
    
    # Assign Agent
    assigned_agent_id = agent_manager.assign_agent(ticket_data)
    ticket_data['assigned_agent_id'] = assigned_agent_id
    
    # Check Escalation Rules
    import escalation_manager
    is_escalated, reason = escalation_manager.evaluate_escalation(ticket_data)
    
    if is_escalated:
        # All tickets remain 'Open' - escalation is flagged via escalation_reason field
        # Escalation logic is independent of status now
        ticket_data['escalation_reason'] = reason
        # Status always starts as 'Open' regardless of escalation 
        # Optionally re-assign to a 'Human Queue' or specific Level 2 agent?
        # For now, we adjust status logic as requested.
    
    database.save_ticket(ticket_data)
    return ticket_data

def get_dashboard_data():
    """
    Returns a DataFrame configured for the dashboard.
    Adds SLA status and Agent Name columns, and normalizes statuses.
    """
    df = database.get_tickets_summary_df()
    
    if df.empty:
        return df
    
    def normalize_status(s):
        """Convert all legacy statuses to standard 3-status system: Open, In Progress, Closed"""
        if s is None:
            return 'Open'
        
        s = str(s).strip().lower()
        
        # Map all variants to the standard 3 statuses
        if s in ['closed', 'resolved', 'completed', 'solved']:
            return 'Closed'
        elif s in ['in progress', 'inprogress', 'in_progress', 'pending']:
            return 'In Progress'
        elif s in ['open', 'assigned', 'escalated', 'new']:
            return 'Open'
        else:
            return 'Open'
    
    if 'status' in df.columns:
        df['status'] = df['status'].apply(normalize_status)
        
    # Map Agent IDs to Names
    # Fetch agents to map IDs to Names
    try:
        agents = database.get_all_agents()
        # Create dictionary: {agent_id: agent_name}
        agent_map = {a['agent_id']: a['name'] for a in agents}
        
        if 'assigned_agent_id' in df.columns:
             # Map agent IDs to names, with special handling for AI
             df['assigned_agent'] = df['assigned_agent_id'].apply(
                 lambda x: 'AI Assistant' if x == 'AI_ASSISTANT' else agent_map.get(x, 'Unassigned')
             )
        else:
             df['assigned_agent'] = 'Unassigned'
    except Exception as e:
        print(f"Error mapping agents: {e}")
        df['assigned_agent'] = 'Unassigned'

    # Calculate SLA status for each row
    if not df.empty:
        def compute_sla(row):
            # 'created_at' should be a string from DB or datetime
            created = row.get('created_at', row.get('timestamp'))
            priority = row.get('priority', row.get('severity'))
            status_val = row.get('status', 'Open')
            updated = row.get('updated_at')
            
            sla = get_sla_status(created, priority, status_val, updated)
            return sla['time_remaining']

        def compute_sla_status(row):
            created = row.get('created_at', row.get('timestamp'))
            priority = row.get('priority', row.get('severity'))
            status_val = row.get('status', 'Open')
            updated = row.get('updated_at')
            
            sla = get_sla_status(created, priority, status_val, updated)
            return sla['status']

        df['SLA Time Remaining'] = df.apply(compute_sla, axis=1)
        df['SLA Status'] = df.apply(compute_sla_status, axis=1)

    return df

def get_ticket_by_id(ticket_id):
    """Retrieves a single ticket efficiently using a direct database query."""
    return database.get_ticket_by_id(ticket_id)

def update_ticket_status(ticket_id, new_status):
    """Updates the status of a ticket."""
    ticket = get_ticket_by_id(ticket_id)
    if ticket:
        ticket['status'] = new_status
        database.save_ticket(ticket)
        return True
    return False

def update_ticket(ticket_data):
    """Updates or saves a ticket via the database."""
    database.save_ticket(ticket_data)
    return True

def promote_ticket_to_kb(ticket_id, technician_name="Technician"):
    """
    Promotes a resolved ticket to the Knowledge Base as a Markdown article.
    """
    import os
    import rag_manager
    from utils import strip_html
    
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        return False, "Ticket not found."
    
    chat_history = database.get_chat_history(ticket_id)
    
    resolution_summary = "No resolution details found in chat."
    if chat_history:
        resolution_summary = rag_manager.summarize_ticket(chat_history)
    
    subject = ticket.get('subject') or 'No Subject'
    description = strip_html(ticket.get('description', 'No description.'))
    date_str = datetime.now().strftime('%Y-%m-%d')
    topic = ticket.get('topic', 'General')
    
    md_content = f"""# {subject}

**Date:** {date_str}
**Category:** {topic}
**Ticket ID:** {ticket_id}
**Verified By:** {technician_name}

## Problem Description
{description}

## Verified Resolution
{resolution_summary}

---
*This article was automatically promoted from a resolved support ticket.*
"""

    try:
        source_id = f"ticket_{ticket_id}"
        article_data = {
            "title": f"{subject} [Ticket: {ticket_id}]",
            "body": md_content,
            "category": "Solved Ticket",
            "source_id": source_id
        }
        database.save_kb_article(article_data)
        
        # Switching back to the fast method so technicians aren't waiting for a full scan.
        rag_manager.ingest_individual_article(article_data)
        
        return True, f"Successfully promoted to KB (Database ID: {ticket_id})"
    except Exception as e:
        return False, f"Failed to save to database: {str(e)}"

def remove_ticket_from_kb(ticket_id):
    """
    Removes a promoted ticket article from both the KB database and AI vector store.
    """
    import rag_manager
    source_id = f"ticket_{ticket_id}"
    article = database.get_kb_article_by_source(source_id)
    if not article:
        return False, "Article not found in KB."
    
    try:
        database.delete_kb_article(article['id'])
        
        rag_manager.delete_document(f"db_art_{article['id']}")
        
        return True, "Successfully removed from Knowledge Base."
    except Exception as e:
        return False, f"Error during removal: {str(e)}"
