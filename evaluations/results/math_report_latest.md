# Quantitative Model Performance Report (Zoho Tickets)

**Generated on:** 2026-03-31 15:50:22
**Dataset:** Zoho Tickets
**Source Data:** comparison_latest.csv

## 1. Mathematical Metric Definitions
*   **BLEU Score (Precision):** Measures how many phrases the bot used that match the reference exactly.
*   **ROUGE-L Score (Recall):** Measures how much of the structure of the summary was captured by the bot.

> **Note:** For support bots, scores between **10% and 30% are excellent**. Bots provide detailed, conversational answers, while the ground truth is usually a very short summary. A low percentage here just means the bot isn't a carbon-copy of the database, but can still be highly accurate.

## 2. Model Comparison (Avg %)

| model               | bleu_score   | rouge_l_score   |   latency |
|:--------------------|:-------------|:----------------|----------:|
| Gemini 2.5 Pro      | 2.00%        | 17.53%          |   25.4283 |
| Grok 4.20 Reasoning | 1.34%        | 14.52%          |   15.65   |

## 3. Case-by-Case (%) 

### Model: Gemini 2.5 Pro
| case_id   | bleu_pct   | rouge_l_pct   |
|:----------|:-----------|:--------------|
| ZT-001    | 0.86%      | 17.39%        |
| ZT-002    | 0.37%      | 14.04%        |
| ZT-003    | 5.69%      | 21.13%        |
| ZT-005    | 3.97%      | 19.61%        |
| ZT-006    | 0.78%      | 23.02%        |
| ZT-007    | 0.32%      | 10.00%        |

### Model: Grok 4.20 Reasoning
| case_id   | bleu_pct   | rouge_l_pct   |
|:----------|:-----------|:--------------|
| ZT-001    | 1.36%      | 17.83%        |
| ZT-002    | 0.83%      | 12.57%        |
| ZT-003    | 0.43%      | 12.87%        |
| ZT-004    | 1.16%      | 14.86%        |
| ZT-006    | 3.70%      | 21.86%        |
| ZT-007    | 0.54%      | 7.14%         |

