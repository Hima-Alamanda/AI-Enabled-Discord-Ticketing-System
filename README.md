# AI-Enabled Intelligent Ticketing & Support System

A state-of-the-art, multi-agent support ecosystem powered by **Oracle Cloud Infrastructure (OCI)** and **RAG (Retrieval-Augmented Generation)**. This system automates the entire support lifecycle—from initial user query to intelligent resolution and automated Knowledge Base (KB) generation.

---

## System Architecture & AI Intelligence

The system operates on a modular **"Brain & Body"** paradigm, utilizing a fleet of specialized AI agents built with OCI Generative AI.

### Specialized AI Agent Roles (The Brains)
Each interaction is handled by a team of agents working in sequence:
*   **Intent Agent**: The "Receptionist." Classifies user messages (Greeting, Question, Status Check).
*   **Knowledge Agent**: The "Researcher." Uses **RAG** (Retrieval-Augmented Generation) to find fixes in the technical documentation.
*   **Clarification Engine**: The "Diagnostician." If a query is vague, it asks targeted follow-up questions until it has enough data.
*   **Issue Understanding Agent**: The "Analyst." Extracts structured metadata (Category, Urgency, System Type) from human conversations.
*   **Automation Agent**: The "Operator." Handles automated workflows like ticket creation and database updates.
*   **Continuity Agent**: The "Memory." Ensures the AI remembers previous context from the chat history.
*   **Handoff Agent**: The "Summarizer." When human intervention is needed, it drafts a professional technical brief for the technician.

### Technology Stack
*   **Intelligence**: OCI Generative AI (Gemini 2.5 Pro / Grok 4.20 Reasoning / Gemini 2.5 Flash)
*   **Database**: Oracle Autonomous Data Warehouse (ADW)
*   **Vector Engine**: Oracle AI Vector Search (Database 23ai)
*   **Delivery**: Discord-enabled intelligent bot workspace.

---

## Manager's Quick-Start Dashboard

To make management and testing simple, the system includes a **professional Makefile interface** that handles all complex operations with single commands.

| Command | Action |
| :--- | :--- |
| `make help` | Show this implementation dashboard |
| `make setup` | Install all Python dependencies & AI model assets |
| `make db-init` | Initialize Oracle DB pool and register support agents |
| `make rag-sync` | Synchronize Knowledge Base articles into the Vector Store |
| **`make eval-push`** | **Run Benchmark Evaluations and push Latest Reports to GitHub** |
| `make bot-run` | Launch the live Discord AI-Assistant |
| `make bot-status`| Check if the AI bot is currently running |

---

## Prerequisites & Environment Setup

Since this is an enterprise-grade system, it requires specific local environment configurations for OCI and Oracle connectivity.

### 1. Oracle Cloud Connectivity
*   **OCI SDK**: Installed automatically via `make setup`.
*   **`.oci/` Config**: Ensure you have an OCI configuration file located at `~/.oci/config` with your user credentials, fingerprint, and private key.
*   **Compartment ID**: You need the OCID of the compartment where the Generative AI service is enabled.

### 2. Autonomous Database (ADW) Connectivity
The system uses **Oracle Instant Client** for high-performance ADW connections.
1.  **Instant Client**: Download and unzip the [Oracle Instant Client](https://www.oracle.com/database/technologies/instant-client/downloads.html) for your OS.
2.  **Wallet Folder**: Place your **DB Wallet** (e.g., `Wallet_EDI/`) in the root directory.
3.  **Environment Variables**: Add the following to your `.env` file:
    ```bash
    DB_USER=ADMIN
    DB_PASSWORD=YourPassword...
    DB_DSN=your_db_high
    COMPARTMENT_ID=ocid1.compartment...
    DISCORD_TOKEN=your_bot_token...
    ```

---

## Performance Benchmarking & Evaluations

We have implemented a rigorous **Automated Evaluation Framework** (located in `/evaluations`) that keeps the project data-driven.

*   **Models Compared**: Google Gemini 2.5 Pro vs. xAI Grok 4.20 Reasoning.
*   **Metrics**: Correctness, Faithfulness, Actionability, BLEU Score, ROUGE-L, and Latency.
*   **Clean History Policy**: The system is configured to only track the **LATEST** performance reports in GitHub (via `report_latest.md`), keeping the codebase clean while maintaining a full historical archive locally in the `results/` folder.

---

## Workflow

1.  **Clone** the repository.
2.  **Setup Environment**: Place your `oci_config`, `Wallet_EDI`, and `.env` in the root.
3.  **Bootstrap**: Run `make setup` and `make db-init`.
4.  **Analyze**: Run `make eval-push` to see how our latest AI models are performing against the benchmark dataset.
5.  **Test**: Start the bot with `make bot-run`.

---
