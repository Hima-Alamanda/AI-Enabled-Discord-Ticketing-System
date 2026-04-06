
import random
import time
import controller 
import database
import visualizer
import json

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
            agent_id = agent_manager.assign_agent(ticket)
            if agent_id:
                ticket['assigned_agent_id'] = agent_id
                ticket['status'] = 'Open'
                controller.update_ticket(ticket)

        return {
            "status": "success",
            "ticket_id": ticket_id,
            "message": f"I have escalated this issue to a human agent. Escalation Ref: {ticket_id}"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def list_user_tickets(email, status=None):
    """
    Lists all tickets for a specific user. Can be filtered by status.
    """
    try:
        tickets = database.get_user_tickets_summary(email)
        if not tickets:
            return {"message": f"No tickets found for user {email}."}
        
        if status:
            tickets = [t for t in tickets if t.get('status', '').lower() == status.lower()]
            if not tickets:
                return {"message": f"No tickets found for user {email} with status '{status}'."}

        # Return a clean summary
        summary = []
        for t in tickets:
            summary.append({
                "ticket_id": t['ticket_id'],
                "subject": t['subject'],
                "status": t['status'],
                "priority": t['priority'],
                "created_at": str(t['created_at'])
            })
        return {"tickets": summary}
    except Exception as e:
        return {"error": str(e)}

def visualize_data(labels, values, title="User Dashboard", chart_type="bar"):
    """
    Generates a chart from provided data. Used for Interactive Analysis.
    """
    try:
        if chart_type == "bar":
            path = visualizer.create_bar_chart(labels, values, title)
        elif chart_type == "pie":
            path = visualizer.create_pie_chart(labels, values, title)
        elif chart_type == "line":
            path = visualizer.create_line_chart(labels, values, title)
        else:
            return {"error": f"Unsupported chart type: {chart_type}"}
        
        return {"image_path": path, "message": f"Generated {chart_type} chart: {title}"}
    except Exception as e:
        return {"error": str(e)}

def generate_ticket_insights(insight_type="status"):
    """
    Generates visual insights from current database tickets.
    insight_type: 'status', 'priority', or 'trends'
    """
    try:
        if insight_type == "status":
            data = database.get_ticket_status_counts()
            path = visualizer.create_pie_chart(list(data.keys()), list(data.values()), "Ticket Status Distribution")
        elif insight_type == "priority":
            data = database.get_ticket_priority_counts()
            path = visualizer.create_bar_chart(list(data.keys()), list(data.values()), "Ticket Volume by Priority")
        elif insight_type == "trends":
            data = database.get_ticket_volume_trends()
            path = visualizer.create_line_chart(list(data.keys()), list(data.values()), "Monthly Ticket Volume Activity")
        else:
            return {"error": "Unsupported insight type."}

        return {"image_path": path, "message": f"Generated {insight_type} insights dashboard."}
    except Exception as e:
        return {"error": str(e)}

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
    },
    {
        "name": "list_user_tickets",
        "description": "List all support tickets for a specific user. Can be filtered by status (Open, Closed, In-Progress).",
        "parameters": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "The user's email address."
                },
                "status": {
                    "type": "string",
                    "description": "Optional status filter (e.g., 'Open', 'Closed')."
                }
            },
            "required": ["email"]
        }
    },
    {
        "name": "visualize_data",
        "description": "Visualize data provided by the user in a chart. Use this when the user gives numerical data and asks for a chart or graph.",
        "parameters": {
            "type": "object",
            "properties": {
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "The names for each data category."
                },
                "values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "The numeric values for each category."
                },
                "title": {
                    "type": "string",
                    "description": "A descriptive title for the chart."
                },
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "pie", "line"],
                    "description": "The type of chart to display."
                }
            },
            "required": ["labels", "values", "title", "chart_type"]
        }
    },
    {
        "name": "generate_ticket_insights",
        "description": "Show visual analytics of tickets stored in the database. Good for showing ticket status, priority trends, or volume.",
        "parameters": {
            "type": "object",
            "properties": {
                "insight_type": {
                    "type": "string",
                    "enum": ["status", "priority", "trends"],
                    "description": "The type of data to visualize."
                }
            },
            "required": ["insight_type"]
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
    elif tool_name == "list_user_tickets":
        return list_user_tickets(params.get("email"), params.get("status"))
    elif tool_name == "visualize_data":
        return visualize_data(params.get("labels"), params.get("values"), params.get("title"), params.get("chart_type", "bar"))
    elif tool_name == "generate_ticket_insights":
        return generate_ticket_insights(params.get("insight_type", "status"))
    else:
        return {"error": f"Tool '{tool_name}' not found."}
