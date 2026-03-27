# AI Evaluation & Benchmarking Framework

This framework provides a rigorous, data-driven approach to comparing different LLM models (e.g., **Google Gemini 2.5 Pro** vs. **xAI Grok 4.20 Reasoning**) for the AI-Enabled Ticketing System.

## Core Components

1.  **`benchmark_dataset.json`**: A high-quality dataset containing diverse enterprise support scenarios, including ground truth solutions, expected actions, and attachment information.
2.  **`model_comparison_v2.py`**: The primary evaluation engine. It uses an **LLM-as-a-Judge** (Gemini 2.5 Flash) to score responses based on Correctness, Faithfulness, Actionability, and Format Adherence.
3.  **`quantitative_eval.py`**: Calculates mathematical alignment scores including **BLEU** (n-gram overlap) and **ROUGE-L** (structural similarity) against ground truth answers.
4.  **`results/`**: Stores all evaluation artifacts.
    *   **Timestamped Files**: Full history of every run (e.g., `report_20260327_1311.md`). These stay local only.
    *   **Latest Files**: The most recent run results (e.g., `report_latest.md`). These are automatically pushed to GitHub.

## How to Run Evaluations

The system is integrated into the root `Makefile` for ease of use.

### 1. Run and Review (Local Only)
Generates full reports and data locally for your review.
```bash
make eval-run
```

### 2. Run and Push to GitHub (Automated)
Runs the full evaluation suite and automatically pushes the **latest** reports and CSV data to the main repository. This keeps the GitHub history clean (tracking only one "current" report) while preserving your local history.
```bash
make eval-push
```

## Evaluation Metrics

The framework assesses models across two distinct dimensions:

### A. Qualitative (LLM-as-a-Judge)
Scores from **0 to 5** assigned by an objective auditor:
*   **Correctness**: Technical accuracy against the "Golden Answer".
*   **Faithfulness**: Grounding in KB context (hallucination check).
*   **Actionability**: Practicality of the resolution steps provided.
*   **Format Adherence**: Compliance with the required four-header structure.
*   **Escalation Logic**: Correct decision-making (Solve vs. Create Ticket).

### B. Quantitative (Mathematical)
*   **BLEU Score**: Measures word-level overlap with ground truth.
*   **ROUGE-L Score**: Measures sentence-level structural similarity.
*   **Latency (s)**: Average response time per model.
*   **Token Usage**: Detailed tracking of Input, Output, and Total tokens via OCI Generative AI.

## Result Management
*   **Git Policy**: Only files ending in `_latest` in the `results/` directory are tracked in GitHub. 
*   **Local History**: All timestamped files are automatically ignored by Git to prevent repository bloat, allowing you to maintain a comprehensive local archive of all your experiments.
