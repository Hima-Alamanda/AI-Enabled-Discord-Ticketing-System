# Quantitative Model Performance Report (Zoho Tickets)

**Generated on:** 2026-04-01 10:59:42
**Dataset:** Zoho Tickets
**Source Data:** comparison_latest.csv

## 1. Mathematical Metric Definitions
*   **BLEU Score (Precision):** Measures how similar the bot’s response is to the expected support answer. It is usually calculated on a scale from **0 to 1**, where values closer to **1** mean stronger wording similarity. In this report, it is shown as a **percentage** for easier understanding.
*   **ROUGE-L Score (Recall):** Measures how much of the important expected information is included in the bot’s response. It is usually calculated on a scale from **0 to 1**, where values closer to **1** mean better coverage of the expected answer. In this report, it is shown as a **percentage** for easier understanding.

> **Note:** The BLEU and ROUGE-L values in this evaluation are relatively low because the bot’s responses are compared against short reference answers. In support systems, the bot may use different wording, extra explanation, or additional troubleshooting steps, which reduces overlap-based scores even when the answer is helpful and accurate.

## 2. Model Comparison (Avg %)

| model               | bleu_score   | rouge_l_score   |   latency |
|:--------------------|:-------------|:----------------|----------:|
| Gemini 2.5 Pro      | 8.30%        | 26.00%          |   25.9571 |
| Grok 4.20 Reasoning | 8.74%        | 26.77%          |   17.5143 |

## 3. Case-by-Case (%) 

### Model: Gemini 2.5 Pro
| case_id   | bleu_pct   | rouge_l_pct   |
|:----------|:-----------|:--------------|
| ZT-001    | 0.00%      | 5.16%         |
| ZT-002    | 19.16%     | 33.47%        |
| ZT-003    | 6.06%      | 33.44%        |
| ZT-004    | 4.03%      | 21.60%        |
| ZT-005    | 1.91%      | 22.13%        |
| ZT-006    | 11.34%     | 32.43%        |
| ZT-007    | 15.63%     | 33.77%        |

### Model: Grok 4.20 Reasoning
| case_id   | bleu_pct   | rouge_l_pct   |
|:----------|:-----------|:--------------|
| ZT-001    | 3.06%      | 23.10%        |
| ZT-002    | 17.82%     | 35.74%        |
| ZT-003    | 7.57%      | 27.01%        |
| ZT-004    | 13.47%     | 28.91%        |
| ZT-005    | 10.93%     | 27.76%        |
| ZT-006    | 6.42%      | 30.88%        |
| ZT-007    | 1.88%      | 13.97%        |

