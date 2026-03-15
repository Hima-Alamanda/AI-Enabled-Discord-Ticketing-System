
import streamlit as st
import os
import shutil
import pandas as pd
import rag_manager
import database
import time

KB_DIR = "knowledge_base"
ARTICLES_DIR = os.path.join(KB_DIR, "articles")
DATA_DIR = os.path.join(KB_DIR, "data")

def render_kb_manager():
    st.markdown("All data is securely stored in the database.")

    # tabs
    tab1, tab2, tab3 = st.tabs(["Knowledge Assets", "Add New Article", "Upload Files"])

    with tab1:
        # Fetch all knowledge from ADW
        articles = database.get_all_kb_articles()
        
        if articles:
            view_option = st.radio("Select View Mode:", 
                                  ["Show All", "Master Documentation", "FAQs", "Resolved Cases"], 
                                  key="kb_filter_radio_unique_v1",
                                  horizontal=True)

            st.markdown("---")

            master_docs = [a for a in articles if a.get('source_id') == 'Admin']
            data_files = [a for a in articles if a.get('source_id') and '.csv' in a.get('source_id').lower()]
            resolved_cases = [a for a in articles if a not in master_docs and a not in data_files]

            if view_option in ["Show All", "Master Documentation"]:
                st.subheader("Master Documentation")
                if master_docs:
                    for art in master_docs:
                        with st.expander(f"{art['title']} (Admin)"):
                            # Format timestamp to remove milliseconds
                            ts = art.get('updated_at')
                            ts_str = str(ts)[:19] if ts else "N/A"
                            st.markdown(f"**Last Updated:** {ts_str}")
                            st.markdown(art['body'])
                            c1, c2 = st.columns(2)
                            if c1.button("Edit", key=f"edit_master_{art['id']}"):
                                st.session_state['edit_kb_article'] = art
                                st.rerun()
                            if c2.button("Delete", key=f"del_master_{art['id']}"):
                                database.delete_kb_article(art['id'])
                                rag_manager.delete_document(f"db_art_{art['id']}")
                                st.success(f"Deleted: {art['title']}")
                                st.rerun()
                else:
                    st.caption("No master documents found.")
                
                if view_option == "Show All": st.markdown("---")

            if view_option in ["Show All", "Data & FAQs"]:
                st.subheader("Data & FAQs (CSV)")
                if data_files:
                    for art in data_files:
                        with st.expander(f"{art['title']} ({art['source_id']})"):
                            st.markdown(art['body'])
                            if st.button("Delete", key=f"del_data_{art['id']}"):
                                database.delete_kb_article(art['id'])
                                st.rerun()
                else:
                    st.caption("No CSV data found.")
                
                if view_option == "Show All": st.markdown("---")

            if view_option in ["Show All", "Resolved Cases"]:
                st.subheader("Resolved Cases (From Tickets)")
                if resolved_cases:
                    for art in resolved_cases:
                        with st.expander(f"{art['title']}"):
                            st.markdown(f"**Verified By:** {art.get('source_id', 'Technician')}")
                            st.markdown(art['body'])
                            if st.button("Delete", key=f"del_case_{art['id']}"):
                                database.delete_kb_article(art['id'])
                                st.rerun()
                else:
                    st.caption("No resolved tickets promoted yet.")

            st.markdown("---")
            st.subheader("Maintenance")
            st.info("If the AI is out of sync, you can force a full rebuild of the vector index.")
            if st.button("Force Rebuild AI Index", key="force_rebuild_kb"):
                with st.spinner("Cleaning and re-indexing all knowledge..."):
                    rag_manager.reset_database()
                    rag_manager.load_documents_to_db()
                st.success("AI Memory Rebuilt Successfully!")
        else:
            st.info("No articles found in the database. Add one to get started!")



    with tab2:
        st.subheader("Add or Edit Article")
        
        # Check if we are editing
        edit_data = st.session_state.get('edit_kb_article', {})
        
        with st.form("kb_article_form", clear_on_submit=True):
            new_title = st.text_input("Title", value=edit_data.get('title', ''), key="kb_title_input")
            new_category = st.selectbox("Category", ["General", "Finance", "HR", "IT Support", "Technical", "SOP"], 
                                       index=0 if not edit_data else ["General", "Finance", "HR", "IT Support", "Technical", "SOP"].index(edit_data.get('category', 'General')),
                                       key="kb_category_input")
            new_body = st.text_area("Content (Markdown supported)", value=edit_data.get('body', ''), height=300, key="kb_body_input")
            
            submit_label = "Update Article" if edit_data else "Save to Knowledge Base"
            if st.form_submit_button(submit_label):
                if new_title and new_body:
                    article = {
                        "id": edit_data.get('id'),
                        "title": new_title,
                        "body": new_body,
                        "category": new_category,
                        "source_id": edit_data.get('source_id') or "Admin"
                    }
                    database.save_kb_article(article)

                    
                    if 'edit_kb_article' in st.session_state:
                         del st.session_state['edit_kb_article']
                    
                    with st.spinner("Ingesting into AI memory..."):
                        rag_manager.ingest_individual_article(article)
                    
                    st.success("Article saved and AI updated instantly!")
                    st.rerun()


                else:
                    st.error("Title and Content are required.")
        
        if edit_data and st.button("Cancel Edit"):
            del st.session_state['edit_kb_article']
            st.rerun()

    with tab3:
        st.subheader("Upload Documents")
        st.info("Uploaded articles will be automatically imported into the database.")
        
        doc_type = st.radio("Document Type", ["Article (Markdown/Text)", "Data (CSV)"], horizontal=True)
        uploaded_file = st.file_uploader("Choose a file", type=['md', 'txt', 'csv'])
        
        if uploaded_file:
            if st.button("Import to Database"):
                content = uploaded_file.read().decode("utf-8")
                
                if "Article" in doc_type:
                    # Save to Database
                    article = {
                        "title": uploaded_file.name,
                        "body": content,
                        "category": "Imported",
                        "source_id": "Admin"
                    }
                    database.save_kb_article(article)

                    st.success(f"Imported {uploaded_file.name} to database articles.")
                    
                    with st.spinner("Ingesting into AI memory..."):
                        rag_manager.ingest_individual_article(article)
                else:
                    # For CSV, we still keep the file for row-by-row processing in rag_manager
                    # but we could also migrate this later. 
                    os.makedirs(DATA_DIR, exist_ok=True)
                    with open(os.path.join(DATA_DIR, uploaded_file.name), "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success(f"Saved {uploaded_file.name} to {DATA_DIR}")

                    with st.spinner("Updating AI memory..."):
                        rag_manager.load_documents_to_db()
                
                st.success("Database and AI Updated!")

                time.sleep(1)
                st.rerun()
