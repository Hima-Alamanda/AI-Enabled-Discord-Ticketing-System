import streamlit as st
import base64
import os
import smtplib
import re

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


TICKET_TOPICS = [
    "Finance",
    "HR",
    "Supply Chain",
    "Manufacturing",
    "Sales",
    "IT Infrastructure & Hardware",
    "Access & Identity",
    "Other (Custom...)"
]
SEVERITIES = ["Low", "Medium", "High", "Critical"]
INSTANCES = ["DEV - Development", "QA / TEST - Testing", "UAT - User Acceptance Testing", "PROD - Production", "Other (Custom...)"]
DEPLOYMENT_TYPES = ["On-Premise", "Cloud", "Other (Custom...)"]
TICKET_TYPES = ["Incident", "Service Request", "Problem", "Change Request", "Other (Custom...)"]
HYPERCARE_OPTIONS = ["No", "Yes"]
import logging

# TICKET_FILE is deprecated and removed

def setup_logging():
    """Configures application logging."""
    logging.basicConfig(
        filename='app.log',
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.info("Application started.")

USERS = {
    "admin": {"password": "password123", "role": "admin", "name": "Admin", "email": "admin@pcbapps.com"},
    "raghu": {"password": "password123", "role": "agent", "name": "Technician 1", "email": "raghu@pcbapps.com"},
    "bhanu": {"password": "password123", "role": "agent", "name": "Technician 2", "email": "bhanu@pcbapps.com"},
    "customer": {"password": "password123", "role": "customer", "name": "Alex Rivera", "email": "himanthalamanda@gmail.com"},
    "sarah": {"password": "password123", "role": "customer", "name": "Sarah Chen", "email": "sarah@pcbapps.com"},
    "james": {"password": "password123", "role": "customer", "name": "James Anderson", "email": "james@pcbapps.com"}
}

def check_login(username, password):
    if username in USERS and USERS[username]['password'] == password:
        user_data = USERS[username].copy()
        
        # Try to enrich with DB data (Role, Agent ID)
        try:
            import database
            db_agent = database.get_agent_by_email(user_data['email'])
            if db_agent:
                user_data['role'] = db_agent['role']
                user_data['agent_id'] = db_agent['agent_id']
                user_data['topics'] = db_agent.get('topics', [])
        except Exception:
            pass
            
        return user_data
    
    # Default password for all DB agents for now
    if password == "password123": 
        try:
            import database
            agent = database.get_agent_by_email(username)
            if agent and agent.get('active', 1):
                return {
                    "role": agent['role'], # 'admin' or 'agent'
                    "name": agent['name'],
                    "email": agent['email'],
                    "agent_id": agent.get('agent_id'),
                    "topics": agent.get('topics', [])
                }
        except Exception as e:
            print(f"DB Login Error: {e}")
            pass

    # Allow 'user1', 'user2', or 'customer1' etc.
    if (username.lower().startswith("user") or username.lower().startswith("customer")) and password == "password123":
        return {
            "role": "customer",
            "name": username.title(), 
            "email": f"{username.lower()}@example.com"
        }
            
    return None

def load_css():
    with open("styles.css", "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

HTML_TEMPLATES = {}

def load_templates():
    """Parses assets/components.html and populates HTML_TEMPLATES."""
    global HTML_TEMPLATES
    filepath = os.path.join("assets", "components.html")
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            content = f.read()
        
        # Regex to find <template id="...">content</template>
        # Using DOTALL to match newlines
        matches = re.findall(r'<template id="(.*?)">(.*?)</template>', content, re.DOTALL)
        for key, value in matches:
            HTML_TEMPLATES[key] = value.strip()

# Load templates on module import
load_templates()

def load_html(filename):
    """Loads an HTML template from the parsed dictionary."""
    return HTML_TEMPLATES.get(filename, "")

def get_logo_html():
    logo_path = "assets/logo2.png"
    if os.path.exists(logo_path):
        return f'<img src="data:image/png;base64,{base64.b64encode(open(logo_path, "rb").read()).decode()}" style="height: 48px;">'
    return ""

def send_email(to_email, subject, body):
    # Check for secrets
    if "email" not in st.secrets:
        st.warning(" Email not configured! Create `.streamlit/secrets.toml` to enable sending.")
        return False

    sender_email = st.secrets["email"]["gmail_user"]
    sender_password = st.secrets["email"]["gmail_password"]

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Failed to send email: {str(e)}")
        return False

def strip_html(text):
    if isinstance(text, str):
        # Remove all HTML tags
        import re
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)
    return text
