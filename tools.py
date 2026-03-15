
import random
import time
import controller 
# Import controller to access DB (ensure circular imports are handled if any, 
# though tools.py is usually a leaf or main imports it. 
# Safe to import inside functions if needed, but top level is fine here as main.py imports tools)

def check_server_status(server_name):
    """
    Checks the health status of a specific server.
    """
    statuses = ["Online", "Offline", "Maintenance", "Degraded"]
    status = random.choice(statuses)
    latency = random.randint(10, 500)
    return {"server": server_name, "status": status, "latency": f"{latency}ms"}

def reset_user_password(email):
    """
    Simulates sending a password reset link to the user.
    """
    # In a real app, this would call an identity provider API
    time.sleep(1) # Simulate delay
    return {"status": "success", "message": f"Password reset link sent to {email}"}

def check_ticket_status(ticket_id):
    """
    Retrieves the current status of a support ticket.
    """
    # Query Real DB
    ticket = controller.get_ticket_by_id(ticket_id)
    
    if ticket:
        return {
            "ticket_id": ticket_id,
            "status": ticket.get("status", "Unknown"),
            "subject": ticket.get("subject", "No Subject"),
            "priority": ticket.get("priority", "Normal"),
            "last_updated": ticket.get("updated_at", "Unknown")
        }
    else:
        return {"error": f"Ticket ID {ticket_id} not found."}

def create_ticket(description, email, priority="Medium"):
    """
    Creates a new support ticket.
    """
    # Use email as user_id if name not available/passed contextually
    user_id = email.split('@')[0] 
    
    try:
        ticket = controller.create_ticket(
            description=description,
            user_id=user_id,
            email=email,
            priority=priority
        )
        return {
            "status": "success",
            "ticket_id": ticket['ticket_id'],
            "message": f"Ticket {ticket['ticket_id']} has been created successfully."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def escalate_to_human(reason, email, chat_history=None):
    """
    Flags the interaction for human review (simulated by creating a high-priority ticket).
    Saves preceding AI chat history to the live chat table if provided.
    """
    user_id = email.split('@')[0]
    description = f"Live Chat Escalation. Reason: {reason}"
    
    try:
        ticket = controller.create_ticket(
            description=description,
            user_id=user_id,
            email=email,
            priority="High",
            ticket_type="Live Chat"
        )
        
        ticket_id = ticket['ticket_id']
        
        # Save preceding history if provided
        if chat_history:
            import database
            for msg in chat_history:
                sender = msg.get('role', 'unknown')
                content = msg.get('content', '')
                if sender == 'assistant':
                    database.add_chat_message(ticket_id, 'agent', f"[AI History] {content}")
                elif sender == 'user':
                    database.add_chat_message(ticket_id, 'user', content)

        # Force Assignment if not assigned by controller
        if not ticket.get('assigned_agent_id'):
            import agent_manager
            import database
            agent_id = agent_manager.assign_agent(ticket)
            if agent_id:
                database.update_ticket(ticket_id, assigned_agent_id=agent_id, status='Open')
                ticket['assigned_agent_id'] = agent_id 

        return {
            "status": "success",
            "ticket_id": ticket_id,
            "message": f"I have escalated this issue to a human agent. Escalation Ref: {ticket_id}"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Registry of available tools for the AI
AVAILABLE_TOOLS = [
    {
        "name": "check_server_status",
        "description": "Check the health status of a specific server.",
        "parameters": {
            "type": "object",
            "properties": {
                "server_name": {
                    "type": "string",
                    "description": "The name or hostname of the server (e.g., 'web-01', 'db-prod')"
                }
            },
            "required": ["server_name"]
        }
    },
    {
        "name": "reset_user_password",
        "description": "Send a password reset link to a user's email address.",
        "parameters": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "The email address of the user."
                }
            },
            "required": ["email"]
        }
    },
    {
        "name": "check_ticket_status",
        "description": "Get the current status of a support ticket.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "The ticket ID (e.g., 'TKT-2023...')"
                }
            },
            "required": ["ticket_id"]
        }
    },
    {
        "name": "create_ticket",
        "description": "Create a new support ticket for the user. Use this when the user explicitly asks to open a ticket or reports a new issue that requires tracking.",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "A comprehensive description of the issue."
                },
                "email": {
                    "type": "string",
                    "description": "The email address of the user."
                },
                "priority": {
                    "type": "string",
                    "enum": ["Low", "Medium", "High", "Critical"],
                    "description": "The priority level of the ticket. Default to Medium if not specified, High if urgent."
                }
            },
            "required": ["description", "email"]
        }
    },
    {
        "name": "escalate_to_human",
        "description": "Escalate the conversation to a human agent when the user is frustrated, asks for a human, or the issue is too complex.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "The reason for escalation."
                },
                "email": {
                    "type": "string",
                    "description": "The email address of the user."
                }
            },
            "required": ["reason", "email"]
        }
    }
]

def execute_tool(tool_name, params):
    """
    Executes the tool function based on the name.
    """
    if tool_name == "check_server_status":
        return check_server_status(params.get("server_name"))
    elif tool_name == "reset_user_password":
        return reset_user_password(params.get("email"))
    elif tool_name == "check_ticket_status":
        return check_ticket_status(params.get("ticket_id"))
    elif tool_name == "create_ticket":
        return create_ticket(params.get("description"), params.get("email"), params.get("priority", "Medium"))
    elif tool_name == "escalate_to_human":
        return escalate_to_human(params.get("reason"), params.get("email"))
    else:
        return {"error": f"Tool '{tool_name}' not found."}
