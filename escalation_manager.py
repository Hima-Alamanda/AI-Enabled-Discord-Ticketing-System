
import re

def evaluate_escalation(ticket_data):
    """
    Evaluates a ticket to determine if it should be immediately escalated to a human.
    Returns: (is_escalated: bool, reason: str)
    
    Rules:
    1. CRITICAL Severity -> Always Escalate.
    2. PROD Instance + High Severity -> Always Escalate.
    3. Keywords: "Data Breach", "Wire Transfer", "System Down", "Outage".
    4. Topic specific:
       - Security + "Locked Out"
       - Manufacturing + "Line Down"
       - EDI + "Failure"
    """
    
    severity = ticket_data.get('priority') or 'Medium'
    instance = ticket_data.get('instance') or ''
    topic = ticket_data.get('topic') or ''
    desc = (ticket_data.get('description') or '').lower()
    subject = (ticket_data.get('subject') or '').lower()
    combined_text = f"{subject} {desc}"

    if severity == "Critical":
        return True, "Critical Severity - Immediate Human Attention Required."
        
    if severity == "High" and "PROD" in instance:
        return True, "High Severity in Production - Escalating."

    critical_keywords = [
        r"system down", r"outage", r"data breach", r"wire transfer", 
        r"ransomware", r"phishing", r"server room", r"fire", r"flood"
    ]
    
    for kw in critical_keywords:
        if re.search(kw, combined_text):
            return True, f"Critical Keyword Detected: '{kw.replace(r'', '')}'"

    
    # Security
    if topic == "Access & Identity":
        if "locked out" in combined_text and "urgent" in combined_text:
             return True, "Urgent Access Issue."
             
    # Manufacturing
    if topic == "Manufacturing":
        if "line" in combined_text and ("stopped" in combined_text or "down" in combined_text):
            return True, "Manufacturing Line Stoppage."
            
    # Integrations (EDI)
    if topic == "EDI" or "edi" in combined_text:
        if "rejected" in combined_text or "failed" in combined_text:
             # Escalating EDI failures as they impact revenue/orders
             return True, "EDI Transaction Failure."
             
    # Finance
    if topic == "Finance":
        if "payroll" in combined_text or "tax" in combined_text:
            return True, "Financial/Compliance Risk."

    return False, None

def check_ai_confidence(confidence_score):
    """
    Escalates if AI confidence is too low.
    """
    if confidence_score == "low":
        return True, "AI Confidence Low - Human Review Needed."
    return False, None
