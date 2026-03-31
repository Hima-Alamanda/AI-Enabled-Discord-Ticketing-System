import os
import sys
import requests
import json
import argparse
import re
from dotenv import load_dotenv


load_dotenv()

from database import get_connection
from oci_storage import upload_file
from sentence_transformers import SentenceTransformer

# Shared embedding model (loaded once)
_EMBED_MODEL = None

def get_embed_model():
    """Loads the SentenceTransformer model (shared with rag_manager)."""
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        print("Loading embedding model...")
        _EMBED_MODEL = SentenceTransformer("all-mpnet-base-v2")
    return _EMBED_MODEL

# --- Configuration ---
ZOHO_ORG_ID = os.getenv("ZOHO_ORG_ID")
ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
ZOHO_REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
DEPT_ID = "111007000000006907"

# API Endpoints
ACTIVE_URL = "https://desk.zoho.com/api/v1/tickets"
ARCHIVE_URL = "https://support.pcbapps.com/supportapi/zd/pcbapps/api/v1/tickets/archivedTickets"

# Domains to skip when finding inline images (logos, emojis, profile pics)
SKIP_IMAGE_DOMAINS = [
    "zohowebstatic.com", "zohostatic.com", "zohocdn.com",
    "google.com", "gstatic.com", "gravatar.com",
    "microsoft.com", "office.com", "w3.org"
]

def get_fresh_access_token():
    """Refreshes the Zoho OAuth token."""
    url = "https://accounts.zoho.com/oauth/v2/token"
    payload = {
        "refresh_token": ZOHO_REFRESH_TOKEN,
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print(f"FAILED to refresh token: {response.json()}")
        sys.exit(1)
    return response.json().get("access_token")

def is_user_screenshot(url):
    """Returns True only if the image URL is a real user screenshot from Zoho Desk."""
    if "desk.zoho.com" not in url:
        return False
    if any(domain in url for domain in SKIP_IMAGE_DOMAINS):
        return False
    return True

def fetch_conversations_and_inline_images(access_token, ticket_id):
    """Fetches full thread content per ticket by fetching each thread individually."""
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}", "orgId": ZOHO_ORG_ID}
    
    # Step 1: Get list of thread IDs
    threads_url = f"https://desk.zoho.com/api/v1/tickets/{ticket_id}/threads"
    threads_res = requests.get(threads_url, headers=headers)
    
    messages = []
    inline_image_urls = []
    
    if threads_res.status_code != 200:
        return "", []
    
    threads = threads_res.json().get("data", [])
    
    # Step 2: Fetch each thread individually to get full HTML content
    for thread in threads:
        thread_id = thread["id"]
        thread_url = f"https://desk.zoho.com/api/v1/tickets/{ticket_id}/threads/{thread_id}"
        tres = requests.get(thread_url, headers=headers)
        
        if tres.status_code == 200:
            tdata = tres.json()
            summary = tdata.get("summary", "")
            content = tdata.get("content", "")
            direction = tdata.get("direction", "in")
            created = tdata.get("createdTime", "")
            
            if summary:
                messages.append(f"[{direction.upper()} - {created}]: {summary}")
            
            # Extract inline images — Zoho stores them as RELATIVE paths with HTML-encoded & (&amp;)
            # Example: /api/v1/threads/{id}/inlineImages/{hash}?et=...&amp;ha=...&amp;f=4.png
            if content:
                # Capture full src value including query params (stop at quote only)
                rel_imgs = re.findall(r'src=["\'](/api/v1/threads/[^"\']+)["\']', content)
                # Deduplicate and decode HTML entities (&amp; -> &)
                seen = set()
                for rel_url in rel_imgs:
                    clean_url = rel_url.replace("&amp;", "&")
                    full_url = f"https://desk.zoho.com{clean_url}"
                    if full_url not in seen:
                        seen.add(full_url)
                        inline_image_urls.append(full_url)
                
    return "\n---\n".join(messages), inline_image_urls

def upload_inline_images(access_token, ticket_id, inline_image_urls):
    """Downloads inline images from Zoho-hosted URLs and uploads them to OCI."""
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}", "orgId": ZOHO_ORG_ID}
    oci_links = []
    
    for i, img_url in enumerate(inline_image_urls):
        try:
            # Zoho inline images require auth headers to download
            res = requests.get(img_url, headers=headers, timeout=15)
            if res.status_code == 200:
                ctype = res.headers.get("Content-Type", "image/png")
                ext = ctype.split("/")[-1].split(";")[0]
                filename = f"inline_{i+1}.{ext}"
                object_name = f"Zoho_images/{ticket_id}/{filename}"
                upload_file(res.content, object_name, ctype)
                oci_links.append(object_name)
        except Exception as e:
            print(f"      [Inline Image Error] {e}")
            
    return oci_links

def sync_attachments(access_token, ticket_id):
    """Downloads file attachments and uploads them to OCI Object Storage."""
    url = f"https://desk.zoho.com/api/v1/tickets/{ticket_id}/attachments"
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}", "orgId": ZOHO_ORG_ID}
    response = requests.get(url, headers=headers)
    
    oci_links = []
    filenames = []
    
    if response.status_code == 200:
        attachments = response.json().get("data", [])
        for att in attachments:
            name = att["name"]
            download_url = att["contentUrl"]
            file_res = requests.get(download_url, headers=headers)
            if file_res.status_code == 200:
                object_name = f"Zoho_images/{ticket_id}/{name}"
                try:
                    upload_file(file_res.content, object_name, file_res.headers.get("Content-Type"))
                    oci_links.append(object_name)
                    filenames.append(name)
                except Exception as e:
                    print(f"      [OCI Error] {e}")
                    
    return oci_links, json.dumps(filenames)

def save_to_adw(tickets, table_name, access_token):
    """Upserts tickets into the specified ADW table with full artifact extraction."""
    if not tickets:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    count = 0
    
    print(f"Syncing {len(tickets)} tickets into {table_name} with ATTACHMENTS...")
    
    for t in tickets:
        ticket_id = t["id"]
        subject = t["subject"]
        status = t["status"]
        priority = t.get("priority", "Medium")
        created_time_str = t["createdTime"]
        
        # 1. Fetch conversations & detect real inline screenshots
        messages, inline_images = fetch_conversations_and_inline_images(access_token, ticket_id)
        
        # 2. Upload inline screenshots to OCI
        inline_oci_links = upload_inline_images(access_token, ticket_id, inline_images)
        
        # 3. Fetch & upload direct file attachments to OCI
        attachment_oci_links, attachments_json = sync_attachments(access_token, ticket_id)
        
        # 4. Merge all OCI image paths into one list for IMAGE_URLS column
        all_image_urls = json.dumps(inline_oci_links + attachment_oci_links)
        
        # MERGE (Upsert) — prevents duplicates
        query = f"""
            MERGE INTO {table_name} z
            USING (SELECT :1 as tid FROM dual) s
            ON (z.TICKET_ID = s.tid)
            WHEN MATCHED THEN
                UPDATE SET 
                    SUBJECT = :2, 
                    MESSAGES = :3, 
                    IMAGE_URLS = :4, 
                    ATTACHMENTS = :5, 
                    STATUS = :6, 
                    PRIORITY = :7, 
                    CREATED_TIME = :8, 
                    CREATED_AT = SYSTIMESTAMP
            WHEN NOT MATCHED THEN
                INSERT (TICKET_ID, SUBJECT, MESSAGES, IMAGE_URLS, ATTACHMENTS, STATUS, PRIORITY, CREATED_TIME, CREATED_AT)
                VALUES (:9, :10, :11, :12, :13, :14, :15, :16, SYSTIMESTAMP)
        """
        params = (
            ticket_id, subject, messages, all_image_urls, attachments_json, status, priority, created_time_str,
            ticket_id, subject, messages, all_image_urls, attachments_json, status, priority, created_time_str
        )
        cursor.execute(query, params)
        count += 1
        if count % 10 == 0:
            print(f"    Processed {count}/{len(tickets)} tickets...")
            
    conn.commit()
    conn.close()
    return count

def fetch_tickets_paginated(access_token, mode="active"):
    """Fetches ticket list from Zoho with pagination."""
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}", "orgId": ZOHO_ORG_ID}
    url = ACTIVE_URL if mode == "active" else ARCHIVE_URL
    params = {"departmentId": DEPT_ID, "limit": 100, "from": 0}
    if mode == "archive":
        params["viewType"] = "2"
        params["from"] = "0"
        
    all_tickets = []
    print(f"Connecting to Zoho ({mode} mode)...")
    while True:
        response = requests.get(url, headers=headers, params=params)
        data = response.json().get("data", [])
        if not data:
            break
        all_tickets.extend(data)
        if mode == "archive":
            params["from"] = str(int(params["from"]) + len(data))
        else:
            params["from"] += len(data)
        if len(data) < 100:
            break
    return all_tickets

def ingest_tickets_to_kb_vectors(tickets, source_label):
    """
    Vectorizes Zoho ticket conversations and upserts them into KB_VECTORS.
    source_label = 'zoho_ticket' (active) or 'zoho_archive' (historical)
    """
    if not tickets:
        return 0

    model = get_embed_model()
    conn = get_connection()
    cursor = conn.cursor()
    ingested = 0

    for t in tickets:
        ticket_id = t["id"]
        subject = t["subject"]
        status = t.get("status", "")
        priority = t.get("priority", "")
        created = t.get("createdTime", "")

        # Fetch the full messages already stored in ADW (avoid re-calling Zoho API)
        try:
            cursor.execute(
                "SELECT MESSAGES FROM ZOHO_TICKETS WHERE TICKET_ID = :1"
                if source_label == "zoho_ticket"
                else "SELECT MESSAGES FROM ZOHO_ARCHIVE_TICKETS WHERE TICKET_ID = :1",
                [ticket_id]
            )
            row = cursor.fetchone()
            messages = row[0] if row and row[0] else ""
        except Exception:
            messages = ""

        # Skip empty tickets with no conversation
        if not messages.strip():
            continue

        # Build the KB content block — what the bot will read
        content = f"""# {subject}

Status: {status} | Priority: {priority} | Date: {created}
Ticket ID: {ticket_id}

## Conversation
{messages}"""

        title = f"{subject} ({ticket_id[-6:]})"

        # Generate embedding vector
        embedding = model.encode(content)
        vector_str = "[" + ",".join(map(str, embedding.tolist())) + "]"

        # Upsert into KB_VECTORS (delete old version first to prevent duplicates)
        cursor.execute(
            "DELETE FROM KB_VECTORS WHERE SOURCE = :1 AND TITLE = :2",
            [source_label, title]
        )
        cursor.execute(
            "INSERT INTO KB_VECTORS (EMBEDDING, TITLE, SOURCE, CHUNK_INDEX, CONTENT) "
            "VALUES (TO_VECTOR(:1), :2, :3, 0, :4)",
            [vector_str, title, source_label, content]
        )
        ingested += 1
        if ingested % 20 == 0:
            conn.commit()
            print(f"    Vectorized {ingested}/{len(tickets)} tickets...")

    conn.commit()
    conn.close()
    return ingested

def main():
    parser = argparse.ArgumentParser(description="Unified Zoho Desk to ADW Deep Sync")
    parser.add_argument("--archive", action="store_true", help="Sync ARCHIVED tickets instead of active")
    args = parser.parse_args()
    
    mode = "archive" if args.archive else "active"
    table_name = "ZOHO_ARCHIVE_TICKETS" if args.archive else "ZOHO_TICKETS"
    
    print(f"SYNC STARTED: {mode.upper()}")
    token = get_fresh_access_token()
    tickets = fetch_tickets_paginated(token, mode=mode)
    print(f"Retrieved {len(tickets)} records from Zoho. Syncing with full artifact extraction...")
    saved_count = save_to_adw(tickets, table_name, token)
    source_label = "zoho_archive" if args.archive else "zoho_ticket"
    print(f"Successfully Synced {saved_count} records to {table_name}.")
    
    # Step 2: Push tickets into KB_VECTORS so the bot can search them
    print(f"\nIngesting {saved_count} tickets into KB_VECTORS for bot search...")
    ingested = ingest_tickets_to_kb_vectors(tickets, source_label)
    print(f"Successfully ingested {ingested} tickets into KB_VECTORS.")
    print("Sync Completed")

if __name__ == "__main__":
    main()
