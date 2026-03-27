# Quantitative Model Performance Report

**Generated on:** 2026-03-27 13:11:29
**Source Data:** comparison_latest.csv

## 1. Metric Definitions
- **BLEU (Bilingual Evaluation Understudy):** Measures n-gram overlap. (0-1 range, higher is closer to ground truth phrases).
- **ROUGE-L (Longest Common Subsequence):** Measures structural similarity and recall. (0-1 range, higher is more comprehensive).

## 2. Model Comparison (Averages)

| model               |   bleu_score |   rouge_l_score |   latency |
|:--------------------|-------------:|----------------:|----------:|
| Gemini 2.5 Pro      |       0.0085 |          0.1059 |   24.07   |
| Grok 4.20 Reasoning |       0.005  |          0.0981 |   12.2814 |

## 3. Case-by-Case Mathematical Alignment

### Model: Gemini 2.5 Pro
| case_id   |   bleu_score |   rouge_l_score |
|:----------|-------------:|----------------:|
| TC-001    |       0.0264 |          0.1444 |
| TC-002    |       0.0034 |          0.1273 |
| TC-003    |       0.0092 |          0.0915 |
| MM-001    |       0.0039 |          0.0864 |
| MM-002    |       0.0028 |          0.08   |
| TC-006    |       0.0038 |          0.075  |
| MM-003    |       0.0101 |          0.1366 |

### Model: Grok 4.20 Reasoning
| case_id   |   bleu_score |   rouge_l_score |
|:----------|-------------:|----------------:|
| TC-001    |       0.0093 |          0.1075 |
| TC-002    |       0.0076 |          0.1064 |
| TC-003    |       0.0031 |          0.0984 |
| MM-001    |       0.0047 |          0.0979 |
| MM-002    |       0.0036 |          0.0865 |
| TC-006    |       0.0031 |          0.0947 |
| MM-003    |       0.0036 |          0.0952 |

