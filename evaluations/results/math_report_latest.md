# Quantitative Model Performance Report (Zoho Tickets)

**Generated on:** 2026-04-02 14:10:31
**Dataset:** Zoho Tickets
**Source Data:** comparison_latest.csv

## 1. Mathematical Metric Definitions
*   **BLEU Score (Precision):** Measures how similar the bot’s response is to the expected support answer. It is usually calculated on a scale from **0 to 1**, where values closer to **1** mean stronger wording similarity. In this report, it is shown as a **percentage** for easier understanding.
*   **ROUGE-L Score (Recall):** Measures how much of the important expected information is included in the bot’s response. It is usually calculated on a scale from **0 to 1**, where values closer to **1** mean better coverage of the expected answer. In this report, it is shown as a **percentage** for easier understanding.
*   **BERTScore (Semantic):** Measures the semantic similarity between the bot's response and the expected answer using AI embeddings. **This is the strongest metric for judging quality because it understands meaning, not just exact words.** Scale: 0-100% (Higher is better).

> **Note:** The BLEU and ROUGE-L values in this evaluation are relatively low because the bot’s responses are compared against short reference answers. In support systems, the bot may use different wording, extra explanation, or additional troubleshooting steps, which reduces overlap-based scores even when the answer is helpful and accurate.

## 2. Model Comparison (Avg %)

| model               | BLEU Score (0-1)   | ROUGE-L (0-1)   | BERTScore (0-1)   |   Latency (s) |
|:--------------------|:-------------------|:----------------|:------------------|--------------:|
| Gemini 2.5 Pro      | 22.59%             | 38.96%          | 90.12%            |       21.1025 |
| Grok 4.20 Reasoning | 24.05%             | 37.91%          | 90.84%            |       11.7457 |

## 3. Case-by-Case (%) 

### Model: Gemini 2.5 Pro
| case_id   | bleu_pct   | rouge_l_pct   | bert_pct   |
|:----------|:-----------|:--------------|:-----------|
| ZT-001    | 26.05%     | 46.48%        | 91.75%     |
| ZT-002    | 31.49%     | 45.89%        | 91.22%     |
| ZT-003    | 28.97%     | 49.00%        | 93.08%     |
| ZT-004    | 37.29%     | 47.37%        | 92.10%     |
| ZT-005    | 4.51%      | 25.29%        | 85.66%     |
| ZT-006    | 18.12%     | 37.97%        | 89.15%     |
| ZT-007    | 11.23%     | 28.19%        | 88.96%     |
| ZT-008    | 23.09%     | 31.50%        | 89.06%     |

### Model: Grok 4.20 Reasoning
| case_id   | bleu_pct   | rouge_l_pct   | bert_pct   |
|:----------|:-----------|:--------------|:-----------|
| ZT-001    | 21.00%     | 43.51%        | 91.56%     |
| ZT-002    | 26.71%     | 40.16%        | 91.62%     |
| ZT-003    | 30.03%     | 47.66%        | 93.35%     |
| ZT-004    | 41.06%     | 50.19%        | 93.25%     |
| ZT-006    | 14.63%     | 32.52%        | 89.38%     |
| ZT-007    | 14.27%     | 25.32%        | 88.16%     |
| ZT-008    | 20.66%     | 26.02%        | 88.55%     |

