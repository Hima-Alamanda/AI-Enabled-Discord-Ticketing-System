# AI-Enabled Intelligent Ticketing & Support System

A state-of-the-art, multi-agent support ecosystem powered by **Oracle Cloud Infrastructure (OCI)** and **Advanced RAG (Retrieval-Augmented Generation)**. This system automates the entire support lifecycle—from initial user query to intelligent resolution and automated Knowledge Base (KB) generation.

---

## Project Overview

This project was developed to revolutionize IT support by moving from reactive ticketing to proactive AI assistance. By combining **Natural Language Understanding (NLU)** with **High-Precision RAG**, the system provides instant technical solutions while seamlessly managing human agent handoffs and ticket lifecycles.

### Primary Objectives:
*   **Instant Resolution**: Deflect up to 70% of support tickets using intelligent documentation search.
*   **Precision Intelligence**: Use specialized agents to understand context, clarify issues, and predict ticket priority.
*   **Seamless Lifecycle**: Automate ticket creation, SLA monitoring, and "Ticket-to-KB" promotion.
*   **Enterprise Security**: Built on Oracle's robust cloud infrastructure for data privacy and high-performance vector operations.

---

## System Architecture

The system operates on a modular **"Brain & Body"** paradigm, utilizing a fleet of specialized AI agents built with OCI Generative AI.

### 1. Multi-Agent Orchestration
The heart of the system is the **Orchestrator**, which manages the following agents:
*   **Intent Agent**: Analyzes incoming messages to determine if the user is seeking help, checking status, or just chatting.
*   **Knowledge Agent (RAG Hub)**: Performs semantic search across the Knowledge Base using **Oracle ADW Vector Search**.
*   **Clarification Engine**: Engages the user with dynamic follow-up questions to gather missing technical details (e.g., Error IDs, System Environment).
*   **Issue Understanding Agent**: Extracts key entities and technical parameters from messy user descriptions.
*   **Continuity Agent**: Maintains conversation context over long interactions, ensuring the AI never loses the thread.
*   **Handoff Agent**: Coordinates the transition to a human technician, providing a concise AI-generated summary of the problem.

### 2. Retrievel-Augmented Generation (RAG) Pipeline
1.  **Ingestion**: Documentation and past tickets are processed and converted into 768-dimensional embeddings using `all-mpnet-base-v2`.
2.  **Storage**: Vectors are stored in **Oracle Autonomous Database** using native AI Vector Search capabilities.
3.  **Retrieval**: High-speed similarity search retrieves the most relevant technical articles based on the user's current issue.

> **[DIAGRAM PLACEHOLDER: SYSTEM WORKFLOW]**
> *Recommendation: Place a high-level flowchart here showing the path from User Message -> Orchestrator -> RAG Agent -> Clarification -> Final Response.*

---

## Key Features

### Smart Ticketing & Auto-Tagging
*   **Automated Categorization**: Uses LLM-based categorization to predict the `Topic` and `Severity` of a ticket instantly.
*   **SLA Intelligence**: Real-time SLA tracking with custom countdowns and escalation alerts based on priority (P1-P4).
*   **Agent Assignment**: Smart routing of tickets to the best-suited human technician based on the issue topic.

### Self-Evolving Knowledge Base
*   **Ticket-to-KB Promotion**: Once a human technician resolves a unique issue, the system uses AI to summarize the resolution and "promote" it to a permanent KB article.
*   **Vector Sync**: New KB articles are instantly vectorized and added to the RAG pipeline for future queries, creating a self-learning loop.

###  Dynamic User Experience
*   **Multi-Platform Flexibility**: Built with a decoupled core, allowing deployment on **Discord**, **Microsoft Teams**, and **Web Portals**.
*   **Context-Aware UI**: Uses dynamic Discord buttons and menus tailored to the specific technical issue being discussed.

---

## Technology Stack

| Component | Technology |
| :--- | :--- |
| **Intelligence** | OCI Generative AI (Llama 3 / Command R / Gemini) |
| **Database** | Oracle Autonomous Data Warehouse (ADW) |
| **Vector Search** | Oracle AI Vector Search (Database 23ai) |
| **Embedding Model** | `all-mpnet-base-v2` (Sentence Transformers) |
| **Framework** | Python 3.10+, Discord.py |
| **Orchestration** | Custom Multi-Agent "Brain" Logic |

---

## Project Structure

*   `orchestrator.py`: The central hub for message routing and agent management.
*   `agents/`: Contains the logic for all specialized AI agents (Knowledge, Intent, Handoff, etc.).
*   `rag_manager.py`: Handles vectorization, document ingestion, and vector store management.
*   `database.py`: Robust interface for Oracle ADW, ticket persistence, and KB management.
*   `controller.py`: Core business logic for ticket creation, status updates, and KB promotion.
*   `sla_manager.py`: Monitors and calculates real-time SLA deadlines.
*   `auto_tagging.py`: AI-driven classification and metadata prediction for support issues.

---

## Getting Started

### Prerequisites
*   OCI Tenancy with Generative AI and ADW instance.
*   Oracle Instant Client & Wallet for DB connection.
*   Python 3.10+ environment.

### Installation
1.  Clone the repository:
    ```bash
    git clone https://github.com/your-repo/ai-ticketing-system.git
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Configure environmental variables in `.env`:
    ```env
    OCI_CONFIG_FILE=~/.oci/config
    DB_USER=admin
    DB_PASSWORD=your_password
    DISCORD_TOKEN=your_token
    ```

---

## Roadmap
*   [ ] **Microsoft Teams Integration**: Full migration to enterprise Teams environment using Azure Bot Service.
*   [ ] **Advanced Analytics Dashboard**: Real-time visualization of support trends, AI deflection rates, and SLA health.



