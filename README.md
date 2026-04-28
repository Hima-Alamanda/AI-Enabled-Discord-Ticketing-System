# AI-Enabled Intelligent Ticketing & Support System

A state-of-the-art, multi-agent support ecosystem powered by **Oracle Cloud Infrastructure (OCI)** and **RAG (Retrieval-Augmented Generation)**. This system automates the entire support lifecycle—from initial user query to intelligent resolution and automated Knowledge Base (KB) generation.

The platform operates across **two interfaces**:
- **Discord Bot** — the end-user-facing AI assistant where employees submit queries, raise tickets, and receive AI-driven resolutions directly in Discord channels.
- **Admin / Technician Management UI** — a web-based management panel (served via `controller.py`) for administrators and technicians to manage tickets, view SLA dashboards, agent workloads, and KB analytics.

---

## System Architecture & AI Intelligence

![System Architecture](architecture.png)

The system operates on a modular **"Brain & Body"** paradigm, utilizing a fleet of specialized AI agents built with OCI Generative AI.

### Specialized AI Agent Roles (The Brains)
Each interaction is handled by a team of agents working in sequence:
*   **Intent Agent**: The "Receptionist." Classifies user messages (Greeting, Question, Status Check).
*   **Knowledge Agent**: The "Researcher." Uses **RAG** (Retrieval-Augmented Generation) to find fixes in the technical documentation.
*   **Clarification Engine**: The "Diagnostician." If a query is vague, it asks targeted follow-up questions until it has enough data.
*   **Issue Understanding Agent**: The "Analyst." Extracts structured metadata (Category, Urgency, System Type) from human conversations.
*   **Automation Agent**: The "Operator." Handles automated workflows like ticket creation and database updates.
*   **Continuity Agent**: The "Memory." Ensures the AI remembers previous context from the chat history.
*   **Visual Insight Agent**: The "Artist." Generates professional, dark-themed charts (Bar, Pie, Line) to visualize support trends and ticket distribution directly in Discord.
*   **Health Monitor Agent**: The "Auditor." Real-time watchdog that verifies connectivity to Oracle ADW, OCI GenAI, Vector Search, and the Discord bot process.
*   **Handoff Agent**: The "Summarizer." When human intervention is needed, it drafts a professional technical brief for the technician.
*   **Recursive Learning Engine**: The "Self-Corrector." Implements a dual-pass reasoning loop (Initial ➔ Critic ➔ Final) that uses AI-as-a-Judge to self-evaluate and improve responses before delivery.

### Intelligent Agent Assignment
When a ticket is created, the system automatically assigns the best available support agent using a **3-tier workload-balanced algorithm**:
1. **Tier 1**: Match agents by **Topic AND Instance** (e.g., Finance + PROD).
2. **Tier 2 Fallback**: Match agents by **Topic only**.
3. **Tier 3 Fallback**: Assign to **any available agent**.

Within each tier, agents are sorted by their current open-ticket workload — the agent with the **fewest active tickets** is assigned first, ensuring an even distribution of work across the team.

### AI Reliability — Primary → Fallback Model Cascade
All AI calls go through a **two-model cascade** for maximum uptime:
1. **PRIMARY model** (`CHAT_MODEL_ID`) is attempted first.
2. If it fails for any reason (rate limit, safety filter, timeout), the system **automatically retries** with the **FALLBACK model** (`FALLBACK_MODEL_ID`) — no manual intervention required.
3. If both models fail, a graceful error message is returned to the user.

Token usage (input, output, total) is tracked per call and accumulated globally for cost analysis in evaluation reports.

### Technology Stack
*   **Intelligence**: OCI Generative AI (Gemini 2.5 Pro / Grok 4.20 Reasoning / Gemini 2.5 Flash) with automatic primary → fallback cascade
*   **Visuals**: Matplotlib & Seaborn (Premium Dark-Themed Analytics)
*   **Data Lake**: Oracle Autonomous Data Warehouse (ADW) & Oracle Object Storage (for ticket attachments)
*   **Vector Engine**: Oracle AI Vector Search (Database 23ai)
*   **Document Processing**: pdfplumber, pytesseract (OCR), Pillow, python-docx — extracts text from PDF, DOCX, image, and log file attachments for AI analysis
*   **Integration**: Zoho Desk (Active & Archived Ticket Synchronization into KB Vector Store)
*   **Delivery**: Discord-enabled intelligent bot workspace + Admin Management UI

---

## Project Structure — Module Reference

```
├── discord_bot.py          # Main Discord bot — entry point for all user interactions
├── controller.py           # Web controller — Admin & Technician management UI backend
├── orchestrator.py         # Routes every message to the correct agent pipeline
├── chatbot_engine.py       # Core response engine with Recursive Learning loop
├── oci_genai.py            # OCI GenAI client with primary/fallback model cascade + token tracking
├── database.py             # Oracle ADW connection pool + all CRUD operations
├── rag_manager.py          # Loads KB articles into Oracle AI Vector Store
├── auto_tagging.py         # AI-powered ticket field extraction and semantic tagging
├── agent_manager.py        # Agent seeding + workload-balanced ticket assignment algorithm
├── sla_manager.py          # SLA deadline calculation and breach/status detection
├── health_manager.py       # 4-service diagnostics (ADW, GenAI, Vector Search, Discord)
├── oci_storage.py          # OCI Object Storage — upload, PAR URL generation & caching
├── oci_config.py           # OCI SDK configuration (model IDs, endpoints, compartment)
├── zoho_sync.py            # Zoho Desk ↔ ADW ticket synchronization (active & archived)
├── visualizer.py           # Dark-themed chart generation (Bar, Donut, Line) for Discord
├── document_processor.py   # Extracts text from PDF, DOCX, image, and log attachments
├── escalation_manager.py   # Human escalation workflow management
├── exchange_tokens.py      # Zoho OAuth token refresh management
├── utils.py                # Shared constants (TICKET_TOPICS, INSTANCES, helpers)
├── tools.py                # Discord interaction tools and slash command handlers
├── run_discord.sh          # Shell script to activate venv and launch the Discord bot
├── agents/                 # Specialized AI agent modules
│   ├── intent_agent.py         # Classifies user intent and urgency
│   ├── knowledge_agent.py      # RAG-based knowledge retrieval
│   ├── clarification_engine.py # Follow-up questioning until issue is fully defined
│   ├── issue_understanding_agent.py  # Extracts structured ticket metadata
│   ├── automation_agent.py     # Ticket creation and DB update workflows
│   ├── continuity_agent.py     # Conversation memory and issue tracking
│   ├── handoff_agent.py        # Technical brief generation for human escalations
│   └── retrieval_manager.py    # Vector similarity search over KB content
├── evaluations/            # Benchmark evaluation scripts and reports
│   ├── model_comparison_v2.py      # AI model head-to-head performance comparison
│   ├── quantitative_eval.py        # BLEU, ROUGE-L, BERTScore quantitative metrics
│   ├── prompt_evaluation_suite.py  # 4 prompt strategy benchmarks
│   ├── recursive_evaluator.py      # Initial vs Final self-corrected response quality
│   ├── generate_excel_report.py    # Executive Excel report generator
│   ├── zoho_eval.py                # RAG vector search accuracy evaluation (ROUGE-L)
│   ├── benchmark_dataset.json      # Benchmark Q&A dataset for model comparison
│   ├── zoho_benchmark_dataset.json # Zoho ticket-based benchmark dataset
│   └── results/                    # Generated reports (Excel, CSV, Markdown)
└── static/charts/          # Auto-generated chart images served to Discord
```

---

## Manager's Quick-Start Dashboard

To make management and testing simple, the system includes a **professional Makefile interface** that handles all complex operations with single commands.

| Command | Action |
| :--- | :--- |
| `make help` | Show this implementation dashboard |
| `make venv` | Create the Python virtual environment (.venv) |
| `make setup` | Install all Python dependencies & AI model assets |
| `make health` | **Run System Diagnostics (Oracle ADW, OCI GenAI, Vector Search, Discord)** |
| `make db-init` | Initialize Oracle DB pool and seed 18 support agents |
| `make rag-sync` | Synchronize Knowledge Base articles into the Vector Store |
| `make zoho-sync` | **Sync Active Tickets from Zoho Desk into KB Vector Store** |
| `make zoho-archive` | **Sync Archived Tickets from Zoho Desk into KB Vector Store** |
| `make zoho-eval` | **Run Vector Search Accuracy Evaluation (ROUGE-L / Keyword Overlap)** |
| `make eval-run` | Run AI Performance & Mathematical Reports (model comparison + quantitative) |
| `make eval-suite` | Run Comprehensive Prompt Engineering Benchmarking (4 Strategies) |
| `make eval-report` | Generate Executive Excel Performance Report from latest results |
| `make recursive-eval` | **Run Self-Correction Benchmarks (Initial vs Final Response Quality)** |
| **`make eval-push`** | **Run All Benchmarks and push Latest Reports to GitHub** |
| `make bot-run` | Launch the live Discord AI-Assistant |
| `make bot-status` | Check if the AI bot is currently running |
| `make bot-log` | Monitor real-time bot application logs |
| `make bot-stop` | Stop the running Discord bot process |
| `make git-status` | Show modified files and development progress |
| `make git-log` | Show the 10 most recent implementation commits |
| `make clean` | Wipe temporary cache items (pycache, logs, charts) |

---

## Prerequisites & Environment Setup

Since this is an enterprise-grade system, it requires specific local environment configurations for OCI and Oracle connectivity.

### 0. Python Version & Virtual Environment

This project requires **Python 3.10 or higher** (required for `oracledb` Thick Mode and type hints used throughout the codebase).

```bash
# Clone the repository
git clone <repo-url>
cd AI-Enabled-Ticketing-System

# Create the virtual environment
make venv
# OR manually:
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# Install all dependencies
make setup
```

### 1. Oracle Cloud Connectivity
*   **OCI SDK**: Installed automatically via `make setup`.
*   **`.oci/` Config**: Ensure you have an OCI configuration file located at `~/.oci/config` with your user credentials, fingerprint, and private key.
*   **Compartment ID**: You need the OCID of the compartment where the Generative AI service is enabled.

### 2. Autonomous Database (ADW) Connectivity
The system uses **Oracle Instant Client** for high-performance ADW connections in Thick Mode (required for wallet-based SSL authentication on macOS).
1.  **Instant Client**: Download and unzip the [Oracle Instant Client](https://www.oracle.com/database/technologies/instant-client/downloads.html) for your OS into the `instantclient/` folder in the project root.
2.  **Wallet Folder**: Place your **DB Wallet** (unzipped) into `Wallet_EDI/` in the project root.
3.  **Environment Variables**: Copy `.env.example` to `.env` and fill in your details:
    ```bash
    cp .env.example .env
    ```

### 3. Environment Variables Reference

Copy `.env.example` to `.env` and fill in every value before running the system.

```bash
# ── Oracle Database ────────────────────────────────────────────────
DB_USER=<your_adw_username>            # Your ADW database username
DB_PASSWORD=<your_adw_password>        # Your ADW database password
DB_DSN=<your_service_name>             # Service name from tnsnames.ora inside Wallet_EDI/
DB_WALLET_PASSWORD=<your_wallet_pwd>   # Password used to authenticate the ADW wallet

# ── OCI Configuration ──────────────────────────────────────────────
COMPARTMENT_ID=<your_compartment_ocid> # OCI compartment OCID where GenAI is enabled
OCI_REGION=<your_oci_region>           # Your OCI region (e.g. us-ashburn-1, uk-london-1)
OCI_NAMESPACE=<your_namespace>         # Your OCI Object Storage namespace
OCI_BUCKET_NAME=<your_bucket_name>     # Your OCI bucket name for ticket attachment storage

# ── Discord Bot ────────────────────────────────────────────────────
DISCORD_TOKEN=<your_discord_bot_token> # Your bot token from Discord Developer Portal

# ── Zoho Integration (Optional — required for zoho-sync) ───────────
ZOHO_ORG_ID=<your_zoho_org_id>
ZOHO_CLIENT_ID=<your_zoho_client_id>
ZOHO_CLIENT_SECRET=<your_zoho_client_secret>
ZOHO_REFRESH_TOKEN=<your_zoho_refresh_token>
```

| Variable | Required | Purpose |
| :--- | :--- | :--- |
| `DB_USER` |  Yes | ADW login username |
| `DB_PASSWORD` |  Yes | ADW login password |
| `DB_DSN` |  Yes | Service name from `Wallet_EDI/tnsnames.ora` |
| `DB_WALLET_PASSWORD` |  Yes | Wallet authentication password |
| `COMPARTMENT_ID` |  Yes | OCI compartment for GenAI API calls |
| `OCI_REGION` |  Yes | OCI region for Object Storage URL construction |
| `OCI_NAMESPACE` |  Yes | OCI Object Storage namespace |
| `OCI_BUCKET_NAME` |  Yes | Bucket where ticket attachments are stored |
| `DISCORD_TOKEN` |  Yes | Discord bot token |
| `ZOHO_*` |  Optional | Required only for `make zoho-sync` / `make zoho-archive` |

---

## Database Schema — Oracle ADW Tables

The system uses the following tables in Oracle Autonomous Data Warehouse. These must exist before running `make db-init`.

| Table | Purpose |
| :--- | :--- |
| `tickets` | Core support ticket records (22+ fields including topic, priority, SLA, agent, attachments, tags) |
| `agents` | Support agent profiles — name, email, role, topic expertise, instance coverage, workload |
| `comments` | Technician-written comments on individual tickets |
| `ticket_chat` | Full conversation log between the AI bot and users (per ticket) |
| `kb_content` | Knowledge Base articles used as the RAG source (title, body, category, vector embeddings) |
| `kb_views` | Tracks which KB articles are viewed most / least (analytics) |
| `kb_searches` | Logs every search query submitted against the KB |
| `SYSTEM_HEALTH` | Real-time status rows for: `ORACLE_ADW`, `OCI_GENAI`, `DISCORD_BOT`, `VECTOR_SEARCH` |
| `BOT_HEALTH_LOGS` | Per-interaction logs (`issue_id`) linked back to their resolved `ticket_id` |

---

## Zoho Desk Data Pipeline — How Zoho Data Flows into ADW

This system uses **Zoho Desk as the primary source of real-world support ticket data**. Tickets are **extracted (pulled) from Zoho Desk via the Zoho REST API** and ingested into Oracle ADW for AI training, RAG vectorization, and evaluation benchmarking.

### Data Flow

```
Zoho Desk (Live Tickets)
        │
        │  Zoho REST API (OAuth 2.0 — Client Credentials)
        │  zoho_sync.py / exchange_tokens.py
        ▼
  Pulled & Transformed
  (ticket subject, description, status, tags, category, timestamps)
        │
        ├──► Oracle ADW — kb_content table
        │    (stored as KB articles for RAG knowledge base)
        │
        └──► Oracle AI Vector Search
             (embedded using sentence-transformers → 768-dim vectors)
             (used for semantic similarity search during AI resolution)
```

### Two Sync Modes

| Command | What It Pulls | Use Case |
| :--- | :--- | :--- |
| `make zoho-sync` | **Active (open) tickets** from Zoho Desk | Keep the KB fresh with current real-world issues |
| `make zoho-archive` | **Archived (closed/historical) tickets** from Zoho Desk | Bulk-ingest historical data for richer RAG context and evaluation |

### Why Zoho Data is Used
- **Real-World Training Signal** — The AI's Knowledge Agent is grounded in actual resolved support cases, not synthetic data.
- **RAG Accuracy** — Pulled Zoho tickets are vectorized and stored in Oracle AI Vector Search, so when a new user submits a query, the AI finds semantically similar real past tickets and their resolutions.
- **Evaluation Benchmark** — `evaluations/zoho_benchmark_dataset.json` is derived from Zoho data and is used by `make zoho-eval` to measure how accurately the RAG system retrieves relevant past tickets (ROUGE-L / Keyword Overlap scoring).

---

## SLA Policy

The system enforces automated SLA deadlines based on ticket priority. All deadlines are calculated from the ticket's creation timestamp.

| Priority | SLA Deadline | Status Labels |
| :--- | :--- | :--- |
|  Critical | **1 hour** | On Track → At Risk → Breached |
|  High | **4 hours** | On Track → At Risk → Breached |
|  Medium | **24 hours** | On Track → At Risk → Breached |
|  Low | **48 hours** | On Track → At Risk → Breached |

**Status Definitions:**
- **On Track** — More than 4 hours remaining before deadline.
- **At Risk** — Less than 4 hours remaining (shown in yellow).
- **Breached** — Deadline has passed for an open ticket (shown in red).
- **Met** — Ticket was closed before the deadline.
- **Missed** — Ticket was closed after the deadline.

---

## Ticket Attachment Handling

When a user attaches a file to a Discord ticket, the system:

1. **Extracts content** — `document_processor.py` reads the file and extracts text using:
   - `pdfplumber` for PDF files
   - `python-docx` for DOCX/Word files
   - `pytesseract` (OCR) for images (PNG, JPG)
   - Plain text reader for `.txt` and `.log` files
2. **Uploads to OCI Object Storage** — The raw file is stored in the OCI bucket under `tickets/{ticket_id}/{filename}`.
3. **Generates a secure download URL** — A **Pre-Authenticated Request (PAR)** URL is created (valid for 24 hours) for secure access without requiring OCI credentials. PAR URLs are cached in memory to avoid redundant API calls.
4. **AI Analysis** — The extracted text is injected into the ticket context so the AI can analyze error messages, logs, and screenshots during support resolution.

---

## Performance Benchmarking & Evaluations

We have implemented a rigorous **Automated Evaluation Framework** (located in `/evaluations`) that keeps the project data-driven.

*   **Models Compared**: Google Gemini 2.5 Pro vs. xAI Grok 4.20 Reasoning.
*   **Metrics**: Correctness, Faithfulness, Actionability, BLEU Score, ROUGE-L, BERTScore, and Latency.
*   **Benchmark Datasets**:
    - `evaluations/benchmark_dataset.json` — General Q&A dataset for model comparison.
    - `evaluations/zoho_benchmark_dataset.json` — Real Zoho ticket-based dataset for RAG evaluation.
*   **4 Prompt Strategies** tested by `make eval-suite` (via `prompt_evaluation_suite.py`):
    1. Zero-Shot
    2. Few-Shot
    3. Chain-of-Thought
    4. Structured Instruction
*   **Executive Reporting**: The system generates a multi-sheet **EXECUTIVE_PERFORMANCE_REPORT_LATEST.xlsx** automatically, featuring heatmapped quality scores, token cost analysis, and model recommendations.
*   **Recursive Learning Audit**: Use `make recursive-eval` to generate the `recursive_learning_report.csv`. This report provides a detailed breakdown of quality improvements (Correctness, Faithfulness, Actionability) between the AI's first draft and its final self-corrected response.
*   **Token Cost Tracking**: Every OCI GenAI call tracks input, output, and total tokens globally. These are aggregated in the evaluation reports for cost analysis and model ROI comparison.
*   **Clean History Policy**: The system is configured to track only the **LATEST** performance reports in GitHub (via `PROMPT_REPORT.md`, `recursive_learning_report.csv`, and the Excel file), keeping the codebase clean while maintaining a full historical archive locally in the `results/` folder.

---

## AI Visual Analytics & Insights

The system features a **Premium Visual Engine** (via `visualizer.py`) that transforms raw support data into executive-ready charts directly within Discord:

*   **Dark-Theme Presentation**: All charts are optimized for Discord and professional dashboards using a deep-dark `#121212` background.
*   **Dynamic Charting**:
    *   **Bar Charts**: For comparing support metrics and agent performance.
    *   **Donut (Pie) Charts**: For visualizing ticket category distribution.
    *   **Activity Trends (Line)**: For tracking activity spikes and SLA adherence over time.
*   **Zero-Overhead Storage**: Charts are generated on-the-fly and stored in the `static/charts/` directory for immediate retrieval.

---

## Workflow

1.  **Clone** the repository and create the virtual environment (`make venv`).
2.  **Setup Environment**: Configure your `.env`, place `Wallet_EDI/` and `instantclient/` in the project root, and ensure `~/.oci/config` is configured.
3.  **Install Dependencies**: Run `make setup` to install all Python packages and download NLTK assets.
4.  **Bootstrap**: Run `make db-init` to initialize the Oracle connection pool and seed 18 support agents (2 admin + 16 domain specialists across 8 topics).
5.  **Verify State**: Run **`make health`** to confirm connectivity across all 4 services: Oracle ADW, OCI GenAI, Oracle Vector Search, and the Discord bot process.
6.  **Ingest Content**: Run **`make zoho-sync`** to pull active Zoho Desk tickets into the KB Vector Store. Run **`make zoho-archive`** to also ingest archived/historical tickets.
7.  **Analyze & Benchmark**: Run **`make eval-push`** to execute all prompt strategy audits and generate the latest **EXECUTIVE_PERFORMANCE_REPORT_LATEST.xlsx**, then push to GitHub automatically.
8.  **Live Deployment**: Launch the Discord Assistant with `make bot-run`. Monitor logs with `make bot-log`. Check status with `make bot-status`. Stop with `make bot-stop`.

---
