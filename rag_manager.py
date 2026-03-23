import oci_genai
import database
import json
from datetime import date
from sentence_transformers import SentenceTransformer

# Using all-mpnet-base-v2 (768 dimensions) to match the Oracle ADW table schema
EMBED_MODEL_NAME = "all-mpnet-base-v2"
_EMBED_MODEL = None

def get_embed_model():
    """loads the embedding model."""
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

