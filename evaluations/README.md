# AI Evaluation Framework — PCB Apps Support Bot

This folder contains the complete evaluation pipeline to measure and compare the performance of the AI support bot using **real Zoho Desk ticket data**.

---

## Folder Structure

```
evaluations/
├── benchmark_dataset.json         # Generic IT benchmark (7 test cases)
├── zoho_benchmark_dataset.json    # Real Zoho ticket queries (7 test cases)
├── zoho_eval.py                   # RAG retrieval test (no GenAI)
├── model_comparison_v2.py         # Full Gemini vs Grok comparison (GenAI judge)
├── quantitative_eval.py           # BLEU & ROUGE-L math scores
├── zoho_eval_results.json         # Output from zoho_eval.py
└── results/
    ├── comparison_latest.csv      # Model comparison raw data
    ├── report_latest.md           # LLM judge report (Gemini vs Grok)
    ├── quantitative_latest.csv    # BLEU/ROUGE raw data
    └── math_report_latest.md      # BLEU/ROUGE summary report
```

---

## The Three Evaluations — What Each Does

| Script | Uses GenAI? | What It Tests |
|---|---|---|
| `zoho_eval.py` | No — local model only | Does the **search engine** find the right ticket? |
| `model_comparison_v2.py` | Yes — Gemini + Grok + Flash judge | Does the **AI give a good answer** using the retrieved ticket? |
| `quantitative_eval.py` | No — pure math | Do the AI's **words** match the expected answer (BLEU/ROUGE)? |

### Think of It Like a Librarian + Professor

```
zoho_eval.py        = LIBRARIAN TEST
                      "Did the librarian find the right book on the shelf?"
                      (No reading — just finding the right ticket in KB_VECTORS)

model_comparison_v2 = PROFESSOR TEST
                      "Did the AI read the book and give a correct,
                       well-explained answer to the student?"
                      (Gemini Flash judges the answer quality 0–5)

quantitative_eval   = WORD MATCHING TEST
                      "Do the AI's words match the textbook answer word-for-word?"
                      (Math only — doesn't care if the answer is logically right)
```

> **Most important:** `model_comparison_v2.py` — it tests the real bot response quality.

---

## How to Run

### Step 1 — RAG Retrieval Test (Fast, no API cost)
```bash
python3 evaluations/zoho_eval.py
```
Tests whether KB_VECTORS finds the right Zoho ticket for each query.
Output: `evaluations/zoho_eval_results.json`

### Step 2 — Full Model Comparison (Gemini vs Grok, uses API)
```bash
# Run on Zoho ticket data
python3 evaluations/model_comparison_v2.py --dataset zoho

# Run on original generic IT benchmark
python3 evaluations/model_comparison_v2.py --dataset generic
```
Calls both models on 7 real queries, uses Gemini Flash as an AI judge.
Output: `evaluations/results/comparison_latest.csv` + `report_latest.md`

### Step 3 — BLEU & ROUGE Math Scores (run AFTER Step 2)
```bash
python3 evaluations/quantitative_eval.py --dataset zoho
```
Reads the Step 2 CSV and computes BLEU-4 and ROUGE-L scores.
Output: `evaluations/results/quantitative_latest.csv` + `math_report_latest.md`

---

## Part 1 — `zoho_eval.py` Explained

### How It Works (Step by Step)

```
1. USER QUERY  (e.g. "I have a batch error during end of month reporting")
           ↓
2. SentenceTransformer (all-mpnet-base-v2) converts query → 768 numbers (vector)
           ↓
3. Oracle KB_VECTORS searched — finds 3 closest stored ticket vectors
   (Pure cosine distance math — no AI model involved)
           ↓
4. Returns the closest matching ticket content from past Zoho tickets
           ↓
5. Calculates two scores:
   - Keyword Overlap: How many query words appear in the retrieved ticket?
   - ROUGE-L: How similar is the retrieved text to the expected resolution?
           ↓
6. Saves results to zoho_eval_results.json
```

### Results Summary (5 test cases on Zoho data)

| Test Case | Expected Ticket | Found? | Distance | Keyword Overlap | ROUGE-L |
|---|---|---|---|---|---|
| ZT-001 — Batch error | Error message end of month | Missed (FAQ found instead) | 0.38 | 20% | 0.11 |
| ZT-002 — Zoho access | zoho tickets | Perfect | 0.11 | 66.7% | 0.24 |
| ZT-003 — HMO eligibility | Retirees HMO file | Correct | 0.30 | 70% | 0.22 |
| ZT-004 — Address book | Address book UDC | Correct | 0.29 | 70% | 0.09 |
| ZT-005 — Daiwa close | Daiwa Year-End Close | Perfect | 0.28 | 66.7% | 0.19 |

**Overall RAG Accuracy: 4/5 (80%)**

| Overall Metric | Score | What It Means |
|---|---|---|
| Avg Keyword Overlap | 58.7% | Bot finds broadly relevant content |
| Avg ROUGE-L | 0.17 | Moderate text similarity to resolution |
| Avg Vector Distance | 0.27 | Good semantic similarity (lower = better) |
| Avg Response Time | 0.27s | Very fast — sub-second retrieval |

> **Note on ZT-001 miss:** The JE batch error query matched a pre-existing FAQ ("Batch job R09801 failed in JDE") slightly more than the actual Zoho ticket. The real Zoho ticket was the 2nd result (distance 0.39 vs FAQ 0.38) — a very close margin. The answer from the FAQ is still relevant.

---

## Part 2 — Model Comparison Results (Gemini vs Grok)

### LLM Judge Scores (0–5 per metric, 0–40 total per test case)

Test cases were real Zoho ticket queries. Gemini Flash scored each response as an independent judge.

| Case | Gemini 2.5 Pro | Grok 4.20 Reasoning | Winner |
|---|---|---|---|
| ZT-001 — Batch error | 3/40 Asked for clarification | 33/40 Gave correct steps | Grok |
| ZT-002 — Zoho access | 32/40 | 29/40  | Gemini |
| ZT-003 — HMO eligibility | 31/40 | 21/40 Hallucinated system name | Gemini |
| ZT-004 — Address book | 17/40 Said "by design" (wrong) | 16/40 Gave wrong workaround | Tie |
| ZT-005 — Daiwa close | 31/40  | 18/40 Hallucinated all 5 steps | Gemini |
| ZT-006 — Remove from file | N/A | 30/40  | — |
| ZT-007 — Vague "broken" | 40/40 Asked for details | 12/40 Jumped to generic steps |  Gemini |

### Average Quality Scores (0–5 scale)

| Metric | Gemini 2.5 Pro | Grok 4.20 Reasoning |
|---|---|---|
| Correctness | **3.00** | 2.29 |
| Faithfulness | **2.83** | 2.00 |
| Actionability | 2.67 | **3.71** |
| Format Adherence | **0.83** | 0.14 |
| Ambiguity Handling | 4.17 | **4.43** |
| Empathy & Tone | **4.50** | 4.43 |
| Escalation Logic | **3.50** | 2.86 |

### Performance & Cost

| Model | Avg Latency | Avg Total Tokens |
|---|---|---|
| Gemini 2.5 Pro | 26.4s | 5,951 |
| Grok 4.20 Reasoning | **15.3s** | 6,935 |

---

## Part 3 — BLEU & ROUGE Scores

### What These Metrics Mean

- **BLEU (0–1):** Measures exact n-gram phrase overlap between bot response and expected answer. Higher = uses same phrases as ground truth.
- **ROUGE-L (0–1):** Measures longest common sequence of words. Higher = covers the same key points.

> **Important:** Both metrics score low for support bots (~0.02 BLEU, ~0.15 ROUGE-L). This is **completely normal**. Support bots give long, detailed explanations while ground truth answers are short summaries. The LLM judge scores in `report_latest.md` are far more meaningful.

### Results

| Model | BLEU | ROUGE-L | Speed |
|---|---|---|---|
| Gemini 2.5 Pro | 0.017 | **0.158** | 26.4s |
| Grok 4.20 Reasoning | **0.022** | 0.155 | **15.3s** |

**Verdict on math scores: Roughly equal. Grok is slightly faster.**

---

## Final Verdict — Which Model Is Better?

| Criteria | Better Model | Reason |
|---|---|---|
| Overall quality & accuracy | **Gemini 2.5 Pro** | Higher correctness, faithfulness, escalation scores |
| Handling vague queries | **Gemini** | Scored 40/40 — correctly asked for details |
| Avoiding hallucinations | **Gemini** | Grok invented steps for Daiwa close & eligibility |
| Speed | **Grok** | 40% faster (15s vs 26s) |
| Step-by-step actions | **Grok** | Scored higher on actionability (3.71 vs 2.67) |

### Recommendation
**Use Gemini 2.5 Pro for production.** It is more accurate, doesn't hallucinate when context is limited, and correctly escalates or asks for clarification when needed. Grok is faster but risks giving confident-sounding but incorrect answers when the knowledge base lacks detail.

---

## Datasets

### `benchmark_dataset.json` (Generic IT — 7 cases)
Generic enterprise IT scenarios: VPN errors, SAP issues, Outlook crashes, escalations.
Used for: Baseline model comparison across common IT support scenarios.

### `zoho_benchmark_dataset.json` (Real Zoho — 7 cases)
Derived from real resolved Zoho Desk tickets at PCB Apps.
Used for: Testing the bot against actual historical support conversations.

| ID | Category | Query Topic |
|---|---|---|
| ZT-001 | Zoho-Ticket | JE batch posting error — end of month |
| ZT-002 | Zoho-Archive | Zoho access denied for DC33/JFK |
| ZT-003 | Zoho-Archive | HMO retirees active on eligibility file |
| ZT-004 | Zoho-Ticket | Address book blank value issue |
| ZT-005 | Zoho-Ticket | Daiwa fiscal year-end close process |
| ZT-006 | Zoho-Archive | Remove member from eligibility file |
| ZT-007 | Edge-Case | Vague query — "something is broken" |
