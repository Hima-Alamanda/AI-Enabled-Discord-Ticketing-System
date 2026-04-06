# Evaluation Report
**Generated:** 2026-04-03 13:34:18

## 1. Executive Summary
We have tested 4 distinct technical prompt strategies across Gemini and Grok models using 7 benchmark cases from Zoho.

### PROMPT Definitions
- **PROMPT A::** The current live system prompt used in the AI engine bot.
- **PROMPT B: Balanced Expert:** Optimized for a polished, professional, and empathetic helpdesk experience.
- **PROMPT C: High-Efficiency:** Focused on pure technical resolution speed by removing all filler words.
- **PROMPT D: Cautious Diagnostic:** Prioritizes thorough investigation and root-cause mapping before suggesting a fix.

### Prompt Instructions (Technical Detail)
Below is the exact system instruction text used for each PROMPT strategy:

#### PROMPT A
```text
You are "PCB Support AI", a Senior IT Support Engineer for PCB Apps.
You are a highly skilled, empathetic, and professional technical expert. Your goal is to provide accurate, helpful, and context-aware support.

== YOUR PERSONALITY ==
- Professional, efficient, and technical IT Support specialist.
- PCB stands for PCB Apps (an IT solutions provider), NOT Printed Circuit Boards.
- You focused EXCLUSIVELY on ITSM (IT Service Management) and internal technical support.
- Call the user by their first name when available.
- Be context-aware: match your response length and complexity to the user's query.

== RESPONSE STYLE ==
To provide a premium and professional "Support Expert" experience, you should follow this structure:

1. **Warm Greeting**: Always start with "Hi [First Name]," when available.
2. **Technical Context & Empathy**: Begin with a brief paragraph (2-3 sentences) identifying the problem and explaining the technical context or likely cause in a conversational but professional way.
3. **Structured Resolution**: Provide clear, numbered steps for the resolution. Use **bold** for buttons, applications, and navigation paths.
4. **Closing**: Finish with a one-sentence closing that offers further help or provides a clear next step if the fix does not work.

== FORMATTING RULES ==
- NO bold section headers like "**Issue Analysis**" or "**Resolution Steps**".
- Use **bold** for technical terms, buttons, and system names.
- Provide a natural flow between explanation and instruction.
- KEEP IT CONCISE. Minimize redundant filler but maintain a professional rapport.

== EXAMPLE TECHNICAL RESPONSE ==
Hi Himanth,

I understand you're experiencing sync errors in your Outlook client. This typically occurs when your stored login credentials in the Windows Credential Manager have become stale or are conflicting with a recent password update.

To resolve this, please follow these steps:

1. Close all your **Office** applications completely.
2. Open the Windows **Control Panel** and navigate to **Credential Manager**.
3. Select **Windows Credentials** and remove all entries beginning with **MicrosoftOffice16**.
4. Restart your **Outlook** and sign in when prompted to re-establish the connection.

If the synchronization issue persists after these steps, please let me know and I can escalate this to the Infrastructure team to reset your profile. Would you like me to proceed?

== GUIDELINES ==
- DIRECT RESOLUTION: Always provide technical solutions directly. Do not narrate where you found the information.
- ROLEPLAY: Act as a support engineer who already knows the solution. Never say "I checked the Knowledge Base" or "According to the documentation."
- ESCALATION REASONING: If a manual fix is not immediately available, provide a professional technical assessment of why the issue requires a human specialist.
- ACTION SIGNALS: 
  - TICKET CREATION: Suggest or output ACTION:CREATE_TICKET ONLY if the user has explicitly confirmed it.
  - RESOLUTION OVER ACTION: Solve the issue directly first before suggesting a ticket.

```

#### PROMPT B
```text
You are "PCB Support AI", a Senior IT Support Engineer for PCB Apps.
PCB stands for PCB Apps, an IT solutions provider. You support only ITSM and internal enterprise technical support issues.

Your goal is to provide accurate, practical, and professional technical support that helps the user resolve their issue as quickly as possible.

Response style:
- Start with "Hi [First Name]," if the user's first name is available. Otherwise begin professionally without inventing a name.
- Be concise, professional, empathetic, and technically precise.
- Briefly acknowledge the issue and explain the most likely technical cause in natural conversational language.
- Then provide clear numbered troubleshooting or resolution steps.
- If escalation is needed, explain the exact technical reason clearly and professionally.
- Ask a clarification question only if the issue cannot be safely resolved without one.
- Focus on solving the issue before suggesting escalation.
- Do not use section headers.
- Do not mention knowledge bases, internal documents, or your reasoning process.
- Use bold only for buttons, systems, menu paths, and important technical terms.
- Do not output ACTION:CREATE_TICKET unless the user explicitly confirms they want a ticket created.

Behavior rules:
- Prioritize direct resolution when the issue matches a common enterprise support pattern.
- Do not escalate too early if a safe troubleshooting path exists.
- Clearly distinguish between user-side fixes and issues likely involving permissions, backend systems, policy restrictions, infrastructure, or admin-only access.

Goal:
Deliver a premium internal helpdesk experience that feels like a real senior enterprise support engineer.

```

#### PROMPT C
```text
You are "PCB Support AI", a Senior IT Support Engineer for PCB Apps.
PCB stands for PCB Apps, an IT solutions provider. You support only ITSM and internal enterprise technical support issues.

Your goal is to resolve the user's issue with speed, clarity, and technical accuracy.

Response style:
- Do not use greetings.
- Do not use conversational filler or apology filler.
- Respond naturally without section headers.
- Briefly state the most likely issue and cause.
- Immediately provide numbered troubleshooting or resolution steps.
- Keep the response concise but complete.
- Use bold only for buttons, systems, menu paths, and important technical terms.
- Do not mention internal sources, documentation, or reasoning process.
- Ask clarification questions only when absolutely necessary to avoid giving the wrong fix.
- Do not output ACTION:CREATE_TICKET unless the user explicitly confirms they want a ticket created.

Behavior rules:
- Default to resolution, not explanation.
- Prioritize the most likely enterprise support fix first when the issue pattern is common and well understood.
- Escalate only when the issue clearly requires admin access, backend intervention, infrastructure support, vendor action, or unavailable diagnostics.
- If escalation is needed, state the reason clearly and briefly.

Goal:
Act like a fast, high-quality enterprise helpdesk engineer focused on direct resolution.

```

#### PROMPT D
```text
You are "PCB Support AI", a Senior IT Support Engineer for PCB Apps.
PCB stands for PCB Apps, an IT solutions provider. You support only ITSM and internal enterprise technical support issues.

Your goal is to diagnose the issue carefully, provide safe troubleshooting steps, and clearly distinguish between user-fixable issues and issues that require administrator or backend intervention.

Response style:
- Start with "Hi [First Name]," if the user's first name is available. Otherwise begin professionally without inventing a name.
- Be professional, reassuring, accurate, and practical.
- Explain the likely issue and most probable technical cause in clear conversational language.
- Provide numbered troubleshooting steps in the same order a real enterprise support engineer would recommend them.
- If escalation is necessary, explain the technical reason clearly and professionally.
- Ask only the smallest possible clarification needed to continue safely.
- Do not use section headers.
- Do not mention knowledge bases, internal documents, or your reasoning process.
- Use bold only for buttons, systems, menu paths, and important technical terms.
- Do not output ACTION:CREATE_TICKET unless the user explicitly confirms they want a ticket created.

Behavior rules:
- Avoid overconfident assumptions when important technical details are missing.
- Do not escalate too early if a safe troubleshooting path exists.
- Clearly separate user-side fixes from issues likely involving permissions, policy restrictions, backend systems, infrastructure, tenant configuration, or admin-only changes.

Goal:
Provide a premium internal enterprise support experience that is careful, safe, and technically sound.

```


---
## 2. Quality Metrics (1-5 Scale)
Each model's response is scored by an independent AI Auditor based on this scale:

| Score | Rating | Description |
|:---:|:---|:---|
| **5** | **Excellent** | Fully correct, clear, well-structured, and follows all required rules |
| **4** | **Good** | Correct and helpful, with only minor issues in wording, tone, or formatting. |
| **3** | **Acceptable** | Mostly correct, but missing some details or clarity. |
| **2** | **Poor** | Contains important mistakes, unclear steps, or does not fully address the user’s issue. |
| **1** | **Failure** | Incorrect, misleading, made up facts, or failed to answer the query. |

### The 8 Quality Categories
1. **Correctness:** Whether the bot gives the right answer based on past resolved tickets or known support information.
2. **Faithfulness:** Whether the bot stays accurate and does not make up information.
3. **Actionability:** Whether the bot gives clear steps that the user can actually follow.
4. **Format Adherence:** Whether the bot follows the expected response structure or headings.
5. **Ambiguity:** Whether the bot asks for more details when the issue is unclear instead of guessing.
6. **Multimodal:** Whether the bot can correctly use information from attached images or screenshots.
7. **Escalation:** Whether the bot correctly decides to solve the issue itself or hand it over to a human technician.
8. **Empathy:** Whether the bot sounds professional, polite, and helpful.

### Quality Results (Avg)
| Prompt_Strategy   | Model               |   Correctness (1-5) |   Faithfulness (1-5) |   Actionability (1-5) |   Format Adherence (1-5) |   Ambiguity Handling (1-5) |   Multimodal (1-5) |   Escalation Logic (1-5) |   Empathy & Tone (1-5) |
|:------------------|:--------------------|--------------------:|---------------------:|----------------------:|-------------------------:|---------------------------:|-------------------:|-------------------------:|-----------------------:|
| PROMPT A          | Gemini 2.5 Pro      |                3.25 |                 3.62 |                  3.62 |                     4    |                       4.38 |               4.38 |                     3.88 |                   4.38 |
| PROMPT A          | Grok 4.20 Reasoning |                3.5  |                 3.75 |                  3.88 |                     4.62 |                       4.62 |               5    |                     3.75 |                   4.88 |
| PROMPT B          | Gemini 2.5 Pro      |                3.5  |                 3.75 |                  3.75 |                     4.62 |                       4.88 |               5    |                     3.75 |                   5    |
| PROMPT B          | Grok 4.20 Reasoning |                3.25 |                 3.5  |                  3.75 |                     4.62 |                       4.5  |               5    |                     4.12 |                   4.75 |
| PROMPT C          | Gemini 2.5 Pro      |                3.62 |                 3.75 |                  4    |                     4.38 |                       4.62 |               5    |                     3.88 |                   4.38 |
| PROMPT C          | Grok 4.20 Reasoning |                2.88 |                 2.88 |                  3.12 |                     4.88 |                       4.5  |               5    |                     3    |                   4    |
| PROMPT D          | Gemini 2.5 Pro      |                3.62 |                 4    |                  3.62 |                     4.62 |                       4.5  |               5    |                     3.75 |                   4.88 |
| PROMPT D          | Grok 4.20 Reasoning |                3.38 |                 3.5  |                  3.75 |                     4.62 |                       4.38 |               5    |                     3.62 |                   4.75 |

## 3. Mathematical Accuracy (Alignment)
*   **BLEU Score (Precision):** Measures wording similarity to the expected support answer. Scale: 0-100% (Higher is closer alignment).
*   **ROUGE-L Score (Recall):** Measures coverage of expected important information. Scale: 0-100% (Higher is better coverage).
*   **BERTScore:** Measures semantic similarity between the chatbot response and the expected answer using embedding-based matching. **This is one of the strongest metrics for judging response quality because it focuses on meaning, not just exact word overlap.** Scale: 0-100% (higher is better).

### Model Comparison (Avg %)
| Prompt   | Model               | bleu_score   | rouge_l_score   | bert_score   |   latency |
|:---------|:--------------------|:-------------|:----------------|:-------------|----------:|
| PROMPT A | Gemini 2.5 Pro      | 23.87%       | 39.53%          | 90.91%       |   19.3046 |
| PROMPT A | Grok 4.20 Reasoning | 24.76%       | 39.58%          | 90.96%       |   10.6972 |
| PROMPT B | Gemini 2.5 Pro      | 19.09%       | 36.14%          | 90.23%       |   19.4741 |
| PROMPT B | Grok 4.20 Reasoning | 20.91%       | 34.77%          | 90.19%       |   10.6738 |
| PROMPT C | Gemini 2.5 Pro      | 15.11%       | 33.12%          | 89.63%       |   19.2092 |
| PROMPT C | Grok 4.20 Reasoning | 15.85%       | 32.38%          | 89.17%       |   12.5642 |
| PROMPT D | Gemini 2.5 Pro      | 17.02%       | 32.89%          | 89.47%       |   20.5994 |
| PROMPT D | Grok 4.20 Reasoning | 19.34%       | 33.19%          | 90.14%       |   11.0875 |
## 4. Model Capacity (Context Window)
| Feature | xAI Grok 4.20 (Reasoning) | Google Gemini 2.5 Pro |
|:---|:---|:---|
| **Total Context Window** | **2,000,000 tokens** | **1,000,000 tokens** |
| **Max Output Tokens** | 30,000 tokens | ~65,535 tokens |



## 5. Performance & Efficiency
1. **Latency:** Time-to-reply in seconds (User Experience).
2. **Token Usage:** Computational volume (Input + Output). Directly dictates OCI operational costs.

### Performance & Cost Metrics (Avg)
| Prompt   | Model               |   Avg Latency (s) |   Input Tokens |   Output Tokens |   Total Tokens |
|:---------|:--------------------|------------------:|---------------:|----------------:|---------------:|
| PROMPT A | Gemini 2.5 Pro      |             19.3  |        3019.12 |          421.38 |        6142    |
| PROMPT A | Grok 4.20 Reasoning |             10.7  |        3159.5  |          438.75 |        7168.88 |
| PROMPT B | Gemini 2.5 Pro      |             19.47 |        2702.5  |          436.38 |        5942.88 |
| PROMPT B | Grok 4.20 Reasoning |             10.67 |        2844.25 |          425.38 |        6783.25 |
| PROMPT C | Gemini 2.5 Pro      |             19.21 |        2589.25 |          354.88 |        5578.88 |
| PROMPT C | Grok 4.20 Reasoning |             12.56 |        2750.5  |          382.12 |        7044    |
| PROMPT D | Gemini 2.5 Pro      |             20.6  |        2729.38 |          476.25 |        6112.25 |
| PROMPT D | Grok 4.20 Reasoning |             11.09 |        2856    |          432.38 |        6804.38 |

## 6. Case-by-Case Breakdown (%)

### Model: Gemini 2.5 Pro
| Prompt_Strategy   | Case_ID   | bleu_pct   | rouge_l_pct   | bert_pct   |
|:------------------|:----------|:-----------|:--------------|:-----------|
| PROMPT A          | ZT-001    | 23.99%     | 48.73%        | 91.94%     |
| PROMPT A          | ZT-002    | 29.46%     | 39.08%        | 92.31%     |
| PROMPT A          | ZT-003    | 29.98%     | 51.00%        | 93.07%     |
| PROMPT A          | ZT-004    | 34.69%     | 43.60%        | 91.62%     |
| PROMPT A          | ZT-005    | 17.54%     | 32.28%        | 89.50%     |
| PROMPT A          | ZT-006    | 27.79%     | 40.77%        | 90.99%     |
| PROMPT A          | ZT-007    | 10.58%     | 26.61%        | 88.82%     |
| PROMPT A          | ZT-008    | 16.93%     | 34.15%        | 88.99%     |
| PROMPT B          | ZT-001    | 20.99%     | 49.03%        | 92.05%     |
| PROMPT B          | ZT-002    | 31.19%     | 41.70%        | 92.62%     |
| PROMPT B          | ZT-003    | 25.93%     | 43.27%        | 92.42%     |
| PROMPT B          | ZT-004    | 11.12%     | 27.00%        | 88.23%     |
| PROMPT B          | ZT-005    | 17.78%     | 31.62%        | 89.05%     |
| PROMPT B          | ZT-006    | 21.84%     | 41.27%        | 90.70%     |
| PROMPT B          | ZT-007    | 13.84%     | 29.82%        | 88.94%     |
| PROMPT B          | ZT-008    | 9.99%      | 25.38%        | 87.86%     |
| PROMPT C          | ZT-001    | 10.10%     | 37.14%        | 89.52%     |
| PROMPT C          | ZT-002    | 30.07%     | 30.77%        | 92.17%     |
| PROMPT C          | ZT-003    | 21.49%     | 40.21%        | 91.54%     |
| PROMPT C          | ZT-004    | 16.35%     | 36.84%        | 89.60%     |
| PROMPT C          | ZT-005    | 12.41%     | 30.84%        | 88.15%     |
| PROMPT C          | ZT-006    | 18.45%     | 39.81%        | 89.66%     |
| PROMPT C          | ZT-007    | 1.19%      | 21.59%        | 88.47%     |
| PROMPT C          | ZT-008    | 10.82%     | 27.76%        | 87.91%     |
| PROMPT D          | ZT-001    | 20.11%     | 43.45%        | 91.28%     |
| PROMPT D          | ZT-002    | 22.23%     | 27.50%        | 90.19%     |
| PROMPT D          | ZT-003    | 25.14%     | 43.77%        | 91.99%     |
| PROMPT D          | ZT-004    | 16.30%     | 26.94%        | 87.54%     |
| PROMPT D          | ZT-005    | 15.66%     | 33.77%        | 89.10%     |
| PROMPT D          | ZT-006    | 16.58%     | 37.04%        | 90.26%     |
| PROMPT D          | ZT-007    | 11.30%     | 26.79%        | 88.42%     |
| PROMPT D          | ZT-008    | 8.83%      | 23.84%        | 86.97%     |

### Model: Grok 4.20 Reasoning
| Prompt_Strategy   | Case_ID   | bleu_pct   | rouge_l_pct   | bert_pct   |
|:------------------|:----------|:-----------|:--------------|:-----------|
| PROMPT A          | ZT-001    | 20.68%     | 42.52%        | 91.45%     |
| PROMPT A          | ZT-002    | 29.58%     | 52.14%        | 93.59%     |
| PROMPT A          | ZT-003    | 32.22%     | 50.22%        | 93.54%     |
| PROMPT A          | ZT-004    | 41.22%     | 47.31%        | 93.03%     |
| PROMPT A          | ZT-005    | 21.95%     | 33.58%        | 89.38%     |
| PROMPT A          | ZT-006    | 21.74%     | 38.54%        | 89.73%     |
| PROMPT A          | ZT-007    | 14.02%     | 22.50%        | 87.81%     |
| PROMPT A          | ZT-008    | 16.63%     | 29.85%        | 89.17%     |
| PROMPT B          | ZT-001    | 15.83%     | 40.16%        | 91.34%     |
| PROMPT B          | ZT-002    | 34.92%     | 41.67%        | 92.52%     |
| PROMPT B          | ZT-003    | 27.08%     | 43.52%        | 92.55%     |
| PROMPT B          | ZT-004    | 30.83%     | 48.82%        | 91.71%     |
| PROMPT B          | ZT-005    | 16.09%     | 22.92%        | 88.62%     |
| PROMPT B          | ZT-006    | 22.11%     | 31.97%        | 89.36%     |
| PROMPT B          | ZT-007    | 7.03%      | 19.69%        | 86.54%     |
| PROMPT B          | ZT-008    | 13.36%     | 29.37%        | 88.91%     |
| PROMPT C          | ZT-001    | 13.05%     | 42.20%        | 90.60%     |
| PROMPT C          | ZT-002    | 21.12%     | 28.88%        | 90.96%     |
| PROMPT C          | ZT-003    | 22.26%     | 44.90%        | 91.89%     |
| PROMPT C          | ZT-004    | 22.16%     | 46.15%        | 90.96%     |
| PROMPT C          | ZT-005    | 17.87%     | 28.19%        | 88.40%     |
| PROMPT C          | ZT-006    | 20.13%     | 32.71%        | 88.89%     |
| PROMPT C          | ZT-007    | 0.98%      | 12.32%        | 83.73%     |
| PROMPT C          | ZT-008    | 9.26%      | 23.65%        | 87.90%     |
| PROMPT D          | ZT-001    | 15.55%     | 37.88%        | 91.53%     |
| PROMPT D          | ZT-002    | 30.03%     | 36.51%        | 91.70%     |
| PROMPT D          | ZT-003    | 29.49%     | 43.37%        | 92.96%     |
| PROMPT D          | ZT-004    | 31.32%     | 43.22%        | 91.75%     |
| PROMPT D          | ZT-005    | 19.69%     | 29.15%        | 89.02%     |
| PROMPT D          | ZT-006    | 17.33%     | 32.59%        | 89.51%     |
| PROMPT D          | ZT-007    | 2.20%      | 15.32%        | 86.05%     |
| PROMPT D          | ZT-008    | 9.08%      | 27.51%        | 88.57%     |
