import oracledb
import os
import pandas as pd
import json
import datetime
import re
import uuid
import ast
import oci_config

DB_USER = "EDI_TEST"
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Dynamically locate Wallet and Instant Client based on the project's current folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to the unzipped wallet folder
WALLET_DIR = os.path.join(BASE_DIR, "Wallet_EDI")
# Path to the extracted Instant Client (Thick Mode)
IC_DIR = os.path.join(BASE_DIR, "instantclient")

# Service name from tnsnames.ora
DSN = "pocediadw_high"


# Initialize Oracle Client (Thick Mode) - Required for macOS SSL / Wallet stability
try:
    if not os.environ.get("ORACLE_INIT"):
        oracledb.init_oracle_client(lib_dir=IC_DIR)
        os.environ["ORACLE_INIT"] = "1"
except Exception as e:
    if "DPI-1047" not in str(e): # Ignore already initialized
        print(f"Warning: Oracle Client Init: {e}")

_pool = None

def get_pool():
    """Initializes and returns the global Oracle connection pool using THICK MODE."""
    global _pool
    if _pool is None:
        try:
            _pool = oracledb.create_pool(
                user=DB_USER,
                password=DB_PASSWORD,
                dsn=DSN,
                min=2,
                max=10,
                increment=1,
                config_dir=WALLET_DIR,
                wallet_location=WALLET_DIR,
                wallet_password="WalletPassword123"
            )
            print("Successfully initialized Oracle Connection Pool (Thick Mode).")
        except Exception as e:
            print(f"FAILED to initialize Oracle Connection Pool: {e}")
            raise e
    return _pool

def output_type_handler(cursor, name, default_type, size, precision, scale):
    """Handler to automatically convert CLOBs to strings for faster processing."""
    if default_type == oracledb.DB_TYPE_CLOB:
        return cursor.var(oracledb.DB_TYPE_LONG, arraysize=cursor.arraysize)
    if default_type == oracledb.DB_TYPE_BLOB:
        return cursor.var(oracledb.DB_TYPE_LONG_RAW, arraysize=cursor.arraysize)

def get_connection():
    """Returns a connection from the global Oracle connection pool."""
    try:
        conn = get_pool().acquire()
        # Set output type handler for this connection to handle CLOBs efficiently
        conn.outputtypehandler = output_type_handler
        return conn
    except Exception as e:
        print(f"Oracle Pool Acquisition Error: {e}")
        raise e

def init_db():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT table_name FROM user_tables")
        tables = [row[0] for row in c.fetchall()]
        print(f"Connected to Oracle. Found tables: {tables}")
    except Exception as e:
        if "ORA-28001" in str(e):
             print(f"FATAL: Password for EDI_TEST has expired. Please reset it in OCI Console.")
        elif "ORA-01017" in str(e):
             print(f"FATAL: Invalid username/password. Password used: {DB_PASSWORD[:3]}***")
        else:
             print(f"Database Initialization/Check failed: {e}")
    finally:
        if conn: conn.close()




def get_all_kb_articles():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        query = "SELECT id, title, body, category, source_id, created_at, updated_at FROM kb_content ORDER BY created_at DESC"
        c.execute(query)
        columns = [col[0].lower() for col in c.description]
        articles = []
        for row in c.fetchall():
            data = dict(zip(columns, row))
            # CLOB handled by output_type_handler now
            articles.append(data)
        return articles
    finally:
        if conn: conn.close()

def save_kb_article(article_data):
    conn = get_connection()
    c = conn.cursor()
    
    if article_data.get('id'):
        query = "UPDATE kb_content SET title=:1, body=:2, category=:3, source_id=:4, updated_at=SYSTIMESTAMP WHERE id=:5"
        c.execute(query, (article_data['title'], article_data['body'], article_data.get('category', 'General'), article_data.get('source_id'), article_data['id']))
    else:
        query = "INSERT INTO kb_content (title, body, category, source_id, created_at, updated_at) VALUES (:1, :2, :3, :4, SYSTIMESTAMP, SYSTIMESTAMP)"
        c.execute(query, (article_data['title'], article_data['body'], article_data.get('category', 'General'), article_data.get('source_id')))
            
    conn.commit()
    conn.close()



def delete_kb_article(article_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM kb_content WHERE id=:1", (article_id,))
    conn.commit()
    conn.close()

def get_kb_article_by_source(source_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM kb_content WHERE source_id=:1", (source_id,))
    row = c.fetchone()
    if row:
        columns = [col[0].lower() for col in c.description]
        article = dict(zip(columns, row))
        if hasattr(article.get('body'), 'read'): article['body'] = article['body'].read()
        conn.close()
        return article
    conn.close()
    return None


def query_to_df(query, conn, params=None):
    """Helper to convert SQL query results to a DataFrame without triggering Pandas DBAPI2 warnings."""
    c = conn.cursor()
    if params:
        c.execute(query, params)
    else:
        c.execute(query)
    if c.description:
        columns = [col[0].lower() for col in c.description]
        return pd.DataFrame(c.fetchall(), columns=columns)
    return pd.DataFrame()

def get_tickets_summary_df():
    """Returns a DataFrame with only the essential columns for high-performance dashboard lists."""
    conn = None
    try:
        conn = get_connection()
        # Exclude large CLOBs like description and attachment for the summary view
        # Include topic, email and user_id as they are needed for filtering and display
        query = "SELECT ticket_id, subject, status, priority, topic, email, user_id, assigned_agent_id, created_at, updated_at FROM tickets"
        df = query_to_df(query, conn)
        return df
    except Exception as e:
        print(f"Error fetching tickets summary: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()

def get_all_tickets_df():
    """Fetches all tickets. Use get_tickets_summary_df for dashboards instead."""
    conn = None
    try:
        conn = get_connection()
        # Since we have output_type_handler, CLOBs are fetched as strings automatically
        df = query_to_df("SELECT * FROM tickets", conn)
        return df
    except Exception as e:
        print(f"Error fetching tickets df: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()

def get_ticket_status_counts():
    """Returns a distribution of ticket statuses for pie charts."""
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT status, COUNT(*) FROM tickets GROUP BY status")
        rows = c.fetchall()
        return {r[0]: r[1] for r in rows}
    except Exception as e:
        print(f"Error fetching status counts: {e}")
        return {}
    finally:
        if conn: conn.close()

def get_ticket_priority_counts():
    """Returns counts of tickets by priority level."""
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT priority, COUNT(*) FROM tickets GROUP BY priority")
        rows = c.fetchall()
        return {r[0]: r[1] for r in rows}
    except Exception as e:
        print(f"Error fetching priority counts: {e}")
        return {}
    finally:
        if conn: conn.close()

def get_user_tickets_summary(email):
    """Retrieves a summarized list of tickets for a specific user (email)."""
    df = get_tickets_summary_df()
    if df.empty: return []
    user_records = df[df['email'].str.lower() == email.lower()]
    return user_records.to_dict('records')

def get_ticket_volume_trends():
    """Groups tickets by creation month for charts."""
    conn = None
    try:
        conn = get_connection()
        query = "SELECT TO_CHAR(created_at, 'YYYY-MM'), COUNT(*) FROM tickets GROUP BY TO_CHAR(created_at, 'YYYY-MM') ORDER BY 1"
        c = conn.cursor()
        c.execute(query)
        rows = c.fetchall()
        return {r[0]: r[1] for r in rows}
    except Exception as e:
        print(f"Error fetching trends: {e}")
        return {}
    finally:
        if conn: conn.close()

def save_ticket(ticket_data):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM tickets WHERE ticket_id = :1", (ticket_data['ticket_id'],))
    exists = c.fetchone()
    
    res_timer_raw = ticket_data.get('resolution_time')
    if isinstance(res_timer_raw, str):
        match = re.search(r'\d+', res_timer_raw)
        res_time = int(match.group()) if match else 0
    elif res_timer_raw is None:
        res_time = 0
    else:
        res_time = int(res_timer_raw)

    params = (
        ticket_data.get('description'), ticket_data.get('topic'), ticket_data.get('priority'),
        ticket_data.get('status'), res_time, ticket_data.get('user_id'),
        ticket_data.get('email'), ticket_data.get('subject'), ticket_data.get('partner'),
        ticket_data.get('attachment'), ticket_data.get('auto_tags'),
        ticket_data.get('instance'), ticket_data.get('deployment_type'), ticket_data.get('ticket_type'),
        ticket_data.get('version'), ticket_data.get('connected_systems'),
        ticket_data.get('customer_case_ref'), ticket_data.get('hypercare'),
        ticket_data.get('assigned_agent_id'), ticket_data.get('rca'),
        ticket_data.get('issue_id'), # NEW: The MSG- interaction ID
        ticket_data['ticket_id']
    )

    if exists:
        attachment_val = ticket_data.get('attachment')
        if attachment_val is None:
            query = """UPDATE tickets SET description=:1, topic=:2, priority=:3, status=:4, 
                       resolution_time=:5, user_id=:6, email=:7, subject=:8, partner=:9, 
                       auto_tags=:10, instance=:11, deployment_type=:12, 
                       ticket_type=:13, version=:14, connected_systems=:15, customer_case_ref=:16, 
                       hypercare=:17, assigned_agent_id=:18, rca=:19, issue_id=:20, updated_at=SYSTIMESTAMP WHERE ticket_id=:21"""
            update_params = (
                params[0], params[1], params[2], params[3], params[4],
                params[5], params[6], params[7], params[8],
                params[10], params[11], params[12], params[13], params[14],
                params[15], params[16], params[17], params[18], params[19],
                params[20], # issue_id
                ticket_data['ticket_id']
            )
        else:
            query = """UPDATE tickets SET description=:1, topic=:2, priority=:3, status=:4, 
                       resolution_time=:5, user_id=:6, email=:7, subject=:8, partner=:9, 
                       attachment=:10, auto_tags=:11, instance=:12, deployment_type=:13, 
                       ticket_type=:14, version=:15, connected_systems=:16, customer_case_ref=:17, 
                       hypercare=:18, assigned_agent_id=:19, rca=:20, issue_id=:21, updated_at=SYSTIMESTAMP WHERE ticket_id=:22"""
            update_params = params
        c.execute(query, update_params)
    else:
        # Reorder params for INSERT
        insert_params = (
            ticket_data['ticket_id'], params[0], params[1], params[2], params[3],
            params[4], params[5], params[6], params[7], params[8],
            params[9], params[10], params[11], params[12], params[13],
            params[14], params[15], params[16], params[17], params[18], params[19],
            params[20]  # issue_id
        )
        query = """INSERT INTO tickets (ticket_id, description, topic, priority, status, 
                   resolution_time, user_id, email, subject, partner, attachment, auto_tags, 
                   instance, deployment_type, ticket_type, version, connected_systems, 
                   customer_case_ref, hypercare, assigned_agent_id, rca, issue_id, created_at, updated_at) 
                   VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14, :15, :16, :17, :18, :19, :20, :21, :22, SYSTIMESTAMP, SYSTIMESTAMP)"""
        c.execute(query, insert_params)
    
    # --- SYNC: Back-fill the ticket_id into the BOT_HEALTH_LOGS table ---
    if ticket_data.get('issue_id'):
        try:
            c.execute(
                "UPDATE BOT_HEALTH_LOGS SET TICKET_ID = :1 WHERE ISSUE_ID = :2",
                (ticket_data['ticket_id'], ticket_data['issue_id'])
            )
            print(f"[DB Sync] Linked Ticket {ticket_data['ticket_id']} back to Interaction {ticket_data['issue_id']}")
        except Exception as sync_err:
            print(f"[DB Sync Warning] Failed to link ticket to log: {sync_err}")

    conn.commit()
    conn.close()

def update_ticket_attachment(ticket_id, attachment_json):
    """
    Directly updates only the attachment column for a given ticket_id.
    Used after OCI upload so the object name is reliably written to ADW.
    attachment_json : JSON string e.g. '["tickets/TKT-001/0_file.png"]'
    """
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "UPDATE tickets SET attachment = :1, updated_at = SYSTIMESTAMP WHERE ticket_id = :2",
            (attachment_json, ticket_id)
        )
        conn.commit()
        print(f"[DB] attachment updated for ticket {ticket_id}: {attachment_json}")
    except Exception as e:
        print(f"[DB] ERROR updating attachment for {ticket_id}: {e}")
        raise
    finally:
        if conn:
            conn.close()




def _parse_agent_data(d):
    """Helper to parse JSON fields in agent data."""
    for key in ['topics', 'instances']:
        val = d.get(key)
        if val and isinstance(val, str):
            try: d[key] = json.loads(val)
            except: d[key] = []
        elif not val: d[key] = []
    return d

def get_all_agents():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM agents WHERE active=1")
        columns = [col[0].lower() for col in c.description]
        agents = []
        for row in c.fetchall():
            d = dict(zip(columns, row))
            agents.append(_parse_agent_data(d))
        return agents
    finally:
        if conn: conn.close()

def get_agent_by_id(agent_id):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM agents WHERE agent_id=:1", (agent_id,))
        row = c.fetchone()
        if row:
            columns = [col[0].lower() for col in c.description]
            d = dict(zip(columns, row))
            return _parse_agent_data(d)
        return None
    finally:
        if conn: conn.close()

def get_agent_by_email(email):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM agents WHERE email=:1", (email,))
        row = c.fetchone()
        if row:
            columns = [col[0].lower() for col in c.description]
            d = dict(zip(columns, row))
            return _parse_agent_data(d)
        return None
    finally:
        if conn: conn.close()

def get_agent_workload():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        # Workload includes all tickets that are not 'Closed'
        c.execute("SELECT assigned_agent_id, COUNT(*) FROM tickets WHERE status NOT IN ('Closed', 'Resolved', 'Solved', 'completed') GROUP BY assigned_agent_id")
        rows = c.fetchall()
        return {r[0]: r[1] for r in rows if r[0]}
    finally:
        if conn: conn.close()

def save_agent(agent_data):
    conn = get_connection()
    c = conn.cursor()
    topics_json = json.dumps(agent_data.get('topics', []))
    instances_json = json.dumps(agent_data.get('instances', []))
    
    c.execute("SELECT 1 FROM agents WHERE agent_id=:1", (agent_data['agent_id'],))
    exists = c.fetchone()
    
    if exists:
        query = "UPDATE agents SET name=:1, email=:2, role=:3, topics=:4, instances=:5, active=:6, live_chat_active=:7 WHERE agent_id=:8"
        c.execute(query, (agent_data['name'], agent_data['email'], agent_data.get('role', 'agent'), topics_json, instances_json, agent_data.get('active', 1), agent_data.get('live_chat_active', 1), agent_data['agent_id']))
    else:
        query = "INSERT INTO agents (agent_id, name, email, role, topics, instances, active, live_chat_active, created_at) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, SYSTIMESTAMP)"
        c.execute(query, (agent_data['agent_id'], agent_data['name'], agent_data['email'], agent_data.get('role', 'agent'), topics_json, instances_json, agent_data.get('active', 1), agent_data.get('live_chat_active', 1)))
    conn.commit()
    conn.close()

def set_agent_live_status(agent_id, is_active):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE agents SET live_chat_active=:1 WHERE agent_id=:2", (1 if is_active else 0, agent_id))
    conn.commit()
    conn.close()

def get_agent_stats():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        stats = {}
        c.execute("SELECT assigned_agent_id, COUNT(*) FROM tickets WHERE status NOT IN ('Closed') AND assigned_agent_id IS NOT NULL GROUP BY assigned_agent_id")
        for r in c.fetchall():
            aid, count = r
            if aid not in stats: stats[aid] = {'active': 0, 'resolved': 0}
            stats[aid]['active'] = count
        c.execute("SELECT assigned_agent_id, COUNT(*) FROM tickets WHERE status IN ('Closed') AND assigned_agent_id IS NOT NULL GROUP BY assigned_agent_id")
        for r in c.fetchall():
            aid, count = r
            if aid not in stats: stats[aid] = {'active': 0, 'resolved': 0}
            stats[aid]['resolved'] = count
        return stats
    finally:
        if conn: conn.close()


def add_comment(ticket_id, author, message):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO comments (ticket_id, author, message, created_at) VALUES (:1, :2, :3, SYSTIMESTAMP)", (ticket_id, author, message))
    conn.commit()
    conn.close()

def get_comments(ticket_id):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT author, message, created_at FROM comments WHERE ticket_id=:1 ORDER BY created_at ASC", (ticket_id,))
        rows = c.fetchall()
        comments = []
        for r in rows:
            comments.append({"author": r[0], "message": r[1], "created_at": r[2]})
        return comments
    finally:
        if conn: conn.close()



def add_chat_message(ticket_id, sender, message, attachment=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO ticket_chat (ticket_id, sender, message, attachment, timestamp) VALUES (:1, :2, :3, :4, SYSTIMESTAMP)", (ticket_id, sender, message, attachment))
    conn.commit()
    conn.close()

def get_chat_history(ticket_id):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT sender, message, timestamp, attachment FROM ticket_chat WHERE ticket_id=:1 ORDER BY timestamp ASC", (ticket_id,))
        rows = c.fetchall()
        history = []
        for r in rows:
            history.append({"sender": r[0], "author": r[0], "message": r[1], "timestamp": r[2], "attachment": r[3]})
        return history
    finally:
        if conn: conn.close()

def get_ticket_chat_history(ticket_id):
    # Backward compatibility wrapper
    return get_chat_history(ticket_id)


def get_admin_analytics():
    conn = get_connection()
    try:
        df_tickets = query_to_df("SELECT ticket_type FROM tickets", conn)
        type_counts = df_tickets['ticket_type'].value_counts().to_dict() if not df_tickets.empty and 'ticket_type' in df_tickets.columns else {}
    except:
        type_counts = {}
    c = conn.cursor()
    c.execute("SELECT sender, COUNT(*) FROM ticket_chat WHERE sender != 'user' GROUP BY sender")
    agent_activity = dict(c.fetchall())
    conn.close()
    return {"type_counts": type_counts, "agent_activity": agent_activity}

def get_technician_metrics(agent_id):
    conn = get_connection()
    try:
        df = query_to_df("SELECT * FROM tickets WHERE assigned_agent_id = :1", conn, params=(agent_id,))
    except: df = pd.DataFrame()
    
    if df.empty:
        conn.close()
        return {"status_counts": pd.Series(), "avg_tat": 0, "resolved_today": 0, "topic_counts": pd.Series(), "trend_data": pd.DataFrame()}

    status_counts = df['status'].value_counts()
    today = datetime.datetime.now().date()
    resolved_today = 0
    # Include both 'Closed' and legacy 'Resolved' for metrics
    resolved_df = df[df['status'].str.lower().isin(['closed', 'resolved', 'solved', 'completed'])].copy()
    if not resolved_df.empty:
        resolved_df['updated_at'] = pd.to_datetime(resolved_df['updated_at'], errors='coerce')
        resolved_today = len(resolved_df[resolved_df['updated_at'].dt.date == today])

    avg_tat = 0
    if not resolved_df.empty:
        resolved_df['created_at'] = pd.to_datetime(resolved_df['created_at'], errors='coerce')
        resolved_df['tat_hours'] = (resolved_df['updated_at'] - resolved_df['created_at']).dt.total_seconds() / 3600
        avg_tat = resolved_df['tat_hours'].mean()

    topic_counts = df['topic'].value_counts()
    trend_data = resolved_df.set_index('updated_at').resample('D').size().reset_index() if not resolved_df.empty else pd.DataFrame()
    if not trend_data.empty: trend_data.columns = ['Date', 'Resolved Count']
    
    conn.close()
    return {"status_counts": status_counts, "avg_tat": avg_tat, "resolved_today": resolved_today, "topic_counts": topic_counts, "trend_data": trend_data}

def get_ticket_by_id(ticket_id):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        query = """
            SELECT ticket_id, subject, description, topic, priority, status, 
                   instance, deployment_type, ticket_type, version, connected_systems,
                   customer_case_ref, hypercare, assigned_agent_id, created_at, 
                   updated_at, auto_tags, partner, email, user_id, attachment
            FROM tickets WHERE ticket_id = :1
        """
        c.execute(query, (ticket_id,))
        row = c.fetchone()
        ticket = None
        if row:
            ticket = {
                "ticket_id": row[0], "subject": row[1], "description": row[2], "topic": row[3],
                "priority": row[4], "status": row[5], "instance": row[6], "deployment_type": row[7],
                "ticket_type": row[8], "version": row[9], "connected_systems": row[10],
                "customer_case_ref": row[11], "hypercare": row[12], "assigned_agent_id": row[13],
                "created_at": row[14], "updated_at": row[15], "auto_tags": row[16],
                "partner": row[17], "email": row[18], "user_id": row[19], "attachment": row[20]
            }
        return ticket
    finally:
        if conn: conn.close()

def log_kb_view(article_id, title):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM kb_views WHERE article_id=:1", (article_id,))
    if c.fetchone():
        c.execute("UPDATE kb_views SET view_count = view_count + 1, last_viewed=SYSTIMESTAMP WHERE article_id=:1", (article_id,))
    else:
        c.execute("INSERT INTO kb_views (article_id, title, last_viewed) VALUES (:1, :2, SYSTIMESTAMP)", (article_id, title))
    conn.commit()
    conn.close()

def log_kb_search(query):
    if not query or not query.strip(): return
    conn = get_connection()
    c = conn.cursor()
    # Truncate to 2000 chars to avoid ORA-12899 (we just increased the limit)
    truncated_query = query.strip()[:2000]
    c.execute("INSERT INTO kb_searches (query, timestamp) VALUES (:1, SYSTIMESTAMP)", (truncated_query,))
    conn.commit()
    conn.close()

def get_kb_search_analytics():
    conn = get_connection()
    df = query_to_df("SELECT query, COUNT(*) as count FROM kb_searches GROUP BY query ORDER BY count DESC FETCH FIRST 10 ROWS ONLY", conn)
    conn.close()
    return df

def get_kb_analytics():
    conn = get_connection()
    try:
        # Most viewed
        df_most = query_to_df("SELECT title, view_count FROM kb_views WHERE article_id NOT LIKE '%.csv%' ORDER BY view_count DESC FETCH FIRST 10 ROWS ONLY", conn)
        # Least viewed
        df_least = query_to_df("SELECT title, view_count FROM kb_views WHERE article_id NOT LIKE '%.csv%' ORDER BY view_count ASC FETCH FIRST 10 ROWS ONLY", conn)
        conn.close()
        return {"most_viewed": df_most, "least_viewed": df_least}
    except Exception as e:
        print(f"Error checking KB analytics: {e}")
        return {"most_viewed": pd.DataFrame(), "least_viewed": pd.DataFrame()}


def get_technician_tickets(agent_id):
    """Retrieves all tickets assigned to a specific technician."""
    conn = get_connection()
    try:
        if not agent_id: return pd.DataFrame()
        query = """
            SELECT ticket_id, subject, description, topic, priority, status, 
                   instance, deployment_type, ticket_type, version, connected_systems,
                   customer_case_ref, hypercare, assigned_agent_id, created_at, 
                   updated_at, auto_tags, partner, email, user_id, attachment
            FROM tickets WHERE assigned_agent_id = :1
        """
        c = conn.cursor()
        c.execute(query, (agent_id,))
        rows = c.fetchall()
        
        data = []
        for row in rows:
            desc = row[2].read() if hasattr(row[2], 'read') else row[2]
            tags = row[16].read() if hasattr(row[16], 'read') else row[16]
            
            data.append({
                "ticket_id": row[0], "subject": row[1], "description": desc,
                "topic": row[3], "priority": row[4], "status": row[5],
                "instance": row[6], "deployment_type": row[7], "ticket_type": row[8],
                "version": row[9], "connected_systems": row[10],
                "customer_case_ref": row[11], "hypercare": row[12],
                "assigned_agent_id": row[13], "created_at": row[14],
                "updated_at": row[15], "auto_tags": tags,
                "partner": row[17], "email": row[18], "user_id": row[19],
                "attachment": row[20]
            })
            
        df = pd.DataFrame(data)
        
        if not df.empty:
            from sla_manager import get_deadline
            
            def calc_sla(row):
                try:
                    priority = row.get('priority', 'Medium')
                    created = row.get('created_at')
                    if not created: return 0
                    
                    deadline = get_deadline(created, priority)
                    if not deadline: return 0
                    
                    now = datetime.datetime.now()
                    updated = row.get('updated_at')
                    status = row.get('status')
                    
                    if status in ['Closed', 'Resolved'] and updated:
                        end_time = updated
                    else:
                        end_time = now
                    
                    if isinstance(end_time, pd.Timestamp): end_time = end_time.to_pydatetime()
                    
                    if deadline.tzinfo and not end_time.tzinfo:
                         end_time = end_time.replace(tzinfo=deadline.tzinfo)
                    elif not deadline.tzinfo and end_time.tzinfo:
                         deadline = deadline.replace(tzinfo=end_time.tzinfo)
                         
                    delta = deadline - end_time
                    return delta.total_seconds() / 3600
                except:
                    return 0

            df['sla_hours_remaining'] = df.apply(calc_sla, axis=1)
            
        return df

    except Exception as e:
        print(f"Error fetching tech tickets: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def get_technician_analytics_detailed(agent_id):
    """
    Returns detailed analytics for a technician dashboard.
    Includes: Performance Metrics, Trends, Distribution, Compliance.
    """
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM tickets WHERE assigned_agent_id = :1", (agent_id,))
        total = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM tickets WHERE assigned_agent_id = :1 AND status IN ('Closed', 'Resolved', 'Solved', 'completed')", (agent_id,))
        resolved = c.fetchone()[0]
        
        c.execute("SELECT priority, COUNT(*) FROM tickets WHERE assigned_agent_id = :1 GROUP BY priority", (agent_id,))
        prio_dist = {row[0]: row[1] for row in c.fetchall()}
        
        conn.close()
        
        df = get_technician_tickets(agent_id)
        
        due_date_counts = {'Overdue': 0, 'Today': 0, 'Tomorrow': 0, 'This Week': 0}
        sla_compliance = {'Compliant': 0, 'Breached': 0}
        productivity_trend = pd.DataFrame()
        mttr = 0
        
        if not df.empty:
            breached = len(df[df['sla_hours_remaining'] < 0])
            compliant = len(df[df['sla_hours_remaining'] >= 0])
            sla_compliance = {'Compliant': compliant, 'Breached': breached}
            
            now = datetime.datetime.now()
            today = now.date()
            tomorrow = today + datetime.timedelta(days=1)
            week_end = today + datetime.timedelta(days=7)
            
            open_df = df[~df['status'].str.lower().isin(['closed', 'resolved', 'solved', 'completed'])]
            for _, row in open_df.iterrows():
                rem = row.get('sla_hours_remaining', 0)
                if rem < 0:
                    due_date_counts['Overdue'] += 1
                else:
                    # Calculate deadline date from current time and hours remaining
                    deadline = now + datetime.timedelta(hours=rem)
                    d_date = deadline.date()
                    if d_date == today:
                        due_date_counts['Today'] += 1
                    elif d_date == tomorrow:
                        due_date_counts['Tomorrow'] += 1
                    elif d_date <= week_end:
                        due_date_counts['This Week'] += 1
            
            # Include both 'Closed' and legacy 'Resolved' for trend analysis
            resolved_df = df[df['status'].str.lower().isin(['closed', 'resolved', 'solved', 'completed'])].copy()
            if not resolved_df.empty:
                resolved_df['resolved_date'] = pd.to_datetime(resolved_df['updated_at']).dt.date
                productivity_trend = resolved_df.groupby('resolved_date').size().reset_index(name='Resolved Count')
                productivity_trend.columns = ['Date', 'Resolved Count']
                
                resolved_df['duration'] = (pd.to_datetime(resolved_df['updated_at']) - pd.to_datetime(resolved_df['created_at'])).dt.total_seconds() / 3600
                mttr = round(resolved_df['duration'].mean(), 1)
        
        metrics = {
            'total_handled': total,
            'resolved': resolved,
            'first_response_time_avg': 0.5, 
            'mttr': mttr
        }
        
        return {
            'performance_metrics': metrics,
            'productivity_trend': productivity_trend,
            'priority_distribution': prio_dist,
            'sla_compliance_breakdown': sla_compliance,
            'due_date_counts': due_date_counts
        }
        
    except Exception as e:
        print(f"Error in tech analytics: {e}")
        return {
            'performance_metrics': {}, 'productivity_trend': pd.DataFrame(),
            'priority_distribution': {}, 'sla_compliance_breakdown': {}
        }


def get_resolution_analytics():
    """Returns resolution statistics (AI vs Human)."""
    conn = get_connection()
    try:
        c = conn.cursor()
        # Human Resolved: Closed tickets with a real human agent assigned (not AI_ASSISTANT)
        c.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Closed', 'Resolved', 'Solved', 'completed') AND assigned_agent_id IS NOT NULL AND assigned_agent_id != 'AI_ASSISTANT'")
        human = c.fetchone()[0]
        
        # AI Resolved: Closed tickets with NO agent or assigned to AI_ASSISTANT
        c.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Closed', 'Resolved', 'Solved', 'completed') AND (assigned_agent_id IS NULL OR assigned_agent_id = 'AI_ASSISTANT')")
        ai = c.fetchone()[0]
        
        conn.close()
        return {'AI Resolved': ai, 'Human Resolved': human}
    except Exception as e:
        print(f"Error in resolution analytics: {e}")
        return {'AI Resolved': 0, 'Human Resolved': 0}

def get_tag_analytics():
    """Returns frequency of auto-tags."""
    conn = get_connection()
    try:
        df = query_to_df("SELECT auto_tags FROM tickets", conn)
        if df.empty: return pd.Series()
        
        all_tags = []
        for tags in df['auto_tags']:
             # Handle CLOB
             if hasattr(tags, 'read'): tags = tags.read()
             if not tags: continue
             
             # Parse
             try:
                 # If list string
                 if tags.strip().startswith('['):
                     t_list = ast.literal_eval(tags)
                     if isinstance(t_list, list):
                         all_tags.extend(t_list)
                 else:
                     # Comma separated?
                     all_tags.extend([t.strip() for t in tags.split(',') if t.strip()])
             except:
                 pass
                 
        return pd.Series(all_tags).value_counts()
    except Exception as e:
        print(f"Error in tag analytics: {e}")
        return pd.Series()
    finally:
        conn.close()


def search_kb_vectors(query_vector, n_results=3, source=None):
    """
    Performs a native Vector Search in Oracle ADW 23ai.
    Uses string conversion for the vector to avoid client-side version requirements (DPI-1050).
    'source' parameter allows filtering by specific knowledge sources (e.g. 'POC_HYBRID_DOCS').
    """
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Convert list/numpy array to a JSON string representation for TO_VECTOR
        if hasattr(query_vector, 'tolist'):
            v_list = query_vector.tolist()
        else:
            v_list = list(query_vector)
        vector_str = "[" + ",".join(map(str, v_list)) + "]"
        
        # Build SQL based on source filter
        if source:
            query = """
                SELECT CONTENT, SOURCE, TITLE, VECTOR_DISTANCE(EMBEDDING, TO_VECTOR(:1), COSINE) as distance
                FROM KB_VECTORS
                WHERE SOURCE = :2
                ORDER BY distance
                FETCH FIRST :3 ROWS ONLY
            """
            params = [vector_str, source, n_results]
        else:
            query = """
                SELECT CONTENT, SOURCE, TITLE, VECTOR_DISTANCE(EMBEDDING, TO_VECTOR(:1), COSINE) as distance
                FROM KB_VECTORS
                ORDER BY distance
                FETCH FIRST :2 ROWS ONLY
            """
            params = [vector_str, n_results]
        
        c.execute(query, params)
        
        results = []
        for row in c.fetchall():
            content = row[0].read() if hasattr(row[0], 'read') else row[0]
            results.append({
                "content": content,
                "source": row[1],
                "title": row[2],
                "distance": row[3]
            })
        return results
    except Exception as e:
        print(f"Error performing Vector Search in ADW: {e}")
        return []
    finally:
        if conn: conn.close()


def search_similar_resolved_tickets(query: str, limit: int = 3) -> list:
    """
    Searches closed/resolved tickets whose subject or description contains keywords
    from the query. Returns a list of dicts with ticket details for the chatbot context.
    """
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        # Split query into keywords (3+ chars) and build a LIKE filter
        keywords = [w.strip() for w in query.split() if len(w.strip()) >= 3]
        if not keywords:
            return []

        # Build OR conditions for keyword matching (limit to first 5 keywords)
        conditions = []
        params = []
        for kw in keywords[:5]:
            conditions.append("(LOWER(subject) LIKE :p OR LOWER(description) LIKE :p)")
            params.append(f"%{kw.lower()}%")
            params.append(f"%{kw.lower()}%")

        where_clause = " OR ".join(conditions)

        sql = f"""
            SELECT ticket_id, subject, description, status, priority, topic, updated_at
            FROM tickets
            WHERE status IN ('Closed', 'Resolved', 'Solved', 'completed')
              AND ({where_clause})
            ORDER BY updated_at DESC
            FETCH FIRST :limit ROWS ONLY
        """
        params.append(limit)

        c.execute(sql, params)
        rows = c.fetchall()

        results = []
        for row in rows:
            desc = row[2].read() if hasattr(row[2], 'read') else (row[2] or "")
            # Trim description for context
            desc_trimmed = str(desc)[:500] if desc else ""
            results.append({
                "ticket_id": row[0],
                "subject": row[1] or "",
                "description": desc_trimmed,
                "status": row[3] or "",
                "priority": row[4] or "",
                "topic": row[5] or "",
                "resolution": f"Resolved on {row[6]}" if row[6] else "No date logged"
            })
        return results





    except Exception as e:
        print(f"[DB] search_similar_resolved_tickets error: {e}")
        return []

def log_bot_health(health_data):
    """
    Saves a complete bot health & evaluation record to the database.
    health_data : dict containing all log fields captured during chatbot_engine.py execution.
    """
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        
        query = """
            INSERT INTO BOT_HEALTH_LOGS (
                TICKET_ID, ISSUE_ID, USER_ID, USER_QUERY, QUERY_INTENT, LATENCY_SEARCH, 
                LATENCY_LLM, KB_DISTANCE, KB_SOURCE_USED, KB_CONFIDENCE, 
                INPUT_TOKENS, OUTPUT_TOKENS, TOTAL_TOKENS, MODEL_USED,
                SCORE_CORRECTNESS, SCORE_FAITHFULNESS, SCORE_ACTIONABILITY, ERROR_MSG
            ) VALUES (
                :1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14, :15, :16, :17, :18
            )
        """
        
        # Clean query text for DB storage (truncate to avoid ORA errors)
        query_text = str(health_data.get('user_query', ''))[:4000]
        
        params = (
            health_data.get('ticket_id'), 
            health_data.get('issue_id'), # The conversation session ID
            health_data.get('user_id'),   # Track who is speaking
            query_text,
            health_data.get('intent', 'unknown'), 
            health_data.get('latency_search', 0.0),
            health_data.get('latency_llm', 0.0), 
            health_data.get('kb_distance'), 
            str(health_data.get('kb_source', ''))[:500], 
            health_data.get('kb_confidence', 'low'),
            health_data.get('input_tokens', 0), 
            health_data.get('output_tokens', 0),
            health_data.get('total_tokens', 0), 
            health_data.get('model', oci_config.CHAT_MODEL_ID),
            health_data.get('correctness', 0), 
            health_data.get('faithfulness', 0),
            health_data.get('actionability', 0), 
            str(health_data.get('error_msg', ''))[:4000]
        )
        
        c.execute(query, params)
        conn.commit()
    except Exception as e:
        print(f"[Health Log Error] Failed to insert log: {e}")
    finally:
        if conn: conn.close()


def report_system_error(service_name, error_msg):
    """
    Instantly marks a service as OFFLINE in the dashboard when a runtime error occurs.
    """
    conn = None
    try:
        conn = database.get_connection() # Use already initialized or get new
        c = conn.cursor()
        c.execute(
            "UPDATE SYSTEM_HEALTH SET STATUS = 'OFFLINE', ERROR_MSG = :1, LAST_CHECKED = SYSTIMESTAMP WHERE SERVICE_NAME = :2",
            (str(error_msg)[:4000], service_name)
        )
        conn.commit()
    except:
        pass
    finally:
        if conn: conn.close()


    
