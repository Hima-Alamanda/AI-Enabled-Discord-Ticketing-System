# PCB Apps AI Bot — Model Evaluation Guide

This guide explains the metrics and current results from our side-by-side comparison of **Gemini 2.5 Pro** and **Grok 4.20 Reasoning** using real Zoho Desk support tickets.

---

## 1. Quality Metrics (0-5 Scale)
Each model's response is scored by an independent AI Auditor (Gemini 2.5 Flash) on a scale of **0 to 5**.

| Score | Rating | Description |
|:---:|:---|:---|
| **5** | **Excellent** | Perfect answer, follows all rules, tone is ideal. |
| **4** | **Good** | Accurate and helpful with minor style or formatting oversights. |
| **3** | **Acceptable** | Generally correct but misses some details. |
| **1-2** | **Poor** | Significant errors, confusing steps, or missed the user's intent. |
| **0** | **Failure** | Completely incorrect, hallucinated facts, or ignored the query. |

### The 8 Quality Categories
1.  **Correctness:** Was the final solution actually correct compared to the historical Zoho ticket?
2.  **Faithfulness:** Did the bot stick strictly to the internal Knowledge Base without inventing ("hallucinating") facts?
3.  **Actionability:** How clear and easy-to-follow were the step-by-step instructions for the user?
4.  **Format Adherence:** Did the bot use the required structured headers (Issue Analysis, Cause, Resolution, etc.)?
5.  **Ambiguity:** For vague questions, did the bot correctly ask for more info BEFORE trying to solve?
6.  **Multimodal:** Did the bot correctly interpret screenshots or images attached to the ticket?
7.  **Escalation:** Did the bot make the right decision to either solve the issue or raise it to a human agent?
8.  **Empathy:** Was the tone warm, professional, and helpful throughout the conversation?

---

## 2. Mathematical Metrics (%)
These metrics compare how similar the bot's sentences are to the "Ground Truth" answer from our database. These are presented as percentages (0% to 100%).

*   **BLEU Score (Precision):** Measures how many phrases the bot used that match the reference exactly. 
*   **ROUGE-L Score (Recall):** Measures how much of the structure of the summary was captured by the bot.

> **Note:** For support bots, scores between **10% and 30% are excellent**. Bots provide detailed, conversational answers, while the ground truth is usually a very short summary. A low percentage here just means the bot isn't a carbon-copy of the database, but can still be highly accurate.

---

## 3. Performance Metrics
*   **Latency:** The total time (in seconds) the bot took to process and reply.
*   **Token Usage:** The amount of "data" processed by the model (Input + Output). This directly relates to operational cost.

---

## Current Zoho Dataset Results (Summary)

### Quality & Performance (Avg)
| Metric | Gemini 2.5 Pro | Grok 4.20 Reasoning |
|:---|:---:|:---:|
| **Correctness** | **3.00 / 5** | 2.29 / 5 |
| **Faithfulness** | **2.83 / 5** | 2.00 / 5 |
| **Actionability** | 2.67 / 5 | **3.71 / 5** |
| **Empathy** | **4.50 / 5** | 4.43 / 5 |
| **Escalation Logic** | **3.50 / 5** | 2.86 / 5 |
| **Latency (Speed)** | 26.38 seconds | **15.33 seconds** |
| **Total Token Cost** | **Lower** | Higher |

### Mathematical Alignment (%)
| Metric | Gemini 2.5 Pro | Grok 4.20 Reasoning |
|:---|:---:|:---:|
| **BLEU %** | 1.72% | **2.20%** |
| **ROUGE-L %** | **15.78%** | 15.53% |

---

## Final Recommendation
We recommend **Gemini 2.5 Pro** for the PCB Apps production bot. 

*   **Why:** It is more **faithful** to our internal data and has a higher **correctness** rate. 
*   **Risk:** While Grok is faster, it occasionally "hallucinates" steps that do not exist in our systems, which could mislead users. Gemini is safer and more empathetic.
