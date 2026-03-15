
import datetime

# SLA Configurations (in Hours)
SLA_HOURS = {
    "Critical": 1,
    "High": 4,
    "Medium": 24,
    "Low": 48
}

def get_deadline(created_at_input, severity):
    """Calculates the deadline based on creation time and severity."""
    if isinstance(created_at_input, (datetime.datetime, datetime.date)):
        created_at = created_at_input
    else:
        try:
            created_at = datetime.datetime.strptime(str(created_at_input), "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            # Try ISO format if default fails, or return None
            try:
                created_at = datetime.datetime.fromisoformat(str(created_at_input))
            except:
                return None
        
    hours = SLA_HOURS.get(severity, 24) # Default to 24h (Medium)
    if isinstance(hours, str): 
         # Handle if hours is "24 Hours" string by mistake
         try: hours = int(hours.split()[0])
         except: hours = 24
         
    deadline = created_at + datetime.timedelta(hours=int(hours))
    return deadline

def get_sla_status(created_at_input, severity, status='Open', updated_at_input=None):
    """
    Returns a status dict with text and color.
    Status: At Risk, Breached, On Track, Met, Missed
    """
    deadline = get_deadline(created_at_input, severity)
    if not deadline:
        return {"status": "Error", "color": "grey", "time_remaining": "N/A"}
        
    # Handle Closed Tickets
    if status in ['Closed', 'Resolved']:
        end_time = datetime.datetime.now()
        
        if isinstance(updated_at_input, (datetime.datetime, datetime.date)):
            end_time = updated_at_input
        elif updated_at_input:
            try:
                end_time = datetime.datetime.strptime(str(updated_at_input), "%Y-%m-%d %H:%M:%S")
            except:
                try: end_time = datetime.datetime.fromisoformat(str(updated_at_input))
                except: pass
        
        if end_time <= deadline:
             return {"status": "Met", "color": "#22c55e", "time_remaining": "-"} # Green
        else:
             return {"status": "Missed", "color": "#ef4444", "time_remaining": "-"} # Red

    # Handle Active Tickets
    now = datetime.datetime.now()
    delta = deadline - now
    total_seconds = int(delta.total_seconds())
    
    # Breached
    if total_seconds < 0:
        return {
            "status": "Breached",
            "color": "#ef4444", # Red
            "time_remaining": format_timedelta(abs(total_seconds)) + " overdue"
        }
    
    # At Risk (e.g. less than 25% time left or less than 4 hours depending on severity?)
    # Simple rule: < 4 hours or < 20% of original SLA
    # User said "At Risk in yellow text"
    
    original_duration = SLA_HOURS.get(severity, 48) * 3600
    if total_seconds < 3600 * 4: # Less than 4 hours
        return {
            "status": "At Risk",
            "color": "#eab308", # Yellow/Gold (using hex that is visible on white)
            "time_remaining": format_timedelta(total_seconds)
        }
        
    return {
        "status": "On Track",
        "color": "#22c55e", # Green
        "time_remaining": format_timedelta(total_seconds)
    }

def format_timedelta(seconds):
    hours = seconds // 3600
    mins = (seconds % 3600) // 60
    return f"{hours}h {mins}m"
