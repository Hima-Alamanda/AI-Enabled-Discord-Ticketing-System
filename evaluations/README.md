# AI Evaluation Framework (Enterprise Edition)

This framework provides a rigorous, data-driven pipeline to measure and compare the performance of the AI-Enabled Ticketing System. It uses real **Zoho Desk** support data to simulate production scenarios.

---

## 1. The Diagnostic Benchmark (8 Zoho Cases)
Our evaluation uses a diverse 8-case benchmark derived from real PCB Apps support history. The dataset is split into two distinct testing categories:

| Case ID | Type | Retrieval Source | Goal |
|:---|:---|:---|:---|
| **ZT-001 - ZT-004** | **Sanitized SOPs** | Manually Verified Knowledge Base | Measures accuracy when high-quality documentation is available. |
| **ZT-005 - ZT-008** | **Raw Ticket Vectors** | Unstructured Archive History | Measures the bot's "deduction" skills using raw previous chat history. |

---

## 2. Advanced Metric System (Likert 1-5 & BERTScore)
We have moved beyond simple keyword matching to a sophisticated "LLM-as-a-Judge" and semantic similarity system.

### **Quality Metrics (Scale: 1-5)**
Scored by an automated AI Auditor (Gemini Flash) using a multi-dimensional rubric:
- **Correctness (1-5):** Technical accuracy relative to the Golden Answer.
- **Faithfulness (1-5):** Grounding in the Knowledge Base (Anti-Hallucination).
- **Actionability (1-5):** Clarity of the troubleshooting steps.
- **Empathy & Tone (1-5):** Professionalism and helpdesk rapport.
- **Ambiguity Handling (1-5):** Ability to clarify vague queries.

### **Mathematical & Semantic Metrics**
- **BERTScore (0-1):** Our strongest metric. Uses embeddings to measure **semantic meaning** similarity. Even if words differ, if the intent is identical, the score is high.
- **BLEU / ROUGE (0-1):** Statistical text overlap metrics for structural comparison.
- **Latency (s):** Operational speed (Target: < 15 seconds).

---

## 3. Key Tools

| Script | Purpose |
|:---|:---|
| `prompt_evaluation_suite.py` | Runs all 32 test combinations (4 prompts x 2 models x 8 cases). |
| `model_comparison_v2.py` | Developer tool for rapid 1-on-1 model comparisons. |
| `quantitative_eval.py` | Batch calculation tool for BLEU/ROUGE/BERTScore. |
| `zoho_eval.py` | Tests the RAG retrieval engine (Librarian Test) without GenAI. |

---

## 5. Summary of Findings (Latest V7 Run)
*   **Winner for Faithfulness:** Grok 4.20 Reasoning (Prompt B).
*   **Winner for Speed:** Grok 4.20 Reasoning (Prompt A/C).
*   **Winner for Diagnostic Accuracy:** Gemini 2.5 Pro (Prompt D).

**Detailed findings can be found in `evaluations/results/PROMPT_REPORT.md`.**
