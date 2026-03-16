import oci_genai
import database
import json
from datetime import date
from sentence_transformers import SentenceTransformer

# Using all-mpnet-base-v2 (768 dimensions) to match the Oracle ADW table schema
EMBED_MODEL_NAME = "all-mpnet-base-v2"
_EMBED_MODEL = None

def get_embed_model():
    """Lazily loads the embedding model."""
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        print(f"Initializing RAG Hub with local embedding model: {EMBED_MODEL_NAME}...")
        _EMBED_MODEL = SentenceTransformer(EMBED_MODEL_NAME)
    return _EMBED_MODEL

def summarize_ticket(chat_history):
    """
    Summarizes a ticket's chat history into a concise resolution article.
    Used by controller.py for KB promotion.
    """
    if not chat_history:
        return "No resolution details found in chat."
    
    # Format chat history for the prompt
    history_str = ""
    for msg in chat_history:
        sender = msg.get('sender', 'unknown')
        text = msg.get('message', '')
        history_str += f"{sender.upper()}: {text}\n"

    system_prompt = "You are an Expert IT Support Analyst. Summarize the following chat history into a clear, concise resolution article for a Knowledge Base. Focus on the root cause and the final fix. Keep it under 150 words."
    
    try:
        summary = oci_genai.get_chat_response(
            prompt=f"Summarize this support conversation:\n\n{history_str}",
            system_prompt=system_prompt,
            temperature=0.3
        )
        return summary
    except Exception as e:
        print(f"Error summarizing ticket: {e}")
        return "Failed to generate AI summary."

def get_ai_response(user_query, tools=None, user_context=None, history=None, stream=False):
    """
    Core RAG Function (OCI GenAI + ADW Native Vector Search).
    """
    
    database.log_kb_search(user_query)

    query_vector = get_embed_model().encode(user_query)

    search_results = database.search_kb_vectors(query_vector, n_results=5)
    
    docs = [r['content'] for r in search_results]
    sources = list(set([r['source'] for r in search_results]))
    
    # Log KB Views for analytics
    for res in search_results:
        database.log_kb_view(res['source'], res['title'])
    
    # Context Text for Prompt
    context_text = "\n\n".join(docs) if docs else "No specific technical procedures found."
    
    # Calculate Confidence (Based on Cosine distance)
    # Cosine distance: 0.0 is perfect. For all-mpnet-base-v2, 0.4-0.6 is good, > 0.7 is questionable.
    confidence = "high"
    if not docs:
        confidence = "low"
    elif search_results and search_results[0]['distance'] > 0.7:
        confidence = "low"

    user_name = user_context.get('name', 'Customer') if user_context else "Customer"
    user_info_str = f"CURRENT USER CONTEXT:\n{json.dumps(user_context, indent=2)}" if user_context else ""
    
    HIGH_PROMPT = f"""You are a Senior IT Support Technician for "PCB Apps", an IT solutions provider.
You specialized in ITSM (IT Service Management). You do NOT deal with circuit board design or manufacturing.
A support ticket has ALREADY been created. DO NOT offer to create a ticket.

CONFIDENCE_MODE: HIGH
RULES:
- A verified Knowledge Base (KB) match exists in the context below.
- You MUST provide both a Description and a Solution section.
- If a specific technical fix exists in the context (e.g., "Restart X", "Change setting Y"), list it as steps.
- CRITICAL: If you find NO specific technical fix in the context, you MUST ignore the HIGH_PROMPT format and instead use the **LOW_PROMPT Status** format: "I am escalating this ticket to a human technician."
- DO NOT ask the user for more information or pose any questions.
- Output MUST follow the format below EXACTLY.

FORMAT:
Hi {user_name},

**Description:**
Provide a short, factual sentence summary of the issue.

**Solution:**
1. [Actionable technical step]
2. [Actionable technical step]
"""

    LOW_PROMPT = f"""You are a Senior IT Support Technician for "PCB Apps", an IT solutions provider.
You specialized in ITSM (IT Service Management). You do NOT deal with circuit board design or manufacturing.
A support ticket has ALREADY been created. DO NOT offer to create a ticket.

CONFIDENCE_MODE: LOW
RULES:
- This scenario requires specialized analysis or senior technician intervention.
- You MUST escalate this ticket.
- Use the phrase "human technician" in your status.
- DO NOT ask any questions or request more information from the user.
- DO NOT invent a fix or guess what might work.
- Output MUST follow the format below EXACTLY.

FORMAT:
Hi {user_name},

**Description:**
Provide a short, factual sentence summary of the issue.

**Status:**
I am escalating this ticket for senior technician review. This specific scenario requires specialized analysis to resolve.
"""

    system_prompt = HIGH_PROMPT if confidence == "high" else LOW_PROMPT

    # Combining instructions, context, and query for the final call
    final_prompt = f"""{user_info_str}

KNOWLEDGE BASE CONTEXT:
{context_text}

USER TICKET/QUERY:
{user_query}

IMPORTANT: You MUST follow the EXACT format provided in the system instructions.
"""

    full_response = oci_genai.get_chat_response(
        prompt=final_prompt, 
        system_prompt=system_prompt,
        temperature=0.2,
        max_tokens=2000
    )

    # Clean the response
    full_response = full_response.strip()
    
    # Pre-cleaning: Remove common AI repetition of the greeting/name
    expected_greeting = f"Hi {user_name},"
    lines = full_response.split('\n')
    
    # If the first line is the greeting, check if the second line is a repeat or just the name
    if len(lines) > 1 and lines[0].strip() == expected_greeting:
        # Check if second line is just the last name or a repeat
        second_line = lines[1].strip().rstrip(',')
        if second_line and second_line in user_name:
            # Remove the redundant second line
            lines.pop(1)
            full_response = '\n'.join(lines).strip()

    # Re-verify start
    if not full_response.startswith(expected_greeting):
        if expected_greeting in full_response:
            idx = full_response.find(expected_greeting)
            full_response = full_response[idx:].strip()
        else:
            full_response = f"{expected_greeting}\n\n{full_response}"

    return {
        "content": full_response,
        "sources": sources,
        "confidence": confidence,
        "is_stream": False
    }


def reset_database():
    """Wipe the KB_VECTORS table in ADW."""
    print("Clearing KB_VECTORS in ADW...")
    conn = database.get_connection()
    try:
        c = conn.cursor()
        c.execute("TRUNCATE TABLE KB_VECTORS")
        conn.commit()
    except Exception as e:
        print(f"Error resetting KB_VECTORS: {e}")
    finally:
        conn.close()

def delete_document(doc_id):
    """Delete a specific document vector from ADW."""
    conn = database.get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM KB_VECTORS WHERE ID = :1", [doc_id])
        conn.commit()
    except Exception as e:
        print(f"Error deleting vector {doc_id}: {e}")
    finally:
        conn.close()

def ingest_individual_article(article_data):
    """
    Ingests a single article into the KB_VECTORS store.
    This is much faster than load_documents_to_db as it avoids scanning all files.
    """
    if not article_data:
        return
    
    conn = database.get_connection()
    try:
        title = article_data.get('title', 'Unknown Title')
        body = article_data.get('body', '')
        category = article_data.get('category', 'General')
        
        # Prepare final content for vectorization. 
        # If the body already starts with a header (like promoted tickets do), use it directly.
        if body.strip().startswith("#"):
            content = body.strip()
        else:
            content = f"# {title}\n\nCategory: {category}\n\n{body}"
        
        # Generate the vector locally
        print(f"Generating vector for new article: {title}")
        embedding = get_embed_model().encode(content)
        vector_str = "[" + ",".join(map(str, embedding.tolist())) + "]"
        
        c = conn.cursor()
        source = article_data.get('source_id') or "database"
        
        c.execute("DELETE FROM KB_VECTORS WHERE SOURCE = :1 AND TITLE = :2", [source, title])
        
        sql = "INSERT INTO KB_VECTORS (EMBEDDING, TITLE, SOURCE, CHUNK_INDEX, CONTENT) VALUES (TO_VECTOR(:1), :2, :3, 0, :4)"
        c.execute(sql, [vector_str, title, source, content])
        
        conn.commit()
        print(f"Successfully ingested individual article: {title}")
    except Exception as e:
        print(f"Error in incremental ingestion for {article_data.get('title')}: {e}")
        raise
    finally:
        conn.close()



def load_documents_to_db():
    """
    Ingests all articles from ADW into KB_VECTORS.
    Local file scanning has been removed as the KB is now centralized in ADW.
    """
    print("Loading documents from ADW into Vector Store...")
    conn = database.get_connection()
    
    try:
        # Process Database Articles
        articles = database.get_all_kb_articles()
        print(f"Syncing {len(articles)} articles from database...")
        
        for art in articles:
            doc_id = f"db_art_{art['id']}"
            if art['body'].strip().startswith("#"):
                content = art['body'].strip()
            else:
                content = f"# {art['title']}\n\nCategory: {art['category']}\n\n{art['body']}"
            
            # Encode
            embedding = get_embed_model().encode(content)
            # Convert to string for TO_VECTOR to avoid DPI-1050
            vector_str = "[" + ",".join(map(str, embedding.tolist())) + "]"
            
            c = conn.cursor()
            # Delete old version of this database article to avoid duplicates
            # Use source='database' or specific filenames for migrated records
            source = art.get('source_id') or "database"
            c.execute("DELETE FROM KB_VECTORS WHERE SOURCE = :1 AND TITLE = :2", [source, art['title']])
            
            # Move LOB CONTENT to end of INSERT to avoid ORA-24816
            sql = "INSERT INTO KB_VECTORS (EMBEDDING, TITLE, SOURCE, CHUNK_INDEX, CONTENT) VALUES (TO_VECTOR(:1), :2, :3, 0, :4)"
            c.execute(sql, [vector_str, art['title'], source, content])
            conn.commit()

            
        print(f"Success: Indented {len(articles)} documents from cloud storage.")

    except Exception as e:
        print(f"Error during bulk database ingestion: {e}")
    finally:
        conn.close()
    
    print("KB Ingestion Complete.")

