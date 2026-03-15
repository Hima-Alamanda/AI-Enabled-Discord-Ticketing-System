
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import datetime
import base64
import re
import time
import json
import controller 
from auto_tagging import (
    predict_topic, predict_severity, predict_instance, 
    predict_deployment, predict_ticket_type,
    predict_ticket_details_llm
)
from sla_manager import get_sla_status
from rag_manager import get_ai_response
from tools import AVAILABLE_TOOLS, execute_tool
from PIL import Image
from streamlit_autorefresh import st_autorefresh

import utils
import database # DB Layer

# Initialize Logging
utils.setup_logging()

# Initialize Agents
import agent_manager
agent_manager.init_agents()

# Page Configuration

current_dir = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(current_dir, "assets", "logo2.png")


st.set_page_config(
    page_title="PCB Apps Support",
    page_icon=logo_path,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Custom CSS
utils.load_css()


# Constants



if 'page' not in st.session_state:
    st.session_state['page'] = 'Home'

if 'bot_minimized' not in st.session_state:
    st.session_state['bot_minimized'] = True

if 'bot_messages' not in st.session_state:
    st.session_state['bot_messages'] = [
        {"role": "assistant", "content": (
            "Hi! I'm your **AI Support Assistant**\n\n"
            "Here's what I can do for you:\n"
            "- **Search** our technical resources & past resolved cases\n"
            "- **Read** screenshots, PDFs, and error logs you upload\n"
            "- **Create** support tickets automatically\n"
            "- **Escalate** to a human technician when needed\n\n"
            "How can I help you today?"
        )}
    ]

# Counters for resetable file uploaders
if 'customer_attach_counter' not in st.session_state:
    st.session_state['customer_attach_counter'] = 0
if 'agent_attach_counter' not in st.session_state:
    st.session_state['agent_attach_counter'] = 0

def navigate_to(page):
    st.session_state['page'] = page
    st.session_state['manual_nav_pending'] = True


#import pages.Technician_Dashboard
#import pages.agent_my_tickets
#import pages.all_tickets_view
#import pages.ticket_details

# Redundant render_navbar removed. Using utils.render_navbar() centralized in utils.py

def render_comments(ticket_id):
    """Renders the discussion history for a ticket."""
    # Use get_chat_history instead of get_comments to see all messages
    chat_history = database.get_chat_history(ticket_id)
    
    if chat_history:
        st.markdown("---")
        st.write("#### Conversation History")
        
        for msg in chat_history:
            sender = msg.get('sender', 'unknown')
            message = msg.get('message', '')
            timestamp_raw = msg.get('timestamp', '')
            timestamp = str(timestamp_raw)[:16] if timestamp_raw else ''
            
            if sender == 'ai' or sender == 'bot':
                # AI message
                with st.chat_message("assistant"):
                    if message and message.strip() and message.lower() != "none":
                        st.markdown(message)
                    st.caption(f"AI • {timestamp}")
            
            elif sender == 'agent':
                # Agent message
                with st.chat_message("assistant"):
                    if message and message.strip() and message.lower() != "none":
                        st.markdown(message)
                    
                    att_p = msg.get('attachment')
                    if att_p:
                        try:
                            import oci_storage
                            if str(att_p).startswith('http'):
                                par_url = att_p
                            else:
                                par_url = oci_storage.generate_download_url(att_p)
                                
                            clean_path = str(att_p).split('?')[0].lower()
                            is_image = clean_path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')) or 'discordapp' in str(att_p).lower()
                            
                            if is_image:
                                st.image(par_url, width=400)
                            else:
                                display_name = str(att_p).split("/")[-1].split("?")[0]
                                st.link_button(f"📎 {display_name}", par_url)
                        except:
                            st.caption("Attachment unavailable")
                            
                    st.caption(f"Technician • {timestamp}")
            
            elif sender == 'user' or sender == 'customer':
                # Customer message
                with st.chat_message("user"):
                    if message and message.strip() and message.lower() != "none":
                        st.markdown(message)
                        
                    att_p = msg.get('attachment')
                    if att_p:
                        try:
                            import oci_storage
                            if str(att_p).startswith('http'):
                                par_url = att_p
                            else:
                                par_url = oci_storage.generate_download_url(att_p)
                                
                            clean_path = str(att_p).split('?')[0].lower()
                            is_image = clean_path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')) or 'discordapp' in str(att_p).lower()
                            
                            if is_image:
                                st.image(par_url, width=400)
                            else:
                                display_name = str(att_p).split("/")[-1].split("?")[0]
                                st.link_button(f"📎 {display_name}", par_url)
                        except:
                            st.caption("Attachment unavailable")
                            
                    st.caption(f"Customer • {timestamp}")
    else:
        st.markdown("---")
        st.caption("No conversation history yet.")

def render_sidebar():
    """Renders the left sidebar navigation for all roles."""
    with st.sidebar:
        # 1) TOP CONTAINER START (Logo + Menu)
        st.markdown('<div class="sidebar-top-container">', unsafe_allow_html=True)
        
        # 1.1) Logo
        try:
            logo = Image.open("assets/logo3-removebg.png")
            st.image(logo, width="stretch") 
        except Exception:
            st.write("### PCB Apps")

        # 1.2) Main menu header
        st.markdown(utils.load_html("sidebar_header.html"), unsafe_allow_html=True)

        # 1.3) Role-based navigation
        role = st.session_state.get("role", "customer")

        if role == "admin":
            nav_items = ["Admin Dashboard", "Knowledge Base"]
        elif role in ("technician", "agent"):
            nav_items = ["Technician Dashboard", "My Analytics"]
        else:
            nav_items = ["Home", "Submit Ticket", "My Tickets", "Dashboard"]

        current_page = st.session_state.get("page", nav_items[0])
        default_idx = nav_items.index(current_page) if current_page in nav_items else 0

        # Nav wrapper
        st.markdown(utils.load_html("div_nav_start.html"), unsafe_allow_html=True)
        selected_page = st.radio(
            label="Navigation",
            options=nav_items,
            index=default_idx,
            key="side_nav_radio",
            label_visibility="collapsed"
        )
        st.markdown(utils.load_html("div_close.html"), unsafe_allow_html=True)

        if selected_page != st.session_state.get("page"):
            st.session_state["page"] = selected_page
            st.rerun()
            
        # 1.4) TOP CONTAINER END
        st.markdown('</div>', unsafe_allow_html=True)

        # 4) Spacer that pushes footer to bottom
        st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)


        # 5) Footer pinned at bottom
        display_name = st.session_state.get("user_name") or st.session_state.get("username") or "Guest"
        display_name = str(display_name).strip() or "Guest"

        st.markdown(utils.load_html("div_footer_container_start.html"), unsafe_allow_html=True)

        with st.popover(display_name, width="stretch"):
            if st.button("Profile", width="stretch", key="side_profile"):
                st.info("Profile page coming soon!")
            if st.button("Logout", width="stretch", key="side_logout"):
                st.session_state.clear()
                st.rerun()

        st.markdown(utils.load_html("div_close.html"), unsafe_allow_html=True)

def page_ticket_details():
    ticket_id = st.session_state.get('selected_ticket_id')
    if not ticket_id:
        st.error("No ticket selected.")
        if st.button("Back to Dashboard"):
            st.session_state['page'] = 'Admin Dashboard'
            st.rerun()
        return

    ticket = controller.get_ticket_by_id(ticket_id)
    if not ticket:
        st.error("Ticket not found.")
        if st.button("Back"):
            st.session_state['page'] = 'All Tickets'
            st.rerun()
        return

    # Breadcrumbs
    st.caption(f"Home > Tickets > {ticket_id}")
    if st.button("← Back to List"):
        st.session_state['page'] = 'All Tickets'
        st.rerun()
    
    # Header
    c1, c2 = st.columns([0.8, 0.2])
    with c1:
        st.title(f"{ticket.get('subject', 'No Subject')}")
    with c2:
        st.info(f"{ticket.get('status', 'Open')}")

    col_left, col_right = st.columns([0.65, 0.35], gap="large")
    
    with col_left:
        st.subheader("AI Handoff Report")
        with st.container(border=True):
            st.markdown(ticket.get('description', 'No description provided.'))
        
        # Attachments if any
        att_data = ticket.get('attachment')
        if att_data and att_data != "None":
            # Handle both list (JSON) and single string (legacy)
            try:
                attachments = json.loads(att_data)
                if not isinstance(attachments, list):
                    attachments = [attachments]
            except:
                attachments = [att_data]
                
            for idx, att_path in enumerate(attachments):
                display_name = str(att_path).split("/")[-1].split("?")[0]
                st.markdown(f"**Attachment {idx+1}:** {display_name}")
                try:
                    import oci_storage
                    if str(att_path).startswith('http'):
                        par_url = att_path
                    else:
                        par_url = oci_storage.generate_download_url(att_path)
                    
                    # Clean path for extension check
                    clean_path = str(att_path).split('?')[0].lower()
                    if clean_path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')) or 'discordapp' in str(att_path).lower():
                        st.image(par_url, width=600)
                    st.link_button(f"Download {display_name}", par_url)
                except Exception as oci_err:
                    st.warning(f"Could not retrieve attachment from OCI: {oci_err}")

        # Timeline / Comments
        st.markdown("---")
        render_comments(ticket_id)
        
        # Reply Box - Only for active tickets
        if ticket.get('status') not in ['Closed']:
            st.markdown("### Reply")
            with st.form(key=f"reply_{ticket_id}"):
                reply_text = st.text_area("Add a reply...", height=100)
                send_email_checkbox = st.checkbox("Send email to customer", value=True)
                
                if st.form_submit_button("Post Reply"):
                    if reply_text:
                        author = st.session_state.get('user_name', 'Unknown')
                        # Use add_chat_message instead of add_comment so it appears in customer view
                        database.add_chat_message(ticket_id, 'agent', reply_text)
                        
                        # Do NOT change status here - will change when technician leaves ticket
                        # if ticket.get('status') == 'Open':
                        #     ticket['status'] = 'In Progress'
                        #     controller.update_ticket(ticket)
                        
                        # Send email if checkbox is checked
                        if send_email_checkbox and ticket.get('email'):
                            customer_email = ticket['email']
                            subject = f"Re: {ticket.get('subject', 'Your Support Ticket')} [Ticket #{ticket_id}]"
                            body = f"""Dear Customer,
    
    Thank you for contacting PCB Apps Support.
    
    {reply_text}
    
    ---
    Ticket ID: {ticket_id}
    Status: {ticket.get('status', 'Open')}
    Priority: {ticket.get('priority', 'Medium')}
    
    Best regards,
    {author}
    PCB Apps Support Team
    """
                            email_sent = utils.send_email(customer_email, subject, body)
                            if email_sent:
                                st.success(f"Reply posted and email sent to {customer_email}")
                            else:
                                st.warning("Reply posted but email failed to send. Check email configuration.")
                        else:
                            st.success("Reply posted.")
                        
                        st.rerun()
        else:
            st.info("🕒 This ticket is currently resolved/closed. You can update its status in the sidebar if you wish to re-open it.")

    with col_right:
        st.markdown("### Ticket Details")
        st.markdown("---")
        
        with st.form(key="update_ticket_meta"):
            # Status
            curr_status = ticket.get('status', 'Open')
            status_opts = ["Open", "In Progress", "Closed"]
            # Map old statuses to new ones for backward compatibility
            curr_status_mapped = curr_status if curr_status in status_opts else "Open"
            idx_s = status_opts.index(curr_status_mapped) if curr_status_mapped in status_opts else 0
            new_status = st.selectbox("Status", status_opts, index=idx_s)
            
            # Priority
            curr_pri = ticket.get('priority', 'Medium')
            pri_opts = ["Low", "Medium", "High", "Critical"]
            idx_p = pri_opts.index(curr_pri) if curr_pri in pri_opts else 1
            new_priority = st.selectbox("Severity", pri_opts, index=idx_p)
            
            # Instance
            instances = utils.INSTANCES
            curr_inst = ticket.get('instance')
            inst_idx = instances.index(curr_inst) if curr_inst in instances else 0
            new_instance = st.selectbox("Instance", instances, index=inst_idx)
            
            # Version
            new_version = st.text_input("Version", value=ticket.get('version', ''))
            
            if st.form_submit_button("Update Details"):
                ticket['status'] = new_status
                ticket['priority'] = new_priority
                ticket['instance'] = new_instance
                ticket['version'] = new_version
                
                controller.update_ticket(ticket)
                st.success("Ticket Updated.")
                st.rerun()
                
        # Agent Assignment (Only if Admin or Agent)
        if st.session_state.get('role') in ['admin', 'agent']:
            st.markdown("### Assignment")
            curr_agent_id = ticket.get('assigned_agent_id')
            # Get Agent Name
            agent_name = "Unassigned"
            if curr_agent_id:
                agt = database.get_agent_by_id(curr_agent_id)
                if agt: agent_name = agt['name']
            
            st.write(f"**Assigned To:** {agent_name}")

        # Satisfaction (Mock)
        st.markdown("---")
        st.write("**Customer Satisfaction:** Excellent")

def page_all_tickets_view():
    df_all = controller.get_dashboard_data()
    
    if df_all.empty:
        st.info("No tickets.")
        return

    if 'created_at' in df_all.columns:
        df_all['created_at'] = pd.to_datetime(df_all['created_at'])
        df_all = df_all.sort_values(by='created_at', ascending=False)
    
    col_f1, col_f2 = st.columns([1, 2.5])
    with col_f1:
        time_filter = st.selectbox(
            "Time Range", 
            ["Today", "Last 7 Days", "Last 30 Days", "All Time"], 
            index=3
        )
    with col_f2:
        search = st.text_input("Search Tickets", placeholder="Search by ID, Subject, or Technician...")

    # APPLY FILTERS
    if time_filter != "All Time" and 'created_at' in df_all.columns:
        now = datetime.datetime.now()
        if time_filter == "Today":
            df_all = df_all[df_all['created_at'].dt.date == now.date()]
        elif time_filter == "Last 7 Days":
            cutoff = now - datetime.timedelta(days=7)
            df_all = df_all[df_all['created_at'] >= cutoff]
        elif time_filter == "Last 30 Days":
            cutoff = now - datetime.timedelta(days=30)
            df_all = df_all[df_all['created_at'] >= cutoff]

    if search:
        df_all = df_all[
            df_all['subject'].str.contains(search, case=False, na=False) |
            df_all['ticket_id'].str.contains(search, case=False, na=False) |
            df_all['assigned_agent'].str.contains(search, case=False, na=False)
        ]

    inspect_id = st.session_state.get('inspect_ticket_id')
    if inspect_id:
        st.markdown(f"---")
        c_insp1, c_insp2 = st.columns([3, 1])
        c_insp1.markdown(f"#### Inspecting Ticket: {inspect_id}")
        if c_insp2.button("Close Inspector ✖️", key="close_inspector"):
            st.session_state['inspect_ticket_id'] = None
            st.rerun()
            
        import database
        # Fetch full ticket data for initial attachment
        ticket_data = controller.get_ticket_by_id(inspect_id)
        
        if ticket_data:
            with st.expander("Ticket Details", expanded=True):
                st.markdown("**Description:**")
                st.write(utils.strip_html(ticket_data.get('description', 'No description provided.')))
                
                c_field1, c_field2, c_field3 = st.columns(3)
                with c_field1:
                    st.caption(f"**Topic:** {ticket_data.get('topic', 'N/A')}")
                    st.caption(f"**Instance:** {ticket_data.get('instance', 'N/A')}")
                with c_field2:
                    st.caption(f"**Deployment:** {ticket_data.get('deployment_type', 'N/A')}")
                    st.caption(f"**Version:** {ticket_data.get('version', 'N/A')}")
                with c_field3:
                    st.caption(f"**Systems:** {ticket_data.get('connected_systems', 'N/A')}")
                    st.caption(f"**Priority:** {ticket_data.get('priority', 'Medium')}")

        att_data = ticket_data.get('attachment') if ticket_data else None
        if att_data and att_data != "None":
            try:
                attachments = json.loads(att_data)
                if not isinstance(attachments, list):
                    attachments = [attachments]
            except:
                attachments = [att_data]
                
            import oci_storage
            for idx, att_path in enumerate(attachments):
                display_name = att_path.split("/")[-1]
                with st.expander(f"Attachment {idx+1}: {display_name}", expanded=False):
                    try:
                        par_url = oci_storage.generate_download_url(att_path)
                        if att_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                            st.image(par_url, width="stretch")
                        st.link_button("Download File", par_url)
                    except Exception as oci_err:
                        st.warning(f"Could not retrieve attachment from OCI: {oci_err}")

        history = database.get_ticket_chat_history(inspect_id)
        if history:
            with st.container(height=500, border=True):
                for msg in history:
                    author = msg['author']
                    if author in ['agent', 'bot', 'ai', 'assistant']:
                        role = "assistant"
                        avatar = None
                    else:
                        role = "assistant" # Force left alignment
                        avatar = "👤"
                    
                    ts = msg.get('timestamp', '')
                    att = msg.get('attachment')
                    
                    with st.chat_message(role, avatar=avatar):
                        timestamp_html = utils.load_html("timestamp.html").format(ts=ts)
                        st.markdown(f"**{author.upper()}** {timestamp_html}", unsafe_allow_html=True)
                        if msg.get('message') and str(msg['message']).strip().lower() != "none":
                            st.write(msg['message'])
                        
                        # Render Chat Attachment (OCI bucket)
                        if att:
                            try:
                                import oci_storage
                                if str(att).startswith('http'):
                                    par_url = att
                                else:
                                    par_url = oci_storage.generate_download_url(att)
                                
                                # Clean path for extension check
                                clean_path = str(att).split('?')[0].lower()
                                if clean_path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')) or 'discordapp' in str(att).lower():
                                    st.image(par_url, width=300)
                                
                                display_name = str(att).split("/")[-1].split("?")[0]
                                st.link_button(f"📎 Download {display_name}", par_url)
                            except Exception as oci_err:
                                st.caption(f"Attachment unavailable: {oci_err}")
        else:
            st.info("No chat activity found for this ticket.")
        st.markdown("---")

    c1, c2, c3, c4, c5, c6 = st.columns([0.15, 0.3, 0.15, 0.1, 0.15, 0.15])
    c1.markdown("**ID**")
    c2.markdown("**Subject**")
    c3.markdown("**Status**")
    c4.markdown("**Priority**")
    c5.markdown("**Technician**")
    c6.markdown("**Action**")
    st.markdown("---")
    
    # Limit to 30 for performance in this custom view
    for index, row in df_all.head(30).iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([0.15, 0.3, 0.15, 0.1, 0.15, 0.15])
        c1.write(row['ticket_id'])
        c2.write(row.get('subject', 'No Subject'))
        c3.write(row['status'])
        c4.write(row.get('priority', 'Medium'))
        c5.write(row.get('assigned_agent', 'Unassigned'))
        
        if c6.button("View", key=f"view_{row['ticket_id']}", width="stretch"):
            st.session_state['inspect_ticket_id'] = row['ticket_id']
            st.rerun()
            
    if len(df_all) > 30:
        st.caption(f"Showing 30 of {len(df_all)} tickets. Use search or filters to find older ones.")

def page_home():
    user_name = st.session_state.get('user_name', 'Valued Customer')
    user_email = st.session_state.get('user_email')
    
    # Get recent tickets for this user
    df_all = controller.get_dashboard_data()
    user_tickets = pd.DataFrame()
    if user_email and not df_all.empty:
        if 'email' in df_all.columns:
            user_tickets = df_all[df_all['email'] == user_email]
        elif 'requester_email' in df_all.columns:
            user_tickets = df_all[df_all['requester_email'] == user_email]
    
    # Sort and take top 3
    recent_activity = []
    if not user_tickets.empty:
        if 'created_at' in user_tickets.columns:
            user_tickets = user_tickets.sort_values('created_at', ascending=False)
        
        for _, row in user_tickets.head(3).iterrows():
            status = row.get('status', 'Open')
            # Status styling
            bg, color = "#dcfce7", "#166534" # Default green (Closed)
            if status == 'Open': bg, color = "#eff6ff", "#2563eb" # Blue
            elif status == 'In Progress': bg, color = "#fef9c3", "#854d0e" # Yellow
            
            recent_activity.append({
                "ticket_id": str(row.get('ticket_id')).split('-')[-1] if '-' in str(row.get('ticket_id')) else str(row.get('ticket_id')),
                "subject": row.get('subject', 'No Subject'),
                "status": status,
                "status_style_attr": f'style="background: {bg}; color: {color}; font-size: 0.72rem; padding: 2px 8px; border-radius: 6px; font-weight: 600;"',
                "date": pd.to_datetime(row['created_at']).strftime('%b %d, %Y') if 'created_at' in row else "Recently"
            })

    st.markdown(utils.load_html("hero_section.html").format(user_name=user_name), unsafe_allow_html=True)
    
    st.markdown('<div style="margin-top: -1.5rem;"></div>', unsafe_allow_html=True)
    
    # Helper to load icons as base64
    def get_base64_img(icon_name):
        try:
            with open(f"assets/nav_{icon_name}.png", "rb") as f:
                data = base64.b64encode(f.read()).decode()
                return f"data:image/png;base64,{data}"
        except: return ""

    icon_submit = get_base64_img("submit")
    icon_tickets = get_base64_img("tickets")
    icon_track = get_base64_img("track")

    col_l, col1, col2, col3, col_r = st.columns([0.5, 1, 1, 1, 0.5])
    open_count = len(user_tickets[user_tickets['status'] != 'Closed']) if not user_tickets.empty else 0
    
    with col1:
        st.markdown(f"""
            <div class="shortcut-card">
                <div class="shortcut-icon"><img src="{icon_submit}" style="width: 48px; border-radius: 8px;"></div>
                <div class="shortcut-title">Submit Ticket</div>
                <div class="shortcut-desc">Request Technical Support</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Create Ticket", key="home_btn_submit", width="stretch"):
            navigate_to("Submit Ticket")
            st.rerun()

    with col2:
        st.markdown(f"""
            <div class="shortcut-card">
                <div class="shortcut-icon"><img src="{icon_tickets}" style="width: 48px; border-radius: 8px;"></div>
                <div class="shortcut-title">My Tickets</div>
                <div class="shortcut-desc">{open_count} Active Requests</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("View Tickets", key="home_btn_tickets", width="stretch"):
            navigate_to("My Tickets")
            st.rerun()

    with col3:
        st.markdown(f"""
            <div class="shortcut-card">
                <div class="shortcut-icon"><img src="{icon_track}" style="width: 48px; border-radius: 8px;"></div>
                <div class="shortcut-title">Track Status</div>
                <div class="shortcut-desc">Real-time Ticket Tracking</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Check Status", key="home_btn_track", width="stretch"):
            navigate_to("My Tickets")
            st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col_left, col_right = st.columns([1.5, 1])
    
    with col_left:
        st.markdown(utils.load_html("home_activity_start.html"), unsafe_allow_html=True)
        if not recent_activity:
            st.markdown(utils.load_html("home_activity_empty.html"), unsafe_allow_html=True)
        else:
            for act in recent_activity:
                st.markdown(utils.load_html("home_activity_item.html").format(**act), unsafe_allow_html=True)
        st.markdown(utils.load_html("home_activity_end.html"), unsafe_allow_html=True)

    with col_right:
        st.markdown(utils.load_html("home_health_card.html"), unsafe_allow_html=True)






def page_submit_ticket():
    # Check if user is viewing a ticket
    if st.session_state.get('viewing_ticket'):
        page_view_ticket()
        return
    
    st.markdown(utils.load_html("submit_ticket_header.html"), unsafe_allow_html=True)
    
    # Session State for AI Interaction
    if 'ticket_submitted' not in st.session_state:
        st.session_state['ticket_submitted'] = False
    if 'ai_response' not in st.session_state:
        st.session_state['ai_response'] = None
    if 'current_ticket_id' not in st.session_state:
        st.session_state['current_ticket_id'] = None
    if 'submission_time' not in st.session_state:
        st.session_state['submission_time'] = None
    if 'auto_close_warning_sent' not in st.session_state:
        st.session_state['auto_close_warning_sent'] = False
    if 'show_submission_popup' not in st.session_state:
        st.session_state['show_submission_popup'] = False
    
    # Auto-tagging session state
    if 'detected_tags' not in st.session_state:
        st.session_state['detected_tags'] = []
    if 'selected_tags' not in st.session_state:
        st.session_state['selected_tags'] = []
    if 'last_description' not in st.session_state:
        st.session_state['last_description'] = ""
    if 'auto_filled_fields' not in st.session_state:
        st.session_state['auto_filled_fields'] = {}

    # Auto-fill user details
    current_email = st.session_state.get('user_email', '')
    current_name = st.session_state.get('user_name', '')

    if not st.session_state['ticket_submitted']:
        st.info("Describe your issue and we will analyze it and suggest relevant tags and field values.")

        # Basic Info (outside form for real-time updates)
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("Email Address :red[*]", value=current_email, disabled=True if current_email else False, key="email_input", placeholder="e.g., alex.rivera@example.com")
        with col2:
            name = st.text_input("Full Name :red[*]", value=current_name, disabled=True if current_name else False, key="name_input", placeholder="e.g., Alex Rivera")
        
        subject = st.text_input("Subject Line :red[*]", placeholder="e.g., Cannot access VPN", key="subject_input")
        
        description = st.text_area("Detailed Description :red[*]", placeholder="Please describe the issue in detail...", height=200, key="description_area")
        
        # Attachment section moved directly after description for AI context
        st.markdown(utils.load_html("form_label_attachments.html"), unsafe_allow_html=True)
        attachments = st.file_uploader(
            "Attach Screenshots, Logs, or Documents",
            type=['png', 'jpg', 'jpeg', 'pdf', 'docx', 'txt'],
            help="AI analyzes your documents, Images to suggest relevant tags",
            key="submit_ticket_attachment",
            accept_multiple_files=True
        )

        # Extract plain text from HTML for analysis
        import re
        description_text = re.sub('<[^<]+?>', '', description) if description else ""
        
        # Extract text from attachments if available
        attachment_text = ""
        if attachments:
            from document_processor import extract_text_from_any
            for att in attachments:
                with st.spinner(f"Reading {att.name}..."):
                    text = extract_text_from_any(att)
                    if text is None:
                        st.warning(f"⚠️ **Image OCR Unavailable** for {att.name}: Tesseract is not installed on this server.")
                    elif text:
                        # Provide visual feedback that text was successfully extracted
                        st.markdown(f"Successfully analyzed details in: **{att.name}**")
                        attachment_text += f"\n\n[CONTENT FROM {att.name}]:\n{text}"
                    else:
                        st.info(f"No text extracted from: **{att.name}** (File may be empty or encrypted)")
        
        # Combine text for analysis (Excluding Subject as requested)
        combined_text = description_text
        if attachment_text:
            combined_text += attachment_text
            
        # Fully Automatic AI Detection: Triggers whenever description or attachment changes
        current_combined_hash = combined_text
        has_enough_content = (len(description_text) > 10) or (len(attachment_text) > 10)
        
        if has_enough_content and current_combined_hash != st.session_state.get('last_combined_context', ""):
            st.session_state['last_combined_context'] = current_combined_hash
            
            with st.spinner("Analyzing description and documents..."):
                from auto_tagging import analyze_ticket_with_ai
                analysis = analyze_ticket_with_ai(combined_text)
                st.session_state['detected_tags'] = analysis.get('tags', [])
                st.session_state['auto_filled_fields'] = analysis.get('fields', {})
                st.session_state['ai_raw_debug'] = analysis.get('raw_json_debug', {})
            st.rerun()
        
        # Reset tags if content is cleared
        elif not has_enough_content and st.session_state.get('last_combined_context', "") != "":
             st.session_state['detected_tags'] = []
             st.session_state['auto_filled_fields'] = {}
             st.session_state['ai_raw_debug'] = {}
             st.session_state['last_combined_context'] = ""
             st.rerun()
        
        # Display Auto-Detected Tags with clean Flexbox UI
        # Auto-tagging styles are now in styles.css
            
        # Available suggestions (exclude already selected)
        available_suggestions = [t for t in st.session_state['detected_tags'] if t not in st.session_state['selected_tags']]
        
        # Display Suggested Tags
        if available_suggestions:
            st.caption("Suggested Tags (Click to add to the ticket)")
            
            tag_cols = st.columns(4)
            for idx, tag in enumerate(available_suggestions):
                col_idx = idx % 4
                with tag_cols[col_idx]:
                    if st.button(f"+ {tag}", key=f"select_{tag}", width="stretch"):
                        if tag not in st.session_state['selected_tags']:
                            st.session_state['selected_tags'].append(tag)
                            st.rerun()
        elif has_enough_content and not st.session_state['detected_tags']:
            st.caption("No specific tags suggested for this issue.")
        
        # Display Selected Tags
        if st.session_state['selected_tags']:
            st.markdown("---")
            st.write("**Selected Tags (will be added to the ticket)**")
            
            # Use 4 columns for selected tags
            sel_cols = st.columns(4)
            for idx, tag in enumerate(st.session_state['selected_tags']):
                col_idx = idx % 4
                with sel_cols[col_idx]:
                    if st.button(f"{tag} ✕", key=f"deselect_{tag}", width="stretch", type="secondary"):
                        st.session_state['selected_tags'].remove(tag)
                        st.rerun()
            
            # Clear all button (smaller)
            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                if st.button("Clear All"):
                    st.session_state['selected_tags'] = []
                    st.rerun()

        
        st.markdown("---")
        
        # Enhanced Reactive Fields (Reactivity requires removal of st.form wrapper)
        st.caption("pre-filling the fields based on your description. You can modify any field.")
        
        # Get AI predictions
        ai_fields = st.session_state.get('auto_filled_fields', {})
        
        # Defensive check: ensure all field values are strings (not lists)
        if ai_fields:
            for key, val in ai_fields.items():
                if isinstance(val, list) and len(val) > 0:
                    ai_fields[key] = str(val[0])
                elif val is None:
                    ai_fields[key] = ""
                else:
                    ai_fields[key] = str(val)
        
        # Row 1: Partner Company and Severity
        col1, col2 = st.columns(2)
        with col1:
            from auto_tagging import get_partner_companies
            companies = get_partner_companies()
            
            # AI Logic for Partner
            ai_company = ai_fields.get('company')
            default_company_idx = 0
            is_custom_company = False
            
            if ai_company:
                if ai_company in companies:
                    default_company_idx = companies.index(ai_company)
                else:
                    is_custom_company = True
                    default_company_idx = companies.index("Other (Custom...)") if "Other (Custom...)" in companies else 0
            
            partner_sel = st.selectbox(
                "Partner Company :red[*]",
                options=companies,
                index=default_company_idx if ai_fields else None,
                placeholder="Select Partner Company...",
                help="Select the partner company this ticket is for",
                key="partner_sel"
            )
            
            if partner_sel == "Other (Custom...)":
                partner_company = st.text_input("Custom Partner Company", value=ai_company if is_custom_company else "", placeholder="Enter company name...")
            else:
                partner_company = partner_sel
        
        with col2:
            severities = utils.SEVERITIES
            default_severity = ai_fields.get('severity', "")
            severity = st.selectbox(
                "Severity Level :red[*]",
                options=severities,
                index=severities.index(default_severity) if default_severity in severities else None,
                placeholder="Select Severity...",
                help="How critical is this issue?"
            )
        
        # Row 2: Department/Topic and Instance
        col1, col2 = st.columns(2)
        with col1:
            topics = utils.TICKET_TOPICS
            
            # AI Logic for Topic
            ai_topic = ai_fields.get('topic')
            default_topic_idx = 0
            is_custom_topic = False
            
            if ai_topic:
                if ai_topic in topics:
                    default_topic_idx = topics.index(ai_topic)
                else:
                    is_custom_topic = True
                    default_topic_idx = topics.index("Other (Custom...)") if "Other (Custom...)" in topics else 0
            
            topic_sel = st.selectbox(
                "Department :red[*]",
                options=topics,
                index=default_topic_idx if ai_fields else None,
                placeholder="Select Department...",
                help="Which department or area does this relate to?"
            )
            
            if topic_sel == "Other (Custom...)":
                topic = st.text_input("Custom Department", value=ai_topic if is_custom_topic else "", placeholder="Enter topic...")
            else:
                topic = topic_sel
        
        with col2:
            instances = utils.INSTANCES
            
            # AI Logic for Instance
            ai_instance = ai_fields.get('instance')
            default_inst_idx = 0
            is_custom_inst = False
            
            if ai_instance:
                if ai_instance in instances:
                    default_inst_idx = instances.index(ai_instance)
                else:
                    is_custom_inst = True
                    default_inst_idx = instances.index("Other (Custom...)") if "Other (Custom...)" in instances else 0
                    
            instance_sel = st.selectbox(
                "Which Instance :red[*]",
                options=instances,
                index=default_inst_idx if ai_fields else None,
                placeholder="Select Instance...",
                help="Which environment is affected?"
            )
            
            if instance_sel == "Other (Custom...)":
                instance = st.text_input("Custom Instance", value=ai_instance if is_custom_inst else "", placeholder="e.g. SANDBOX")
            else:
                instance = instance_sel
        
        # Row 3: In Hypercare and On-Prem/Cloud
        col1, col2 = st.columns(2)
        with col1:
            hypercare = st.selectbox(
                "In Hypercare",
                options=utils.HYPERCARE_OPTIONS,
                index=None,
                placeholder="Select...",
                help="Is this system in hypercare support?"
            )
        
        with col2:
            deployment_types = utils.DEPLOYMENT_TYPES
            
            # AI Logic for Deployment
            ai_dep = ai_fields.get('deployment')
            default_dep_idx = 0
            is_custom_dep = False
            
            if ai_dep:
                if ai_dep in deployment_types:
                    default_dep_idx = deployment_types.index(ai_dep)
                else:
                    is_custom_dep = True
                    default_dep_idx = deployment_types.index("Other (Custom...)") if "Other (Custom...)" in deployment_types else 0
            
            deployment_sel = st.selectbox(
                "On-Prem or Cloud",
                options=deployment_types,
                index=default_dep_idx if ai_fields else None,
                placeholder="Select..."
            )
            
            if deployment_sel == "Other (Custom...)":
                deployment = st.text_input("Custom Deployment", value=ai_dep if is_custom_dep else "", placeholder="e.g. Hybrid")
            else:
                deployment = deployment_sel
        
        # Row 4: Connected Systems and Ticket Type
        col1, col2 = st.columns(2)
        with col1:
            connected_systems = st.text_input(
                "Connected Systems",
                placeholder="e.g., SAP, Salesforce",
                help="List any connected systems involved"
            )
        
        with col2:
            ticket_types = utils.TICKET_TYPES
            
            # AI Logic for Ticket Type
            ai_type = ai_fields.get('type')
            default_type_idx = 0
            is_custom_type = False
            
            if ai_type:
                if ai_type in ticket_types:
                    default_type_idx = ticket_types.index(ai_type)
                else:
                    is_custom_type = True
                    default_type_idx = ticket_types.index("Other (Custom...)") if "Other (Custom...)" in ticket_types else 0
            
            ticket_type_sel = st.selectbox(
                "Ticket Type :red[*]",
                options=ticket_types,
                index=default_type_idx if ai_fields else None,
                placeholder="Select..."
            )
            
            if ticket_type_sel == "Other (Custom...)":
                ticket_type = st.text_input("Custom Ticket Type", value=ai_type if is_custom_type else "", placeholder="e.g. Access Request")
            else:
                ticket_type = ticket_type_sel
        
        # Row 5: Customer Case Reference and Version
        col1, col2 = st.columns(2)
        with col1:
            customer_case_ref = st.text_input(
                "Customer Case Reference",
                placeholder="External reference number (if any)"
            )
        
        with col2:
            version = st.text_input(
                "Version",
                value="",
                placeholder="e.g., 1.0",
                help="Software version"
            )
        
        # Submit Button
        submitted = st.button("**Submit Ticket**", type="primary", width="stretch")
        
        if submitted:
            # Check for missing required fields
            missing_fields = []
            if not email: missing_fields.append("Email")
            if not name: missing_fields.append("Name")
            if not subject: missing_fields.append("Subject")
            if not description_text or description_text.strip() == "": missing_fields.append("Description")
            
            # Check selectboxes
            if partner_company is None or partner_company == "": missing_fields.append("Partner Company")
            if topic is None or topic == "": missing_fields.append("Department")
            if instance is None or instance == "": missing_fields.append("Instance")
            if severity is None or severity == "": missing_fields.append("Severity")
            if ticket_type is None or ticket_type == "": missing_fields.append("Ticket Type")

            if missing_fields:
                st.error(f"Please fill in all required fields: {', '.join(missing_fields)}")
            else:
                # Append selected tags to description
                final_description = description
                if st.session_state['selected_tags']:
                    tags_text = " | Tags: " + ", ".join(st.session_state['selected_tags'])
                    inline_tags = utils.load_html("inline_tags.html").format(tags_text=tags_text)
                    final_description += inline_tags
                
                ticket_data = controller.create_ticket(
                    description=final_description,
                    user_id=name,
                    email=email,
                    priority=severity,
                    topic=topic,
                    instance=instance
                )
                
                # Update with all fields
                ticket_data['subject'] = subject
                ticket_data['status'] = 'Open'
                ticket_data['deployment_type'] = deployment
                ticket_data['ticket_type'] = ticket_type
                ticket_data['version'] = version
                ticket_data['connected_systems'] = connected_systems
                ticket_data['customer_case_ref'] = customer_case_ref
                ticket_data['hypercare'] = hypercare
                ticket_data['auto_tags'] = json.dumps(st.session_state['selected_tags'])
                ticket_data['partner'] = partner_company
                
                # Handle Attachments — upload directly to OCI Object Storage
                import oci_storage
                import database as _db
                saved_paths = []
                if attachments:
                    for idx, att in enumerate(attachments):
                        clean_name = "".join([c if c.isalnum() or c in "._-" else "_" for c in att.name])
                        object_name = f"tickets/{ticket_data['ticket_id']}/{idx}_{clean_name}"
                        content_type = oci_storage.get_content_type(att.name)
                        try:
                            oci_storage.upload_file(att.getbuffer(), object_name, content_type)
                            saved_paths.append(object_name)
                        except Exception as oci_err:
                            st.warning(f"Could not upload {att.name} to OCI: {oci_err}")

                attachment_json = json.dumps(saved_paths) if saved_paths else "None"
                ticket_data['attachment'] = attachment_json

                # Write attachment directly to ADW now — before AI spinner runs
                if saved_paths:
                    try:
                        _db.update_ticket_attachment(ticket_data['ticket_id'], attachment_json)
                    except Exception as db_err:
                        st.warning(f"Attachment saved to OCI but ADW update failed: {db_err}")

                with st.spinner("Analyzing your issue..."):
                    import re
                    query = f"Subject: {subject}\nDescription: {description_text}"
                    
                    # Include attachment text context for RAG
                    if attachment_text:
                        query += f"\n\nContent from Attachments:\n{attachment_text}"

                    # Pass user context so LLM has the name
                    ai_result = get_ai_response(query, user_context={"name": name, "email": email})

                    # Handle streaming response
                    if ai_result.get('is_stream'):
                        response_text = ""
                        for token in ai_result['content']:
                            response_text += token
                    else:
                        response_text = ai_result.get('content', "No response generated.")

                    # Save AI confidence to session state for UI logic
                    st.session_state['ai_confidence'] = ai_result.get('confidence', 'high')
                    confidence = st.session_state['ai_confidence']
                    ai_response_text = (response_text or "").strip()
                    
                    # Set ticket status based on AI's confidence
                    if confidence == 'low':
                        ticket_data['status'] = 'Open' # Needs human review
                    else:
                        ticket_data['status'] = 'Open' # AI is providing a solution
                    
                    # Ensure we have the text
                    if not ai_response_text:
                        ai_response_text = "Analysis complete. A technician will review your case shortly."
                    
                    # We trust the rag_manager formatting, but ensure it's clean for Streamlit
                    ai_response_text = ai_response_text.replace("****", "**")
                    ai_response_text = ai_response_text.replace("\n\n\n", "\n\n")

                    ai_response_text = ai_response_text.replace("****", "**")
                    ai_response_text = ai_response_text.replace("\n\n\n", "\n\n")
                
                assigned_agent_id = agent_manager.assign_agent(ticket_data)
                ticket_data['assigned_agent_id'] = assigned_agent_id
                
                # Keep status as Open - escalation is flagged in the response text, not status
                # is_escalation_word = any(kw in ai_response_text.lower() for kw in ["escalate", "human technician", "hand over", "human agent"])
                # Escalation is communicated via response text, status remains Open
                
                controller.update_ticket(ticket_data)
                
                st.session_state['ticket_submitted'] = True
                st.session_state['current_ticket_id'] = ticket_data['ticket_id']
                st.session_state['ai_response'] = ai_response_text
                st.session_state['submission_time'] = time.time()
                st.session_state['auto_close_warning_sent'] = False
                
                # Save AI response to chat history
                database.add_chat_message(ticket_data['ticket_id'], 'ai', ai_response_text)
                
                # Clear auto-tagging state
                st.session_state['detected_tags'] = []
                st.session_state['selected_tags'] = []
                st.session_state['last_description'] = ""
                st.session_state['auto_filled_fields'] = {}
                st.session_state['ai_raw_debug'] = {}
                
                st.rerun()

    else:
        ticket_id = st.session_state['current_ticket_id']
        
        # Check if we should show the final confirmation popup instead of the AI suggestion
        if st.session_state.get('show_submission_popup'):
            st.markdown(utils.load_html("submission_wrapper_start.html"), unsafe_allow_html=True)
            ticket_id_display = ticket_id.split('-')[-1] if '-' in str(ticket_id) else ticket_id
            st.success(f"#### Ticket Submitted Successfully!\n#### Ticket ID: #{ticket_id_display}")
            
            # Get ticket details to show assigned agent
            ticket = controller.get_ticket_by_id(ticket_id)
            if ticket and ticket.get('assigned_agent_id'):
                agent = database.get_agent_by_id(ticket['assigned_agent_id'])
                if agent:
                    st.info(f"**Assigned to:** {agent.get('name', 'Technician')} ({agent.get('email', '')})")
            
            st.markdown(f"""
            Your request has been successfully assigned to a Technician. 

            The Technician will review your issue and assist you shortly. You can track its progress and continue the conversation in the **My Tickets** page.
            """)
            
            st.markdown(utils.load_html("br.html"), unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("View My Ticket", type="primary", width="stretch"):
                    st.session_state['selected_customer_ticket_id'] = ticket_id
                    st.session_state['ticket_submitted'] = False
                    st.session_state['show_submission_popup'] = False
                    navigate_to("My Tickets")
                    st.rerun()
            
            with col2:
                if st.button("Submit Another Ticket", width="stretch"):
                    # Reset all submission states
                    st.session_state['ticket_submitted'] = False
                    st.session_state['ai_response'] = None
                    st.session_state['current_ticket_id'] = None
                    st.session_state['show_submission_popup'] = False
                    st.rerun()
            
            st.markdown(utils.load_html("div_close.html"), unsafe_allow_html=True)
            return

        st.success(f"Ticket **{ticket_id}** Created Successfully!")
        
        # Get ticket details to show assigned agent
       
        
        st.markdown("##### Suggested Solution")
        ai_response = st.session_state.get('ai_response', '')
        st.info(ai_response)
        
        # Check if AI escalated or confidence is low
        # Includes 'specialized technician' to match the AI persona's fallback language
        is_escalated = st.session_state.get('ai_confidence') == 'low' or any(keyword in ai_response.lower() for keyword in ["escalate", "escalating", "human technician", "specialized technician"])
        
        if is_escalated:
            
            
            # Show assigned technician
            agent_details = "Unassigned"
            ticket = controller.get_ticket_by_id(ticket_id)
            if ticket and ticket.get('assigned_agent_id'):
                 agent = database.get_agent_by_id(ticket['assigned_agent_id'])
                 if agent:
                     name = agent.get('name', 'Technician')
                     email = agent.get('email', '')
                     if email:
                         agent_details = f"{name} ({email})"
                     else:
                         agent_details = name
            
            st.write(f"**Assigned to:** {agent_details}")

            # st.info("This ticket has been escalated to our human technician team. They will review it and get back to you soon.")
            # AI Response already contains the escalation notice if generated by RAG
            # If manual escalation, show a generic message ONLY if AI response didn't say it.
            if "escalated" not in ai_response.lower():
                 st.info("This ticket has been escalated to our human technician team.")
            
            # 2 options: View Ticket, Submit Another
            esc_c1, esc_c2 = st.columns(2)
            with esc_c1:
                if st.button("View Ticket", type="primary", width="stretch", key="view_escalated_ticket"):
                    st.session_state['selected_customer_ticket_id'] = ticket_id
                    st.session_state['ticket_submitted'] = False
                    st.session_state['ai_response'] = None
                    st.session_state['show_submission_popup'] = False
                    navigate_to("My Tickets")
                    st.rerun()
            
            with esc_c2:
                if st.button("Submit Another Ticket", width="stretch", key="submit_another_escalated"):
                    st.session_state['ticket_submitted'] = False
                    st.session_state['ai_response'] = None
                    st.session_state['current_ticket_id'] = None
                    st.session_state['show_submission_popup'] = False
                    st.rerun()
        else:
            st.markdown("---")
            st.markdown("##### Does this solve your issue?")
            
            c1, c2 = st.columns(2)
            
            # Calculate elapsed time
            elapsed = time.time() - st.session_state['submission_time']
            remaining = 30 - int(elapsed)
            
            # Option 1: Close Ticket
            if c1.button("Yes, Issue Resolved", type="primary", width="stretch"):
                # Get the full ticket data to preserve all fields
                ticket = controller.get_ticket_by_id(ticket_id)
                
                if ticket:
                    # Update status and assign to AI Assistant (since AI resolved it)
                    ticket['status'] = 'Closed'
                    ticket['assigned_agent_id'] = 'AI_ASSISTANT'  # AI resolved this, not a human agent
                    ticket['resolution_notes'] = 'User confirmed issue resolved by AI solution.'
                    
                    controller.update_ticket(ticket)
                    
                    st.success("Ticket Resolved Successfully! Redirecting to My Tickets...")
                    
                    # Reset State
                    st.session_state['ticket_submitted'] = False
                    st.session_state['ai_response'] = None
                    st.session_state['current_ticket_id'] = None
                    st.session_state['selected_customer_ticket_id'] = None # Ensure we go to list view
                    st.session_state['my_tickets_active_tab'] = "Closed" # Default to Closed tab
                    st.session_state['auto_close_warning_sent'] = False
                    time.sleep(2)
                    navigate_to("My Tickets")
                    st.rerun()
                else:
                    st.error("Ticket not found. Please try again.")

            if c2.button("No, Connect to Technician", width="stretch"):
                # Get the original ticket data
                ticket = controller.get_ticket_by_id(ticket_id)
                
                if ticket:
                    # Update ticket status to Open for agent handling
                    ticket['status'] = 'Open'
                    controller.update_ticket(ticket)
                    
                    # Reset submission state
                    st.session_state['show_submission_popup'] = True
                    st.rerun()
                else:
                    st.error("Ticket not found. Please try again.")
            
            st.markdown(utils.load_html("br.html"), unsafe_allow_html=True)
            if st.button("Submit Another Ticket", width="stretch", key="submit_another_post_suggestion"):
                # Reset all submission states
                st.session_state['ticket_submitted'] = False
                st.session_state['ai_response'] = None
                st.session_state['current_ticket_id'] = None
                st.session_state['show_submission_popup'] = False
                st.rerun()
            

            # Auto-close warning after 20 seconds
            if remaining <= 10 and remaining > 0 and not st.session_state['auto_close_warning_sent']:
                st.warning(f"This ticket will auto-escalate to a technician in {remaining} seconds if no action is taken.")
                st.session_state['auto_close_warning_sent'] = True
            
            # Auto-escalate after 30 seconds
            if remaining <= 0:
                ticket = controller.get_ticket_by_id(ticket_id)
                if ticket:
                    ticket['status'] = 'Open'
                    ticket['resolution_notes'] = 'Auto-escalated to agent after 30 seconds of inactivity.'
                    controller.update_ticket(ticket)
                    
                    # Set state to show confirmation popup
                    st.session_state['show_submission_popup'] = True
                    st.rerun()



def page_customer_table_view():
    """Customer dashboard showing tickets with professional analytics."""
    # Get tickets for current user
    df = controller.get_dashboard_data()
    user_email = st.session_state.get('user_email')
    
    if user_email:
        if 'email' in df.columns:
            df = df[df['email'] == user_email]
        elif 'requester_email' in df.columns:
            df = df[df['requester_email'] == user_email]
    else:
        df = pd.DataFrame()
    
    if df.empty:
        st.info("No tickets found. Submit your first ticket to get started!")
        if st.button("Submit New Ticket", width="stretch"):
            navigate_to("Submit Ticket")
            st.rerun()
        return

    # Filters moved below metrics
    # (Status normalization now happens in controller.get_dashboard_data())

    total_t = len(df)
    open_t = len(df[df['status'] == 'Open'])
    pending_t = len(df[df['status'] == 'In Progress'])
    closed_t = len(df[df['status'] == 'Closed'])
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Tickets", total_t)
    with m2:
        st.metric("Open", open_t)
    with m3:
        st.metric("In Progress", pending_t)
    with m4:
        st.metric("Closed", closed_t)
    
    st.markdown(utils.load_html("br.html"), unsafe_allow_html=True)
    
    # Sort by created_at descending
    if 'created_at' in df.columns:
        df = df.sort_values('created_at', ascending=False)
    
    # Prepare display columns
    display_cols = ['created_at', 'ticket_id', 'subject', 'status', 'priority', 'topic']
    if 'assigned_agent' in df.columns:
        display_cols.insert(6, 'assigned_agent')
    
    display_df = df[display_cols].copy()
    
    # Rename columns
    column_config = {
        'ticket_id': 'Ticket ID',
        'subject': 'Subject',
        'status': 'Status',
        'priority': 'Severity',
        'topic': 'Department',
        'created_at': 'Created On',
        'assigned_agent': 'Assigned Technician'
    }
    
    # Display dataframe
    st.markdown("### Ticket List")

    fc1, fc2 = st.columns(2)
    
    with fc1:
        # Date Filter
        min_date = pd.to_datetime(df['created_at']).min().date() if not df.empty and 'created_at' in df.columns else datetime.date.today()
        max_date = datetime.date.today()
        
        # Safety check for Streamlit range error
        if min_date > max_date:
            min_date = max_date
            
        date_selected = st.date_input(
            "Filter by Date",
            value=None,
            min_value=min_date,
            max_value=max_date
        )
    
    with fc2:
        # Status Filter - Single Select as requested
        all_statuses = ["All", "Open", "In Progress", "Closed"]
        selected_status = st.selectbox("Filter by Status", all_statuses)
        
    # Apply Filters for Table Display
    filtered_df = df.copy()
    
    if date_selected:
        # Ensure created_at is datetime
        if 'created_at' in filtered_df.columns:
            filtered_df['created_at_dt'] = pd.to_datetime(filtered_df['created_at'])
            # Filter by single date
            filtered_df = filtered_df[
                filtered_df['created_at_dt'].dt.date == date_selected
            ]
            
    if selected_status != "All":
        filtered_df = filtered_df[filtered_df['status'] == selected_status]
        
    display_df = filtered_df[display_cols].copy()
    
    # Format created_at to date only if it exists
    if 'created_at' in display_df.columns:
        display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.date
    
    st.dataframe(
        display_df.rename(columns=column_config),
        width="stretch",
        hide_index=True,
    )
    
    st.divider()
    st.markdown("### Service Analytics")
    

    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.markdown("**Status Distribution**")
        status_counts = df['status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        
        fig_status = px.bar(status_counts, x='Status', y='Count',
                           color='Status',
                           color_discrete_map={
                               'Open': '#3b82f6',    # Blue
                               'In Progress': '#f97316', # Orange
                               'Closed': '#10b981'   # Green
                           },
                           template="plotly_white")
        fig_status.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0), height=300, xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig_status, use_container_width=True)
        
    with col_chart2:
        st.markdown("**Severity Breakdown**")
        priority_counts = df['priority'].value_counts().reset_index()
        priority_counts.columns = ['Severity', 'Count']
        # Order priorities logically
        priority_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
        priority_counts['sort'] = priority_counts['Severity'].map(priority_order).fillna(4)
        priority_counts = priority_counts.sort_values('sort')
        
        fig_priority = px.pie(priority_counts, names='Severity', values='Count',
                             color='Severity',
                             color_discrete_map={
                                 'Critical': '#ef4444',
                                 'High': '#f97316',
                                 'Medium': '#3b82f6',
                                 'Low': '#10b981'
                             },
                             template="plotly_white",
                             hole=0.4)
        fig_priority.update_traces(textinfo='none') # Hide labels on the chart, show on hover/legend
        fig_priority.update_layout(showlegend=True, margin=dict(l=0, r=0, t=10, b=0), height=300)
        st.plotly_chart(fig_priority, use_container_width=True)




def page_view_ticket():

    """Customer ticket tracking page with conversation history."""
    st.title("My Ticket")
    
    # Auto-refresh every 5 seconds for real-time conversation
    st_autorefresh(interval=5000, key="customer_ticket_refresh")
    
    # Auto-refresh every 10 seconds to show new agent messages

    if 'ticket_view_last_refresh' not in st.session_state:
        st.session_state['ticket_view_last_refresh'] = time.time()
    
    if time.time() - st.session_state['ticket_view_last_refresh'] > 10:
        st.session_state['ticket_view_last_refresh'] = time.time()
        st.rerun()
    
    # Get ticket ID from session state
    ticket_id = st.session_state.get('current_ticket_id')
    
    if not ticket_id:
        st.error("No ticket selected.")
        if st.button("← Back to Dashboard"):
            navigate_to("Dashboard")
            st.rerun()
        return
    
    # Get ticket details
    ticket = database.get_ticket_by_id(ticket_id)
    
    if not ticket:
        st.error(f"Ticket {ticket_id} not found.")
        if st.button("← Back to My Tickets"):
            st.session_state['viewing_ticket'] = False
            st.session_state['current_ticket_id'] = None
            navigate_to("Dashboard")
            st.rerun()
        return
    
    # Layout: Sidebar for ticket details, main area for conversation
    col_main, col_sidebar = st.columns([2, 1])
    
    with col_sidebar:
        st.markdown("### Ticket Details")
        
        # Status badge
        status = ticket.get('status', 'Open')
        status_colors = {
            'Open': '',
            'In Progress': '',
            'Closed': '',
            'Closed': ''
        }
        st.markdown(f"**Status:** {status}")
        
        # Assigned agent
        assigned_agent = ticket.get('assigned_agent_id', 'Not assigned')
        if assigned_agent and assigned_agent != 'Not assigned':
            # Get agent details
            agent_info = database.get_agent_by_id(assigned_agent)
            if agent_info:
                st.markdown(f"**Assigned to:** {agent_info.get('name', assigned_agent)}")
                st.caption(f"{agent_info.get('email', '')}")
            else:
                st.markdown(f"**Assigned to:** {assigned_agent}")
        else:
            st.markdown("**Assigned to:** Pending assignment")
        
        st.markdown("---")
        
        # Ticket metadata
        st.markdown(f"**Ticket ID:** {ticket_id}")
        
        if ticket.get('priority'):
            priority_colors = {
                'Low': '',
                'Medium': '',
                'High': '',
                'Critical': ''
            }
            st.markdown(f"**Severity:** {ticket['priority']}")
        
        if ticket.get('topic'):
            st.markdown(f"**Department:** {ticket['topic']}")
        
        if ticket.get('instance'):
            st.markdown(f"**Instance:** {ticket['instance']}")
        
        if ticket.get('deployment_type'):
            st.markdown(f"**Deployment:** {ticket['deployment_type']}")
        
        if ticket.get('ticket_type'):
            st.markdown(f"**Type:** {ticket['ticket_type']}")
        
        if ticket.get('partner'):
            st.markdown(f"**Partner Company:** {ticket['partner']}")
        
        if ticket.get('connected_systems'):
            st.markdown(f"**Connected Systems:** {ticket['connected_systems']}")
        
        if ticket.get('version'):
            st.markdown(f"**Version:** {ticket['version']}")
        
        if ticket.get('customer_case_ref'):
            st.markdown(f"**Case Reference:** {ticket['customer_case_ref']}")
        
        st.markdown("---")
        st.caption(f"Created: {ticket.get('created_at', 'N/A')}")
        
        # Back button
        if st.button("← Back to My Tickets", width="stretch"):
            st.session_state['viewing_ticket'] = False
            st.session_state['current_ticket_id'] = None
            navigate_to("Dashboard")
            st.rerun()
    
    with col_main:
        st.markdown(f"### {ticket.get('subject', 'No Subject')}")
        st.caption(f"Ticket #{ticket_id}")
        
        # Display conversation history
        st.markdown("---")
        
        # Get chat history
        messages = database.get_chat_history(ticket_id)
        
        if messages:
            # Display messages
            for msg in messages:
                sender = msg.get('sender', 'unknown')
                message = msg.get('message', '')
                timestamp = msg.get('timestamp', '')
                
                if sender == 'ai' or sender == 'bot':
                    # AI message
                    with st.chat_message("assistant", avatar="🤖"):
                        if message and str(message).strip().lower() != "none":
                            st.markdown(message)
                        st.caption(f"🕒 {timestamp}")
                
                elif sender == 'agent':
                    # Agent message
                    with st.chat_message("assistant", avatar="👨‍🔧"):
                        if message and str(message).strip().lower() != "none":
                            st.markdown(f"**Technician:** {message}")
                        
                        att_p = msg.get('attachment')
                        if att_p:
                            try:
                                import oci_storage
                                par_url = oci_storage.generate_download_url(att_p)
                                if att_p.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                                    st.image(par_url, width="stretch")
                                else:
                                    st.link_button(f"📎 {os.path.basename(att_p)}", par_url)
                            except:
                                st.caption("Attachment unavailable")
                        st.caption(f"🕒 {timestamp}")
                
                elif sender == 'user' or sender == 'customer':
                    # Customer message
                    with st.chat_message("user"):
                        if message and str(message).strip().lower() != "none":
                            st.markdown(message)
                        
                        att_p = msg.get('attachment')
                        if att_p:
                            try:
                                import oci_storage
                                par_url = oci_storage.generate_download_url(att_p)
                                if att_p.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                                    st.image(par_url, width="stretch")
                                else:
                                    st.link_button(f"📎 {os.path.basename(att_p)}", par_url)
                            except:
                                st.caption("Attachment unavailable")
                        st.caption(f"🕒 {timestamp}")
        else:
            st.info("No conversation history yet. Send a message to start chatting with your assigned technician.")
        
        # Message input area
        st.markdown("---")
        st.markdown("#### Send a Message")
        
        with st.form(key=f"customer_message_form_{ticket_id}", clear_on_submit=True):
            customer_message = st.text_area(
                "Your message",
                placeholder="Type your message here...",
                height=100,
                label_visibility="collapsed"
            )
            
            col1, col2 = st.columns([3, 1])
            with col2:
                send_button = st.form_submit_button("Send", width="stretch")
            
            if send_button and customer_message.strip():
                # Add message to chat history
                database.add_chat_message(str(ticket_id), 'customer', customer_message.strip())
                
                # Update ticket status if it was resolved
                if ticket.get('status') == 'Closed':
                    ticket['status'] = 'Open'
                    controller.update_ticket(ticket)
                
                # Immediate rerun for rapid consecutive sends
                st.rerun()




def page_dashboard():
    """Customer Dashboard - Centered list initially, split-view once selected"""
    
    # Auto-refresh every 10 seconds to show new agent messages

    if 'customer_dashboard_refresh' not in st.session_state:
        st.session_state['customer_dashboard_refresh'] = time.time()
    
    if time.time() - st.session_state['customer_dashboard_refresh'] > 30:
        st.session_state['customer_dashboard_refresh'] = time.time()
        st.rerun()
    
    # Initialize selected ticket
    if 'selected_customer_ticket_id' not in st.session_state:
        st.session_state['selected_customer_ticket_id'] = None
    
    # Get tickets for current user
    df = controller.get_dashboard_data()
    user_email = st.session_state.get('user_email')
    
    if user_email:
        if 'email' in df.columns:
            df = df[df['email'] == user_email]
        elif 'requester_email' in df.columns:
            df = df[df['requester_email'] == user_email]
    else:
        df = pd.DataFrame()
    
    # Ensure all required columns exist
    for col in ['ticket_id', 'subject', 'status', 'priority', 'created_at']:
        if col not in df.columns:
            df[col] = "None"

    # Sort by created_at descending (newest first)
    if not df.empty and 'created_at' in df.columns:
        df = df.sort_values('created_at', ascending=False)

    if not st.session_state['selected_customer_ticket_id']:
        st.markdown(utils.load_html("my_tickets_header_customer.html"), unsafe_allow_html=True)
        
        if df.empty:
            st.info("No tickets found. Submit your first ticket to get started!")
            if st.button("Submit New Ticket", width="stretch"):
                navigate_to("Submit Ticket")
                st.rerun()
            return

        # Professional Search Bar & Date Filter
        c_search, c_date = st.columns([0.6, 0.4])
        
        with c_search:
            search_query = st.text_input("Search", placeholder="Search by Ticket ID or Subject...", label_visibility="collapsed")
            
        with c_date:
            min_date = pd.to_datetime(df['created_at']).min().date() if not df.empty and 'created_at' in df.columns else datetime.date.today()
            max_date = datetime.date.today()
            
            # Safety check for Streamlit range error
            if min_date > max_date:
                min_date = max_date
                
            date_selected = st.date_input(
                "Filter by Date",
                value=None,
                min_value=min_date,
                max_value=max_date,
                label_visibility="collapsed"
            )
        
        filtered_df = df.copy()
        
        # Apply Search
        if search_query:
            search_lower = search_query.lower()
            filtered_df = filtered_df[
                filtered_df['ticket_id'].astype(str).str.lower().str.contains(search_lower) |
                filtered_df['subject'].astype(str).str.lower().str.contains(search_lower)
            ]
            
        # Apply Date Filter
        if date_selected:
            # Ensure created_at is datetime
            if 'created_at' in filtered_df.columns:
                filtered_df['created_at_dt'] = pd.to_datetime(filtered_df['created_at'])
                # Filter by single date
                filtered_df = filtered_df[
                    filtered_df['created_at_dt'].dt.date == date_selected
                ]

        # Professional Tabs with Redirect Logic
        # Streamlit tabs don't support programmatic selection, so we reorder if needed
        default_tabs = ["Open", "In Progress", "Closed"]
        active_tab_state = st.session_state.get('my_tickets_active_tab', "Open")
        
        if active_tab_state == "Closed":
            tab_titles = ["Closed", "Open", "In Progress"]
        else:
            tab_titles = default_tabs
            
        tabs = st.tabs(tab_titles)
        
        # Inject Custom CSS for professional cards - MATCHING IMAGE 2
        # Inject Custom CSS for professional cards - MATCHING IMAGE 2
        st.markdown(utils.load_html("style_ticket_cards.html"), unsafe_allow_html=True)

        def render_ticket_list(target_df, key_prefix):
            if target_df.empty:
                st.caption("No tickets found in this category.")
            else:
                for _, row in target_df.iterrows():
                    tid = str(row['ticket_id'])
                    short_id = tid.split('-')[-1] if '-' in tid else tid
                    subj = row['subject'] or "No Subject"
                    
                    # Direct text label for the button to avoid rendering issues
                    label = f"#{short_id}  |  {subj}"
                    
                    if st.button(label, key=f"{key_prefix}_{tid}", width="stretch"):
                        st.session_state['selected_customer_ticket_id'] = tid
                        st.rerun()

        # Logic to categorize tickets
        pending_ids = []
        open_ids = []
        closed_ids = []

        for index, row in filtered_df.iterrows():
            status = row.get('status', 'Open')
            tid = row['ticket_id']
            
            if status in ['Closed']:
                closed_ids.append(tid)
            elif status == 'In Progress':
                pending_ids.append(tid)
            else: 
                # Status is 'Open' (or unknown) - Check for agent replies
                # If agent has replied, it's Pending (technician is working on it)
                chat_history = database.get_chat_history(tid)
                has_agent_reply = any(msg.get('sender') == 'agent' for msg in chat_history)
                
                if has_agent_reply:
                    pending_ids.append(tid)
                else:
                    open_ids.append(tid)
        
        open_df = filtered_df[filtered_df['ticket_id'].isin(open_ids)]
        pending_df = filtered_df[filtered_df['ticket_id'].isin(pending_ids)]
        closed_df = filtered_df[filtered_df['ticket_id'].isin(closed_ids)]

        # Map tab indexes to their content
        for i, title in enumerate(tab_titles):
            with tabs[i]:
                if title == "Open":
                    render_ticket_list(open_df, "list_open")
                elif title == "In Progress":
                    render_ticket_list(pending_df, "list_pending")
                elif title == "Closed":
                    render_ticket_list(closed_df, "list_closed")
                    
        # Reset the redirect state after rendering to ensure subsequent visits default to Open
        if 'my_tickets_active_tab' in st.session_state:
            del st.session_state['my_tickets_active_tab']
            
        return

    ticket = database.get_ticket_by_id(st.session_state['selected_customer_ticket_id'])
    if not ticket:
        st.error("Ticket not found.")
        st.session_state['selected_customer_ticket_id'] = None
        st.rerun()

    # Auto-refresh every 5 seconds for real-time conversation
    st_autorefresh(interval=5000, key="customer_dashboard_chat_refresh")

    # Back button at the top
    if st.button("← Back to All Tickets", type="secondary"):
        st.session_state['selected_customer_ticket_id'] = None
        st.rerun()

    st.markdown(utils.load_html("br.html"), unsafe_allow_html=True)
    
    ticket_id_str = str(ticket.get('ticket_id', ''))
    
    # Header Row: Subject and Metrics
    st.markdown(utils.load_html("ticket_header.html").format(subject=ticket.get('subject', 'No Subject')), unsafe_allow_html=True)
    
    m1, m2, m3 = st.columns(3)
    status_colors = {'Open': '', 'In Progress': '', 'Closed': ''}
    m1.markdown(f"**Status:** {ticket.get('status')}")
    
    priority_colors = {'Critical': '', 'High': '', 'Medium': '', 'Low': ''}
    m2.markdown(f"**Severity:** {ticket.get('priority')}")
    
    tid_full = ticket.get('ticket_id', 'N/A')
    m3.markdown(f"**Ticket ID:** {tid_full}")
    
    st.divider()

    # Metadata Row
    c1, c2 = st.columns(2)
    c1.markdown(f"**From:** {ticket.get('email', 'N/A')}")
    c2.markdown(f"**Created:** {ticket.get('created_at', 'N/A')}")
    
    # Details Expander
    with st.expander("Full Description & Details", expanded=False):
        st.markdown("**Description:**")
        st.write(utils.strip_html(ticket.get('description', 'No description.')))
        
        if ticket.get('topic'): st.caption(f"**Department:** {ticket['topic']}")
        if ticket.get('instance'): st.caption(f"**Instance:** {ticket['instance']}")
        if ticket.get('attachment') and ticket['attachment'] != "None": 
            att_data = ticket['attachment']
            try:
                attachments = json.loads(att_data)
                if not isinstance(attachments, list):
                    attachments = [attachments]
            except:
                attachments = [att_data]
                
            import oci_storage
            for idx, att_path in enumerate(attachments):
                display_name = att_path.split("/")[-1]
                st.markdown(f"**Attachment {idx+1}:** {display_name}")
                try:
                    par_url = oci_storage.generate_download_url(att_path)
                    if att_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                        st.image(par_url, width="stretch")
                    st.link_button(f"Download {display_name}", par_url)
                except Exception as oci_err:
                    st.warning(f"Attachment unavailable: {oci_err}")
        
        # Assigned Agent info
        agent_id = ticket.get('assigned_agent_id')
        if agent_id:
            agent = database.get_agent_by_id(agent_id)
            if agent:
                st.info(f"**Assigned Technician:** {agent.get('name')} ({agent.get('email')})")

    st.divider()
    
    # Conversation History
    st.markdown("### Conversation History")
    chat_container = st.container(height=500, border=True)
    chat_history = database.get_chat_history(ticket_id_str)
    
    with chat_container:
        if not chat_history:
            st.info("No messages yet. Start the conversation below.")
        
        for msg in chat_history:
            sender = msg.get('sender', 'unknown')
            message = msg.get('message', '')
            timestamp = msg.get('timestamp', '')
            attachment_path = msg.get('attachment')
            
            if sender in ['ai', 'bot']:
                with st.chat_message("assistant", avatar="🤖"):
                    if message and str(message).strip().lower() != "none":
                        st.markdown(message)
                    st.caption(f"AI Support • {timestamp}")
            elif sender == 'agent':
                with st.chat_message("assistant", avatar="👨‍🔧"):
                    if message and str(message).strip().lower() != "none":
                        st.markdown(message)
                    if attachment_path:
                        try:
                            import oci_storage
                            par_url = oci_storage.generate_download_url(attachment_path)
                            if attachment_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                                st.image(par_url, width="stretch")
                            else:
                                st.link_button("📎 Download Attachment", par_url)
                        except Exception as oci_err:
                            st.caption(f"Attachment unavailable: {oci_err}")
                    st.caption(f"Technician • {timestamp}")
            else:
                with st.chat_message("user"):
                    if message and str(message).strip().lower() != "none":
                        st.markdown(message)
                    if attachment_path:
                        try:
                            import oci_storage
                            par_url = oci_storage.generate_download_url(attachment_path)
                            if attachment_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                                st.image(par_url, width="stretch")
                            else:
                                st.link_button("📎 Download Attachment", par_url)
                        except Exception as oci_err:
                            st.caption(f"Attachment unavailable: {oci_err}")
                    st.caption(f"You • {timestamp}")
    
    # Customer Chat Input Area
    if ticket.get('status') not in ['Closed']:
        with st.container():
            # Attachment popover clearly aligned with the chat input
            # Improved ratio and gap to prevent any overlap
            col_att, col_input = st.columns([0.15, 0.85], vertical_alignment="center", gap="medium")
            with col_att:
                st.markdown(utils.load_html("attachment_wrapper_start.html"), unsafe_allow_html=True)
                with st.popover("📎", help="Attach a file"):
                    customer_attachment = st.file_uploader("Upload Image/Doc", type=['png','jpg','jpeg','pdf','docx','txt'], key=f"cust_attach_{ticket_id_str}_{st.session_state['customer_attach_counter']}")
                    if customer_attachment:
                        if st.button("Send Message", key=f"send_att_btn_{ticket_id_str}", width="stretch", type="primary"):
                            st.session_state[f"force_send_{ticket_id_str}"] = True
                            st.rerun()
                st.markdown(utils.load_html("div_close.html"), unsafe_allow_html=True)
            
            with col_input:
                reply_text = st.chat_input("Type your message here...", key=f"customer_chat_input_v4_{ticket_id_str}")

        # Trigger send if chat_input used OR "Send with attachment" button clicked
        if reply_text or st.session_state.get(f"force_send_{ticket_id_str}"):
            # Clear the force_send flag
            if f"force_send_{ticket_id_str}" in st.session_state:
                del st.session_state[f"force_send_{ticket_id_str}"]
                
            saved_att_path = None
            if customer_attachment:
                import oci_storage
                object_name = f"tickets/chat/{ticket_id_str}_{int(time.time())}_{customer_attachment.name}"
                content_type = oci_storage.get_content_type(customer_attachment.name)
                try:
                    oci_storage.upload_file(customer_attachment.getbuffer(), object_name, content_type)
                    saved_att_path = object_name
                except Exception as oci_err:
                    st.warning(f"Could not upload attachment to OCI: {oci_err}")
                # Increment counter to clear uploader
                st.session_state['customer_attach_counter'] += 1

            database.add_chat_message(ticket_id_str, 'customer', (reply_text or "").strip(), saved_att_path)
            
            if ticket.get('status') in ['Pending', 'Closed']:
                ticket['status'] = 'Open'
                controller.update_ticket(ticket)
            st.rerun()
    else:
        st.info(" This ticket has been resolved and is now read-only. If you have a new issue, please submit a new ticket.")

def render_floating_bot():
    """
    Renders the intelligent floating AI Support Assistant.
    Features:
    - Multi-turn conversation with intent detection
    - File upload (screenshots, PDFs, logs) inline in chat
    - KB vector search + past ticket search before responding
    - Auto ticket creation and smart escalation
    - Source citations
    """
    from chatbot_engine import get_chatbot_response

    if 'bot_file_key' not in st.session_state:
        st.session_state['bot_file_key'] = 0
    if 'bot_pending_file' not in st.session_state:
        st.session_state['bot_pending_file'] = None

    with st.popover("💬", help="Chat with AI Support", width="content"):

        # ── Header ──────────────────────────────────────────────────────────
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown("AI Support Assistant")
            st.caption("")
        with col_h2:
            if st.button("🗑️", key="bot_clear_history", help="Clear conversation"):
                st.session_state['bot_messages'] = [
                    {"role": "assistant", "content": "Hi! I'm your AI Support Assistant. How can I help you today?\n\nI can:\n- Search past tickets\n- Read your screenshots, logs, and PDFs\n- Create support tickets automatically\n- Escalate to a human agent when needed"}
                ]
                st.session_state['bot_file_key'] += 1
                st.session_state['bot_pending_file'] = None
                st.rerun()
        
        st.divider()

        # ── Chat History Display ─────────────────────────────────────────────
        chat_box = st.container(height=420, border=False)
        with chat_box:
            for i, msg in enumerate(st.session_state['bot_messages']):
                role = msg['role']
                with st.chat_message(role):
                    st.markdown(msg['content'])

                    # Show file attachment badge if present in message
                    if msg.get('file_name'):
                        st.caption(f"{msg['file_name']}")
                    


                    # Action result badge
                    if msg.get('ticket_id') and role == "assistant":
                        st.info(f"Reference: {msg['ticket_id']}")

                    # Ticket Preview / Confirm (AI suggested)
                    if msg.get('action') == "create_ticket" and msg.get('ticket_data') and not msg.get('ticket_id'):
                        st.markdown("---")
                        
                        # Premium Preview Card
                        with st.container(border=True):
                            st.markdown("#### Ticket Confirmation")
                            td = msg['ticket_data']
                            
                            col_preview1, col_preview2 = st.columns([1, 1])
                            with col_preview1:
                                st.markdown(f"**Subject:**\n{td.get('subject')}")
                            with col_preview2:
                                st.markdown(f"**Topic:**\n{td.get('topic')}")
                            
                            st.markdown(f"**Description:**\n{td.get('description')}")
                            
                            st.caption("Review the details above. Clicking below will log this in our system for technician review.")
                            
                            if st.button("Confirm & Create Ticket", key=f"bot_confirm_tkt_{i}", use_container_width=True, type="primary"):
                                with st.spinner("Processing your request..."):
                                    user_email = st.session_state.get("user_email", "unknown")
                                    u_name = st.session_state.get("user_name", "Customer")
                                    u_id = u_name if (u_name and u_name != "unknown") else (user_email.split('@')[0] if '@' in user_email else "Customer")
                                    
                                    new_t = controller.create_ticket(
                                        description=td.get('description'),
                                        user_id=u_id,
                                        email=user_email,
                                        priority="Medium",
                                        topic=td.get('topic'),
                                        ticket_type="AI Assessment"
                                    )
                                    
                                    st.session_state['bot_messages'][i]['ticket_id'] = new_t['ticket_id']
                                    st.session_state['bot_messages'][i]['content'] += f"\n\n **Success!** Ticket **{new_t['ticket_id']}** has been created."
                                    st.success(f"Ticket {new_t['ticket_id']} created!")
                                    st.rerun()

                    # (Feedback buttons and escalation logic removed)


        # ── File Attachment Area ─────────────────────────────────────────────
        uploaded_file = st.file_uploader(
            "Attach file (screenshot, PDF, log)",
            type=['png', 'jpg', 'jpeg', 'pdf', 'txt', 'log', 'docx'],
            key=f"bot_file_uploader_{st.session_state['bot_file_key']}",
            label_visibility="collapsed",
            help="Attach a file for AI analysis (screenshot, error log, PDF)"
        )

        if uploaded_file is not None:
            st.session_state['bot_pending_file'] = uploaded_file
            c1, c2 = st.columns([3, 1])
            with c1:
                st.caption(f"**{uploaded_file.name}**")
            with c2:
                if st.button("Send File", key="bot_send_file_only", type="primary", use_container_width=True):
                    # Trigger sending with empty prompt but containing the file
                    st.session_state['bot_chat_trigger'] = True
                    st.rerun()

        # ── Quick Action Buttons ─────────────────────────────────────────────
        qa1, qa2 = st.columns(2)
        with qa1:
            if st.button("Create Ticket", key="bot_quick_ticket", use_container_width=True):
                st.session_state['bot_messages'].append({"role": "user", "content": "I need to create a support ticket"})
                user_context = {
                    "email": st.session_state.get("user_email", "unknown"),
                    "name": st.session_state.get("user_name", "Customer")
                }
                with st.spinner("Processing..."):
                    resp = get_chatbot_response(
                        user_message="I need to create a support ticket for the issue I described",
                        history=st.session_state['bot_messages'],
                        user_context=user_context
                    )
                reply_msg = {
                    "role": "assistant", 
                    "content": resp["content"], 
                    "sources": resp.get("sources", []), 
                    "ticket_id": resp.get("ticket_id"),
                    "action": resp.get("action"),
                    "ticket_data": resp.get("ticket_data")
                }
                st.session_state['bot_messages'].append(reply_msg)
                st.rerun()
        with qa2:
            if st.button("Check Status", key="bot_quick_status", use_container_width=True):
                st.session_state['bot_messages'].append({"role": "user", "content": "Can you check my ticket status?"})
                st.session_state['bot_messages'].append({"role": "assistant", "content": "Sure! Please share your ticket ID (e.g. `20240301120000` or `AI20240301120000`) and I'll look it up right away."})
                st.rerun()

        # ── Chat Logic ──────────────────────────────────────────────────────
        prompt = st.chat_input("Describe your issue... (or attach a file above)", key="bot_input_global")
        trigger = st.session_state.get('bot_chat_trigger', False)

        if prompt or trigger:
            # Consume trigger
            st.session_state['bot_chat_trigger'] = False

            # Get pending file if any
            pending_file = st.session_state.get('bot_pending_file')
            file_name = pending_file.name if pending_file else None

            # Handle case where only file is sent
            final_prompt = prompt if prompt else f"{file_name}" if file_name else "Hello"

            # Add user message to history
            user_msg = {"role": "user", "content": final_prompt}
            if file_name:
                user_msg["file_name"] = file_name
            st.session_state['bot_messages'].append(user_msg)

            # Display user message
            with chat_box:
                with st.chat_message("user"):
                    st.markdown(final_prompt)
                    if file_name:
                        st.caption(f"{file_name}")

            # Build user context
            user_context = {
                "email": st.session_state.get("user_email", "unknown"),
                "name": st.session_state.get("user_name", "Customer")
            }

            # Get AI response using chatbot engine
            with st.spinner("Thinking..."):
                try:
                    response_data = get_chatbot_response(
                        user_message=final_prompt,
                        history=st.session_state['bot_messages'],
                        user_context=user_context,
                        uploaded_file=pending_file
                    )
                    full_content = response_data.get('content', "I couldn't process that. Please try again.")
                    sources = response_data.get('sources', [])
                    action = response_data.get('action')
                    ticket_id = response_data.get('ticket_id')
                    ticket_data = response_data.get('ticket_data')

                except Exception as e:
                    full_content = f"I encountered an error. Please try again or use the Submit Ticket form. (Error: {type(e).__name__})"
                    sources = []
                    action = None
                    ticket_id = None
                    ticket_data = None

            # Display assistant reply
            with chat_box:
                with st.chat_message("assistant"):
                    st.markdown(full_content)
                    if ticket_id:
                        st.info(f"Reference: {ticket_id}")

            # Save assistant message to history
            st.session_state['bot_messages'].append({
                "role": "assistant",
                "content": full_content,
                "sources": sources,
                "action": action,
                "ticket_id": ticket_id,
                "ticket_data": ticket_data
            })

            # Clear pending file
            st.session_state['bot_pending_file'] = None
            st.session_state['bot_file_key'] += 1

            st.rerun()



def page_agent_dashboard():
    """Agent Dashboard with ticket list and email interface."""
    st.markdown(utils.load_html("technician_dashboard_header.html"), unsafe_allow_html=True)
    
    # Get agent's tickets
    df = controller.get_dashboard_data()
    if df.empty:
        st.info("No tickets in the system.")
        return
    
    agent_id = st.session_state.get('agent_id')
    if not agent_id:
        st.error("Agent ID not found. Please log in again.")
        return
    
    # Filter for this agent
    my_tickets = df[df['assigned_agent_id'] == agent_id].copy() if 'assigned_agent_id' in df.columns else pd.DataFrame()
    
    if my_tickets.empty:
        st.info("You have no assigned tickets.")
        return
    
    # Tabs for Open/In Progress/Solved
    open_count = len(my_tickets[my_tickets['status'] == 'Open'])
    in_progress_count = len(my_tickets[my_tickets['status'] == 'In Progress'])
    solved_count = len(my_tickets[my_tickets['status'] == 'Closed'])
    
    tab1, tab2, tab3 = st.tabs([
        f"Open ({open_count})",
        f"In Progress ({in_progress_count})",
        f"Closed ({solved_count})"
    ])
    
    with tab1:
        open_tickets = my_tickets[my_tickets['status'] == 'Open'].sort_values(by='created_at', ascending=False)
        render_agent_ticket_interface(open_tickets, "open")
        
    with tab2:
        in_progress_tickets = my_tickets[my_tickets['status'] == 'In Progress'].sort_values(by='updated_at', ascending=False)
        render_agent_ticket_interface(in_progress_tickets, "in_progress")
    
    with tab3:
        solved_tickets = my_tickets[my_tickets['status'] == 'Closed'].sort_values(by='updated_at', ascending=False)
        render_agent_ticket_interface(solved_tickets, "solved")


def render_technician_performance(agent_id, my_tickets=None):
    """Renders the performance metrics and charts for a technician."""
    
    # Use detailed analytics from DB
    analytics = database.get_technician_analytics_detailed(agent_id)
    perf = analytics['performance_metrics']
    
    if not perf:
        st.info("No analytics data available yet. Start resolving tickets to see your performance!")
        return

    
    st.markdown("#### My Tickets")
    
    # Move Ticket Table to TOP
    try:
        tickets_df = database.get_technician_tickets(agent_id)
        if not tickets_df.empty:
            f1, f2, f3 = st.columns(3)
            
            with f1:
                company_query = st.text_input("Search Company", placeholder="Enter company name...")
            
            with f2:
                status_filter = st.selectbox("Status", ["All", "Open", "In Progress", "Closed"])
                
            with f3:
                sla_filter = st.selectbox("SLA", ["All", "Breached", "At Risk (<4h)"])
            
            filtered_df = tickets_df.copy()
            # Apply normalization to the status column
            if not filtered_df.empty:
                def quick_norm(s):
                    s = str(s).strip().lower()
                    if s in ['closed', 'resolved', 'completed', 'solved']: return 'Closed'
                    if s in ['in progress', 'inprogress', 'in_progress', 'pending']: return 'In Progress'
                    return 'Open'
                filtered_df['status'] = filtered_df['status'].apply(quick_norm)
            
            if company_query:
                filtered_df = filtered_df[filtered_df['partner'].str.contains(company_query, case=False, na=False)]
                
            if status_filter != "All":
                filtered_df = filtered_df[filtered_df['status'] == status_filter]
                
            if sla_filter == "Breached":
                filtered_df = filtered_df[filtered_df['sla_hours_remaining'] < 0]
            elif sla_filter == "At Risk (<4h)":
                filtered_df = filtered_df[(filtered_df['sla_hours_remaining'] >= 0) & (filtered_df['sla_hours_remaining'] < 4)]

            # Build custom columns for display
            table_data = []
            now = datetime.datetime.now()
            
            for idx, row in filtered_df.iterrows():
                try:
                    created_dt = pd.to_datetime(row['created_at'])
                    created_str = created_dt.strftime('%b %d, %H:%M')
                except:
                    created_dt = now
                    created_str = "-"
                    
                try:
                    if row['status'] == 'Closed' and row.get('updated_at'):
                        end_dt = pd.to_datetime(row['updated_at'])
                        delta = end_dt - created_dt
                    else:
                        delta = now - created_dt
                        
                    days = delta.days
                    hours = delta.seconds // 3600
                    if days > 0:
                        age_str = f"{days}d {hours}h"
                    else:
                        mins = (delta.seconds % 3600) // 60
                        age_str = f"{hours}h {mins}m"
                except:
                    age_str = "-"
                    
                status_val = row.get('status', 'Open')
                if status_val == 'Closed':
                    # Check if it was met or missed
                    # We can use get_updated_at if available or assume met if not calculated
                    # For simplicty based on request "for closed Resolved within SLA"
                    # We need to know if it breached.
                    # We can re-use logic or check sla_hours_remaining if it was frozen (it isn't usually frozen in DB schema unless we store it).
                    # Let's check deadline.
                    from sla_manager import get_deadline
                    deadline = get_deadline(str(created_dt), row.get('priority', 'Medium'))
                    if deadline:
                        end_check = pd.to_datetime(row.get('updated_at')) if row.get('updated_at') else now
                        if end_check <= deadline:
                             sla_str = "Closed within SLA"
                        else:
                             # Calculate overdue amount
                             over_delta = end_check - deadline
                             o_hours = over_delta.days * 24 + over_delta.seconds // 3600
                             sla_str = f"Closed Overdue by {o_hours} hrs"
                    else:
                        sla_str = "Closed"
                else:
                    # Open Ticket Logic
                    # sla_hours_remaining is already in row from get_technician_tickets
                    rem = row.get('sla_hours_remaining', 0)
                    if rem < 0:
                        sla_str = f"Breached: Overdue by {abs(int(rem))} hrs"
                    elif rem < 4:
                        sla_str = f"At Risk: {int(rem)} hrs remaining"
                    else:
                        sla_str = f"On Track: {int(rem)} hrs remaining"

                table_data.append({
                    'Ticket ID': row['ticket_id'],
                    'Company Name': row.get('partner', 'Internal'),
                    'User Name': row.get('user_id', 'Unknown'),
                    'Subject': row.get('subject', 'No Subject'),
                    'Status': row.get('status', 'Open'),
                    'Severity': row.get('priority', 'Medium'),
                    'Created On': created_str,
                    'Ticket Age': age_str,
                    'SLA Status': sla_str
                })
            
            display_df = pd.DataFrame(table_data)
            
            if not display_df.empty:
                st.dataframe(
                    display_df,
                    width="stretch",
                    hide_index=True
                )
            else:
                st.warning("No tickets match the selected filters.")
        else:
            st.info("You have no assigned tickets.")
    except Exception as e:
        st.error(f"Error loading ticket table: {e}")

    st.markdown("---")
    
    # Row 1: KPI Metrics (Adjusted to 4 columns)
    kp1, kp2, kp3, kp4 = st.columns(4)
    kp1.metric("Tickets", perf.get('total_handled', 0))
    kp2.metric("Resolved", perf.get('resolved', 0))
    kp3.metric("Initial Response Time", f"{perf.get('first_response_time_avg', 0)}h")
    kp4.metric("Mean Time to Resolve", f"{perf.get('mttr', 0)}h")
    
    st.markdown("---")
    
    # Row 2: Charts
    st.markdown("**Resolution Performance Trend**")
    if not analytics['productivity_trend'].empty:
        st.line_chart(analytics['productivity_trend'], x='Date', y='Resolved Count', color="#0f172a")
    else:
        st.info("Insufficient data for trend analysis.")
            
    st.markdown("---")
    
  
    
    # Row 3: Severity Pie Chart (Full Width)
    st.markdown("**Severity Handling**")
    if analytics['priority_distribution']:
        prio_df = pd.DataFrame(list(analytics['priority_distribution'].items()), columns=['Severity', 'Count'])
        
        # Define Colors
        color_map = {
            'Critical': '#dc2626', # Red
            'High': '#ea580c',     # Orange
            'Medium': '#3b82f6',   # Blue
            'Low': '#16a34a'       # Green
        }
        
        fig = px.pie(
            prio_df, 
            values='Count', 
            names='Severity', 
            hole=0.4,
            color='Severity',
            color_discrete_map=color_map
        )
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
        st.plotly_chart(fig, use_container_width=True, key="tech_perf_severity_chart")
    else:
        st.info("No severity data.")


    st.markdown("---")

    # Row 4: SLA Compliance Breakdown
    st.markdown("**SLA Compliance Breakdown**")
    sla_data = analytics.get('sla_compliance_breakdown', {'Compliant': 0, 'Breached': 0})
    # Check if we have data (sum of counts > 0)
    if sum(sla_data.values()) > 0:
        sla_df = pd.DataFrame(list(sla_data.items()), columns=['Status', 'Count'])
        fig_sla = px.pie(
            sla_df,
            values='Count',
            names='Status',
            hole=0.4,
            color='Status',
            color_discrete_map={'Compliant': '#16a34a', 'Breached': '#dc2626'}
        )
        fig_sla.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
        st.plotly_chart(fig_sla, use_container_width=True, key="tech_perf_sla_chart")
    else:
        st.info("No SLA data available.")

    st.markdown("---")

    # Row 5: Ticket Due Times
    st.markdown("**Ticket Due Times**")
    due_data = analytics.get('due_date_counts', {})
    if sum(due_data.values()) > 0:
        due_list = []
        for k, v in due_data.items():
            due_list.append({'Timeframe': k, 'Count': v})
        due_df = pd.DataFrame(due_list)
        
        # Sort manually for correct order
        order_cw = ['Overdue', 'Today', 'Tomorrow', 'This Week']
        due_df['Timeframe'] = pd.Categorical(due_df['Timeframe'], categories=order_cw, ordered=True)
        due_df = due_df.sort_values('Timeframe')
        
        # Use Plotly for better customization (thinner bars, horizontal labels)
        fig_due = px.bar(
            due_df,
            x='Timeframe',
            y='Count',
            text='Count', # Show numbers on bars
            color_discrete_sequence=['#64748b']
        )
        
        fig_due.update_layout(
            xaxis_title=None,
            yaxis_title=None,
            xaxis_tickangle=0, 
            bargap=0.7,        
            height=300,
            margin=dict(t=30, b=20, l=0, r=0),
            yaxis=dict(
                showgrid=True,
                dtick=1, 
                range=[0, due_df['Count'].max() + 1] # Ensure space for label on top of bar
            )
        )
        
        fig_due.update_traces(textposition='outside') # Put count above bar
        
        st.plotly_chart(fig_due, use_container_width=True, key="tech_perf_due_chart")
    else:
        st.info("No open tickets due.")


def render_agent_ticket_interface(tickets, tab_type):
    """Render ticket list and details interface for agents."""
    if tickets.empty:
        st.info(f"No {tab_type} tickets.")
        return
    
    # Auto-refresh every 5 seconds for real-time conversation
    st_autorefresh(interval=5000, key=f"agent_chat_refresh_{tab_type}")
    
    # Two-column layout: Ticket list | Ticket details
    col_list, col_details = st.columns([0.35, 0.65], gap="large")
    
    with col_list:
        st.markdown("### Tickets")
        
        # Initialize selected ticket
        if 'selected_agent_ticket' not in st.session_state:
            st.session_state['selected_agent_ticket'] = tickets.iloc[0]['ticket_id']
        
        # Ticket list
        # TICKET LIST - CLICKABLE RADIO CARDS WITH COLORED TEXT
        ticket_options = tickets['ticket_id'].tolist()
        
        def format_ticket_card(tid):
            row = tickets.loc[tickets['ticket_id'] == tid].iloc[0]
            subj = row.get('subject') or "No Subject"
            prio = row.get('priority', 'Medium')
            
            p_text = f":blue[{prio}]"
            if prio == "Critical": p_text = f":red[{prio}]"
            elif prio == "High": p_text = f":orange[{prio}]"
            elif prio == "Medium": p_text = f":blue[{prio}]"
            elif prio == "Low": p_text = f":green[{prio}]"
            
            return f"**{subj}**\n\n{tid} • {p_text}"

        current_sel = st.session_state.get('selected_agent_ticket')
        
        # Determine the index to highlight in this specific tab's list
        if current_sel in ticket_options:
            formatted_index = ticket_options.index(current_sel)
        else:
            # If the selected ticket is not in this list, do not select any radio option visually.
            # This prevents "background" tabs from overriding the selection logic or defaulting to index 0 incorrectly.
            formatted_index = None
        
        def update_selection():
            # Get the value from the specific widget key
            new_id = st.session_state[f"ticket_radio_group_{tab_type}"]
            prev_id = st.session_state.get('selected_agent_ticket')
            
            # Update global state
            st.session_state['selected_agent_ticket'] = new_id
            
            # Logic: Mark previous ticket as In Progress
            if prev_id and prev_id != new_id:
                try:
                    prev_ticket = controller.get_ticket_by_id(prev_id)
                    if prev_ticket and prev_ticket.get('status') == 'Open':
                        chat_history = database.get_chat_history(str(prev_id))
                        if any(msg.get('sender') == 'agent' for msg in chat_history):
                            prev_ticket['status'] = 'In Progress'
                            controller.update_ticket(prev_ticket)
                except Exception:
                    pass

        # We render the radio button. If the user clicks it, 'update_selection' runs and syncs the global state.
        st.radio(
            "Select Ticket",
            options=ticket_options,
            format_func=format_ticket_card,
            index=formatted_index,
            label_visibility="collapsed",
            key=f"ticket_radio_group_{tab_type}",
            on_change=update_selection
        )
        
        # No extra 'if changed:' block needed, callback handles it.
        
    with col_details:
        # Get selected ticket (use the potentially updated current_sel)
        selected_id = st.session_state.get('selected_agent_ticket')
        if not selected_id:
            st.info("Select a ticket to view details.")
            return
        
        ticket = controller.get_ticket_by_id(selected_id)
        if not ticket:
            st.error("Ticket not found.")
            return
        
        # Ticket header
        st.markdown(f"### {ticket.get('subject') or 'No Subject'}")
        
        # Ticket metadata
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"**Status:** {ticket.get('status', 'Open')}")
        with c2:
            priority = ticket.get('priority', 'Medium')
            st.markdown(f"**Priority:** {priority}")
        with c3:
            st.markdown(f"**Ticket ID:** {selected_id}")
        
        st.markdown("---")
        
        # Customer info
        st.markdown(f"**From:** {ticket.get('email', 'N/A')}")
        st.markdown(f"**Created:** {ticket.get('created_at', 'N/A')}")
        
        st.markdown("---")
        
        # Description
        st.markdown("**Description:**")
        st.write(utils.strip_html(ticket.get('description', 'No description.')))
        
        # Attachments
        att_data = ticket.get('attachment')
        if att_data and att_data != "None":
            try:
                attachments = json.loads(att_data)
                if not isinstance(attachments, list):
                    attachments = [attachments]
            except:
                attachments = [att_data]
                
            import oci_storage
            for idx, att_path in enumerate(attachments):
                display_name = att_path.split("/")[-1]
                st.markdown(f"**Attachment {idx+1}:** {display_name}")
                try:
                    par_url = oci_storage.generate_download_url(att_path)
                    if att_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                        st.image(par_url, width="stretch")
                    st.link_button(f"Download {display_name}", par_url)
                except Exception as oci_err:
                    st.warning(f"Could not retrieve attachment from OCI: {oci_err}")
        
        st.markdown("---")
        
        # Comments/Timeline
        st.markdown("<b>Conversation History</b>", unsafe_allow_html=True)
        # Use get_chat_history instead of get_comments to see all messages
        chat_history = database.get_chat_history(selected_id)
        if chat_history:
            for msg in chat_history:
                sender = msg.get('sender', 'unknown')
                message = msg.get('message', '')
                timestamp = msg.get('timestamp', '')
                
                if sender == 'ai' or sender == 'bot':
                    # AI message - Left
                    with st.chat_message("assistant", avatar="🤖"):
                        st.markdown(message)
                        st.caption(f"AI • {timestamp}")
                
                elif sender == 'agent':
                    # Agent message - Right (Tech is the 'user' of this dashboard technically)
                    with st.chat_message("user", avatar="👨‍🔧"):
                        if message and message.strip() and message.lower() != "none":
                            st.markdown(message)
                        
                        if msg.get('attachment'):
                            try:
                                import oci_storage
                                par_url = oci_storage.generate_download_url(msg['attachment'])
                                if msg['attachment'].lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                                    st.image(par_url, width="stretch")
                                else:
                                    st.markdown(utils.load_html("chat_attachment.html").format(filename=os.path.basename(msg['attachment'])), unsafe_allow_html=True)
                                    st.link_button("Download", par_url)
                            except Exception as oci_err:
                                st.caption(f"Attachment unavailable: {oci_err}")
                        st.caption(f"You • {timestamp}")
                
                elif sender == 'user' or sender == 'customer':
                    # Customer message - Left
                    cust_name = ticket.get('user_id', 'Customer')
                    with st.chat_message("assistant", avatar="👤"):
                        if message and message.strip() and message.lower() != "none":
                            st.markdown(message)
                            
                        if msg.get('attachment'):
                            try:
                                import oci_storage
                                par_url = oci_storage.generate_download_url(msg['attachment'])
                                if msg['attachment'].lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                                    st.image(par_url, width="stretch")
                                else:
                                    st.markdown(utils.load_html("chat_attachment_white.html").format(filename=os.path.basename(msg['attachment'])), unsafe_allow_html=True)
                                    st.link_button("Download", par_url)
                            except Exception as oci_err:
                                st.caption(f"Attachment unavailable: {oci_err}")
                        st.caption(f"{cust_name} • {timestamp}")
        else:
            st.caption("No conversation history yet.")
        
        
        
        # Reply logic (only for unsolved tickets)
        if tab_type != "solved":
            st.markdown("---")
            
            # Action controls outside chat input for better visibility
            # Horizontal layout for Agent controls - Improved ratio to prevent overlap
            with st.container():
                col_att, col_input = st.columns([0.15, 0.85], vertical_alignment="center", gap="medium")
                with col_att:
                    with st.popover("📎", help="Attach a file"):
                        agent_chat_attachment = st.file_uploader("Upload Image/Doc", type=['png','jpg','jpeg','pdf','docx','txt'], key=f"agent_attach_{selected_id}_{tab_type}_{st.session_state['agent_attach_counter']}")
                        if agent_chat_attachment:
                            if st.button("Send Message", key=f"send_att_btn_agent_{selected_id}_{tab_type}", width="stretch", type="primary"):
                                st.session_state[f"force_send_agent_{selected_id}_{tab_type}"] = True
                                st.rerun()
                
                with col_input:
                    reply_text = st.chat_input("Type your solution/reply...", key=f"agent_chat_input_{selected_id}_{tab_type}")

            # Secondary controls (Email & Resolution)
            c2, c3 = st.columns([0.4, 0.6], gap="small")
            with c2:
                send_email_checkbox = st.checkbox("Email customer", value=False, key=f"mail_cb_{selected_id}_{tab_type}")
            with c3:
                mark_resolved = st.button("Mark Closed", width="stretch", type="primary", key=f"res_btn_{selected_id}_{tab_type}")

            if reply_text or st.session_state.get(f"force_send_agent_{selected_id}_{tab_type}"):
                # Clear the force_send flag
                if f"force_send_agent_{selected_id}_{tab_type}" in st.session_state:
                    del st.session_state[f"force_send_agent_{selected_id}_{tab_type}"]
                author = st.session_state.get('user_name', 'Agent')
                
                saved_agent_chat_path = None
                if agent_chat_attachment:
                    import oci_storage
                    object_name = f"tickets/chat/{selected_id}_{int(time.time())}_{agent_chat_attachment.name}"
                    content_type = oci_storage.get_content_type(agent_chat_attachment.name)
                    try:
                        oci_storage.upload_file(agent_chat_attachment.getbuffer(), object_name, content_type)
                        saved_agent_chat_path = object_name
                    except Exception as oci_err:
                        st.warning(f"Could not upload attachment to OCI: {oci_err}")
                    # Increment counter to clear uploader
                    st.session_state['agent_attach_counter'] += 1

                database.add_chat_message(selected_id, 'agent', (reply_text or "").strip(), saved_agent_chat_path)
                
                # Do NOT change status immediately - will change when technician leaves ticket
                # if ticket.get('status') == 'Open':
                #     ticket['status'] = 'In Progress'
                #     controller.update_ticket(ticket)
                
                # Send email if checkbox is checked
                if send_email_checkbox and ticket.get('email'):
                    customer_email = ticket['email']
                    subject = f"Re: {ticket.get('subject', 'Your Support Ticket')} [Ticket #{selected_id}]"
                    body = f"""Dear Customer,\n\nThank you for contacting PCB Apps Support.\n\n{reply_text}\n\n---\nTicket ID: {selected_id}\nBest regards,\n{author}\nPCB Apps Support Team"""
                    utils.send_email(customer_email, subject, body)
                
                st.rerun()
            
            if mark_resolved:
                ticket['status'] = 'Closed'
                controller.update_ticket(ticket)
                author = st.session_state.get('user_name', 'Agent')
                database.add_chat_message(selected_id, 'agent', f"Ticket marked as closed by {author}")
                st.success("Ticket marked as closed!")
                st.session_state['selected_agent_ticket'] = None
                st.rerun()
        else:
            st.success("This ticket has been resolved.")
            
            st.divider()
            
            # Check if already promoted
            existing_kb = database.get_kb_article_by_source(f"ticket_{selected_id}")
            
            if existing_kb:
                st.success("This ticket is promoted to KB")
                if st.button("Delete from KB", key=f"delete_kb_{selected_id}_{tab_type}", type="secondary", width="stretch"):
                    with st.spinner("Removing from Knowledge Base..."):
                        success, message = controller.remove_ticket_from_kb(selected_id)
                        if success:
                            st.rerun()
                        else:
                            st.error(message)
            else:
                if st.button("Promote to KB", key=f"promote_kb_{selected_id}_{tab_type}", type="primary", width="stretch"):
                    with st.spinner("Converting ticket to Knowledge Base article..."):
                        author = st.session_state.get('user_name', 'Technician')
                        success, message = controller.promote_ticket_to_kb(selected_id, technician_name=author)
                        if success:
                            st.rerun()
                        else:
                            st.error(message)

def page_admin_dashboard():
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "Overview",
        "Team Status",
        "Analytics",
        "Storage"
    ])
    
    with tab1:
        df = controller.get_dashboard_data()
        if df.empty:
            st.info("No tickets.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Tickets", len(df))
            c2.metric("Open Tickets", len(df[df['status']=='Open']))
            c3.metric("Critical Tickets", len(df[df['priority']=='Critical']))
            c4.metric("SLA Breaches", 0, delta="Good", delta_color="normal")
            
            st.markdown("---")
            page_all_tickets_view()

    with tab2:
        
        import database
        all_agents = database.get_all_agents()
        workloads = database.get_agent_workload()
        
        team_data = []
        for agent in all_agents:
            count = workloads.get(agent['agent_id'], 0)
            topics_str = ", ".join(agent.get('topics', []))
            
            status = "Available"
            if count > 5: status = "Busy"
            if count > 10: status = "Overloaded"
            
            live = "Online" if agent.get('live_chat_active', 1) else "Offline"
            
            role_display = "Technician" if agent.get('role', 'agent') == 'agent' else agent.get('role', 'agent').title()
            
            team_data.append({
                "ID": agent['agent_id'],
                "Name": agent['name'],
                "Role": role_display,
                "Active Tickets": count,
                "Status": status,
                "Live Chat": live,
                "Department": topics_str
            })
            
        if team_data:
            df_team = pd.DataFrame(team_data)
            df_team = df_team.sort_values(by="Active Tickets", ascending=True)
            
            st.caption("Select a technician to see what they are working on.")
            
            event = st.dataframe(
                df_team,
                on_select="rerun",
                selection_mode="single-row",
                hide_index=True,
                column_config={
                    "ID": None, 
                    "Active Tickets": None,
                    "Live Chat": None,
                    "Status": None
                },
                width="stretch"
            )
            
            # Drill Down Logic
            if len(event.selection.rows) > 0:
                idx = event.selection.rows[0]
                selected_agent_id = df_team.iloc[idx]['ID']
                selected_agent_name = df_team.iloc[idx]['Name']
                
                st.markdown("---")
                st.markdown(f"### Workload: {selected_agent_name}")
                
                all_tickets = controller.get_dashboard_data()
                if not all_tickets.empty:
                    col_name = 'assigned_agent_id' if 'assigned_agent_id' in all_tickets.columns else 'assigned_agent'
                    if col_name in all_tickets.columns:
                        agent_tickets = all_tickets[all_tickets[col_name] == selected_agent_id]
                        active_agent_tickets = agent_tickets[agent_tickets['status'].isin(['Open', 'In Progress', 'Pending', 'Escalated'])]
                        
                        if active_agent_tickets.empty:
                            st.success(f"{selected_agent_name} has no active tickets.")
                        else:
                            st.dataframe(
                                active_agent_tickets[['ticket_id', 'subject', 'priority', 'status', 'created_at', 'ticket_type']],
                                width="stretch", hide_index=True
                            )
        else:
            st.info("No agents found in database.")

    with tab3:
        st.write("### Advanced Business Intelligence")
        
        import database
        analytics = database.get_admin_analytics()
        kb_data = database.get_kb_analytics()
        res_data = database.get_resolution_analytics()
        tags_data = database.get_tag_analytics()
        search_data = database.get_kb_search_analytics()
        
        # Row 1: High Level Metrics
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("AI Resolution Rate", f"{(res_data['AI Resolved'] / (res_data['AI Resolved'] + res_data['Human Resolved'] + 0.1) * 100):.1f}%")
        with m2:
            st.metric("KB Articles Tracked", len(kb_data['most_viewed']))
        with m3:
            total_tags = tags_data.sum() if not tags_data.empty else 0
            st.metric("Unique Tags Applied", len(tags_data))

        st.divider()

        # Row 1.5: Ticket Trend Chart
        st.subheader("Ticket Volume Trend")
        df = controller.get_dashboard_data()
        
        if not df.empty and 'created_at' in df.columns:
            # Period Selector
            trend_col1, trend_col2 = st.columns([1, 3])
            with trend_col1:
                period = st.selectbox("Granularity", ["Hourly", "Daily", "Weekly", "Monthly"], index=1, key="trend_period")
            
            # Data Processing
            df_trend = df.copy()
            df_trend['created_at'] = pd.to_datetime(df_trend['created_at'])
            df_trend = df_trend.sort_values('created_at')
            
            # Map resampling codes
            resample_map = {"Hourly": "h", "Daily": "D", "Weekly": "W", "Monthly": "ME"}
            trend_data = df_trend.set_index('created_at').resample(resample_map[period]).size().reset_index()
            trend_data.columns = ['Date', 'Ticket Count']
            
            # Render Trend
            fig_trend = px.area(trend_data, x='Date', y='Ticket Count', 
                              title=f"{period} Ticket Inflow",
                              color_discrete_sequence=['#ff4b4b'],
                              template="plotly_white")
            fig_trend.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=350)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No historical data available for trend analysis.")

        st.divider()

        # Row 2: Distribution Charts
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Tickets by Department")
            if not df.empty and 'topic' in df.columns:
                dept_counts = df['topic'].value_counts().reset_index()
                dept_counts.columns = ['Department', 'Count']
                fig_dept = px.pie(dept_counts, values='Count', names='Department', 
                                hole=0.4, 
                                color_discrete_sequence=px.colors.qualitative.Safe)
                fig_dept.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300)
                st.plotly_chart(fig_dept, use_container_width=True)
            else:
                st.info("No topic data available.")

        with col2:
            st.subheader("Resolution Source")
            res_df = pd.DataFrame(list(res_data.items()), columns=['Source', 'Tickets'])
            fig_res = px.pie(res_df, values='Tickets', names='Source', 
                           hole=0.4,
                           color_discrete_map={'AI Resolved': '#00d4ff', 'Human Resolved': '#ff4b4b'})
            fig_res.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300)
            st.plotly_chart(fig_res, use_container_width=True)
            st.caption("Tickets resolved by AI vs Technicians.")

        st.divider()

        # Row 3: KB Analytics (Top Articles Only)
        st.subheader("Top Articles")
        if not kb_data['most_viewed'].empty:
            st.dataframe(kb_data['most_viewed'], width="stretch", hide_index=True)
        else:
            st.info("No KB views recorded yet.")

        st.divider()

    with tab4:
        st.write("### OCI Bucket Storage — ticketing-attachments")
        st.caption("All attachment files are stored securely in Oracle Cloud Object Storage (us-ashburn-1). Download links expire after 24 hours.")

        import oci_storage

        with st.spinner("Fetching files from OCI bucket..."):
            files = oci_storage.list_all_files()

        if not files:
            st.info("No files found in the bucket yet. Attachments will appear here once tickets with files are submitted.")
        else:
            total_files = len(files)
            total_size_kb = sum(f['size_kb'] for f in files)
            total_size_mb = round(total_size_kb / 1024, 3)

            # Summary metrics
            sm1, sm2, sm3 = st.columns(3)
            sm1.metric("Total Files", total_files)
            sm2.metric("Total Storage", f"{total_size_mb} MB")
            sm3.metric("Bucket", "ticketing-attachments")

            st.markdown("---")
            st.subheader("File List")

            # Build display table
            for f in files:
                col_name, col_tid, col_size, col_date, col_dl = st.columns([3, 2, 1.5, 2, 1.5])
                col_name.write(f["display_name"])
                col_tid.write(f["ticket_id"])
                col_size.write(f"{f['size_kb']} KB")
                col_date.write(f["modified"])
                try:
                    par_url = oci_storage.generate_download_url(f["name"])
                    col_dl.link_button("Download", par_url)
                except Exception as e:
                    col_dl.caption("Unavailable")

def page_analytics():
    """Role-aware analytics page."""
    role = st.session_state.get('role')
    
    if role == 'agent':
        agent_id = st.session_state.get('agent_id')
        if agent_id:
             render_technician_performance(agent_id)
        else:
             st.error("Agent ID not found.")
        return

    st.markdown(utils.load_html("my_activity_header.html"), unsafe_allow_html=True)
    
    import database
    user_email = st.session_state.get('user_email')
    cust_stats = database.get_customer_analytics(user_email)
    
    if not cust_stats:
        st.info("Raise your first ticket to see personalized analytics!")
        return

    # Key Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Tickets Raised", cust_stats['total'])
    col2.metric("AI Resolution Rate", f"{cust_stats['ai_resolution_rate']:.1f}%")
    col3.metric("Avg Resolution Time", f"{cust_stats['avg_tat']:.1f} hrs" if cust_stats['avg_tat'] > 0 else "N/A")
    
    st.divider()

    # Visualizations
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("Your Common Topics")
        if not cust_stats['topics'].empty:
            st.bar_chart(cust_stats['topics'])
        else:
            st.caption("Insufficient data for topic breakdown.")
            
    with col_r:
        st.subheader("Ticket Breakdown")
        df = controller.get_dashboard_data()
        my_df = df[df['email'] == user_email] if not df.empty else pd.DataFrame()
        if not my_df.empty:
            st.bar_chart(my_df['status'].value_counts())
        else:
            st.info("Status distribution currently unavailable.")
 



def page_login():
    # Hide sidebar on login page - Minimal visibility override
    # REMOVED sidebar hiding CSS to prevent visibility issues
    pass
    
    st.markdown(utils.load_html("login_header.html"), unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", type="primary", width="stretch")
            
            if submitted:
                user = utils.check_login(username.lower(), password)
                if user:
                    st.session_state['authenticated'] = True
                    st.session_state['username'] = username.lower()
                    st.session_state['role'] = user['role']
                    st.session_state['user_name'] = user['name']
                    st.session_state['user_email'] = user.get('email', '') 
                    
                    # Store Agent ID if agent
                    if user['role'] == 'agent':
                        # Look up in DB
                        import database
                        # Note: utils.USERS has emails, we use that.
                        agent_rec = database.get_agent_by_email(user.get('email', ''))
                        if agent_rec:
                            st.session_state['agent_id'] = agent_rec['agent_id']
                        else:
                            st.session_state['agent_id'] = None
                    
                    # Redirect based on role
                    if user['role'] == 'agent':
                        st.session_state['page'] = 'Technician Dashboard'
                    else:
                        st.session_state['page'] = 'Home'
                        
                    st.rerun()
                else:
                    st.error("Invalid username or password")

        pass # Credentials removed as requested

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    page_login()
else:
    
    # Mark current ticket as "In Progress" when leaving Technician Dashboard
    current_page = st.session_state['page']
    last_page = st.session_state.get('_last_page_visited')
    
    if last_page == 'Technician Dashboard' and current_page != 'Technician Dashboard':
        # Leaving Technician Dashboard - mark current ticket as "In Progress"
        current_ticket_id = st.session_state.get('selected_agent_ticket')
        if current_ticket_id:
            try:
                current_ticket = controller.get_ticket_by_id(current_ticket_id)
                if current_ticket and current_ticket.get('status') == 'Open':
                    # Check if technician actually replied
                    chat_history = database.get_chat_history(current_ticket_id)
                    agent_messages = [msg for msg in chat_history if msg.get('sender') == 'agent']
                    if agent_messages:
                        current_ticket['status'] = 'In Progress'
                        controller.update_ticket(current_ticket)
            except:
                pass  # Fail silently
    
    # Update last page visited
    st.session_state['_last_page_visited'] = current_page
    
    render_sidebar()
    
    # Sync internal state if needed (sidebar radio already updates st.session_state['page'])

    if st.session_state['page'] == 'Home':
        page_home()
    # AI Support removed from customer navigation
    # elif st.session_state['page'] == 'AI Support':
    #     page_ai_support()
    elif st.session_state['page'] == 'Submit Ticket':
        page_submit_ticket()
    elif st.session_state['page'] == 'My Tickets':
        page_dashboard()
    elif st.session_state['page'] == 'Dashboard':
        page_customer_table_view()
    elif st.session_state['page'] == 'Technician Dashboard':
        page_agent_dashboard()
    elif st.session_state['page'] == 'Admin Dashboard':
        page_admin_dashboard()
    elif st.session_state['page'] == 'Knowledge Base':
        import kb_manager_ui
        kb_manager_ui.render_kb_manager()

    elif st.session_state['page'] == 'Ticket Details':
        page_ticket_details()
    elif st.session_state['page'] in ['Analytics', 'My Analytics']:
        page_analytics()

    # Render Floating Bot for Customers
    if st.session_state.get('role') == 'customer':
        render_floating_bot()
