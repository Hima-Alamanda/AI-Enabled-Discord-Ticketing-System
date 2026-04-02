# Evaluation Report
**Generated:** 2026-04-02 14:57:29

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
## 2. Quality Metrics (0-5 Scale)
Each model's response is scored by an independent AI Auditor based on this scale:

| Score | Rating | Description |
|:---:|:---|:---|
| **5** | **Excellent** | Fully correct, clear, well-structured, and follows all required rules |
| **4** | **Good** | Correct and helpful, with only minor issues in wording, tone, or formatting. |
| **3** | **Acceptable** | Mostly correct, but missing some details or clarity. |
| **1-2** | **Poor** | Contains important mistakes, unclear steps, or does not fully address the user’s issue. |
| **0** | **Failure** | Incorrect, misleading, made up facts, or failed to answer the query. |

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
| PROMPT A          | Gemini 2.5 Pro      |                2.75 |                 3    |                  3    |                     3.88 |                       4.75 |               5    |                     3.38 |                   4.62 |
| PROMPT A          | Grok 4.20 Reasoning |                2.5  |                 2.5  |                  3.12 |                     3.88 |                       3.88 |               4.38 |                     2.75 |                   4    |
| PROMPT B          | Gemini 2.5 Pro      |                2.62 |                 2.88 |                  3    |                     4.12 |                       4.75 |               5    |                     2.62 |                   4.75 |
| PROMPT B          | Grok 4.20 Reasoning |                2.88 |                 3.12 |                  3.12 |                     3.88 |                       3.62 |               4.38 |                     2.88 |                   3.88 |
| PROMPT C          | Gemini 2.5 Pro      |                2.5  |                 3.12 |                  2.5  |                     3.25 |                       4.38 |               4.38 |                     3.12 |                   3.75 |
| PROMPT C          | Grok 4.20 Reasoning |                2.38 |                 2.5  |                  3    |                     4    |                       3.38 |               4.38 |                     2.62 |                   3.75 |
| PROMPT D          | Gemini 2.5 Pro      |                2.88 |                 3.25 |                  3    |                     4.25 |                       4.62 |               4.88 |                     3    |                   4.62 |
| PROMPT D          | Grok 4.20 Reasoning |                2.75 |                 2.88 |                  3.12 |                     4.25 |                       4    |               5    |                     3    |                   4.62 |

## 3. Mathematical Accuracy (Alignment)
*   **BLEU Score (Precision):** Measures wording similarity to the expected support answer. Scale: 0-100% (Higher is closer alignment).
*   **ROUGE-L Score (Recall):** Measures coverage of expected important information. Scale: 0-100% (Higher is better coverage).
*   **BERTScore:** Measures semantic similarity between the chatbot response and the expected answer using embedding-based matching. **This is one of the strongest metrics for judging response quality because it focuses on meaning, not just exact word overlap.** Scale: 0-100% (higher is better).

### Model Comparison (Avg %)
| Prompt   | Model               | bleu_score   | rouge_l_score   | bert_score   |   latency |
|:---------|:--------------------|:-------------|:----------------|:-------------|----------:|
| PROMPT A | Gemini 2.5 Pro      | 21.07%       | 37.16%          | 90.06%       |   20.7676 |
| PROMPT A | Grok 4.20 Reasoning | 23.68%       | 35.54%          | 90.47%       |   12.2916 |
| PROMPT B | Gemini 2.5 Pro      | 18.30%       | 36.04%          | 89.72%       |   20.8426 |
| PROMPT B | Grok 4.20 Reasoning | 16.50%       | 31.55%          | 89.73%       |   12.3949 |
| PROMPT C | Gemini 2.5 Pro      | 13.69%       | 31.89%          | 88.83%       |   20.0476 |
| PROMPT C | Grok 4.20 Reasoning | 13.09%       | 30.84%          | 89.19%       |   14.188  |
| PROMPT D | Gemini 2.5 Pro      | 16.38%       | 27.76%          | 88.71%       |   21.3696 |
| PROMPT D | Grok 4.20 Reasoning | 14.44%       | 28.22%          | 89.21%       |   14.1498 |
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
| PROMPT A | Gemini 2.5 Pro      |             20.77 |        3133.88 |          427.88 |        6195.12 |
| PROMPT A | Grok 4.20 Reasoning |             12.29 |        3203.25 |          432    |        7311.12 |
| PROMPT B | Gemini 2.5 Pro      |             20.84 |        2834.25 |          409.12 |        6026.25 |
| PROMPT B | Grok 4.20 Reasoning |             12.39 |        2890.5  |          443.88 |        7315.25 |
| PROMPT C | Gemini 2.5 Pro      |             20.05 |        2739.25 |          363.38 |        6131.62 |
| PROMPT C | Grok 4.20 Reasoning |             14.19 |        2804.12 |          375.75 |        7387.5  |
| PROMPT D | Gemini 2.5 Pro      |             21.37 |        2887.12 |          486.5  |        6351.75 |
| PROMPT D | Grok 4.20 Reasoning |             14.15 |        2904.88 |          445.88 |        6991.38 |

## 6. Case-by-Case Breakdown (%)

### Model: Gemini 2.5 Pro
| Prompt_Strategy   | Case_ID   | bleu_pct   | rouge_l_pct   | bert_pct   |
|:------------------|:----------|:-----------|:--------------|:-----------|
| PROMPT A          | ZT-001    | 29.01%     | 53.43%        | 92.47%     |
| PROMPT A          | ZT-002    | 25.98%     | 34.70%        | 90.56%     |
| PROMPT A          | ZT-003    | 27.91%     | 47.77%        | 92.80%     |
| PROMPT A          | ZT-004    | 25.20%     | 31.30%        | 90.04%     |
| PROMPT A          | ZT-005    | 5.74%      | 26.62%        | 86.54%     |
| PROMPT A          | ZT-006    | 19.17%     | 39.34%        | 89.61%     |
| PROMPT A          | ZT-007    | 12.65%     | 31.39%        | 89.34%     |
| PROMPT A          | ZT-008    | 22.93%     | 32.75%        | 89.09%     |
| PROMPT B          | ZT-001    | 23.67%     | 50.74%        | 92.18%     |
| PROMPT B          | ZT-002    | 24.67%     | 43.87%        | 91.31%     |
| PROMPT B          | ZT-003    | 34.27%     | 49.39%        | 92.96%     |
| PROMPT B          | ZT-004    | 15.02%     | 30.77%        | 88.98%     |
| PROMPT B          | ZT-005    | 5.87%      | 24.09%        | 86.23%     |
| PROMPT B          | ZT-006    | 7.12%      | 30.41%        | 87.79%     |
| PROMPT B          | ZT-007    | 13.95%     | 29.41%        | 90.02%     |
| PROMPT B          | ZT-008    | 21.79%     | 29.66%        | 88.26%     |
| PROMPT C          | ZT-001    | 9.72%      | 34.62%        | 89.30%     |
| PROMPT C          | ZT-002    | 25.67%     | 32.20%        | 91.01%     |
| PROMPT C          | ZT-003    | 18.22%     | 37.76%        | 90.72%     |
| PROMPT C          | ZT-004    | 27.01%     | 50.93%        | 91.42%     |
| PROMPT C          | ZT-005    | 3.16%      | 21.70%        | 85.31%     |
| PROMPT C          | ZT-006    | 6.02%      | 27.40%        | 85.97%     |
| PROMPT C          | ZT-007    | 4.74%      | 27.27%        | 89.35%     |
| PROMPT C          | ZT-008    | 15.01%     | 23.28%        | 87.59%     |
| PROMPT D          | ZT-001    | 17.99%     | 36.48%        | 90.28%     |
| PROMPT D          | ZT-002    | 20.80%     | 25.77%        | 89.20%     |
| PROMPT D          | ZT-003    | 20.01%     | 33.22%        | 90.70%     |
| PROMPT D          | ZT-004    | 18.87%     | 26.86%        | 88.11%     |
| PROMPT D          | ZT-005    | 12.55%     | 26.11%        | 86.72%     |
| PROMPT D          | ZT-006    | 15.06%     | 28.97%        | 88.90%     |
| PROMPT D          | ZT-007    | 12.85%     | 24.79%        | 88.57%     |
| PROMPT D          | ZT-008    | 12.93%     | 19.84%        | 87.18%     |

### Model: Grok 4.20 Reasoning
| Prompt_Strategy   | Case_ID   | bleu_pct   | rouge_l_pct   | bert_pct   |
|:------------------|:----------|:-----------|:--------------|:-----------|
| PROMPT A          | ZT-001    | 20.88%     | 39.71%        | 91.60%     |
| PROMPT A          | ZT-002    | 32.03%     | 41.27%        | 92.27%     |
| PROMPT A          | ZT-003    | 32.62%     | 45.08%        | 93.02%     |
| PROMPT A          | ZT-004    | 39.84%     | 48.87%        | 93.15%     |
| PROMPT A          | ZT-005    | 13.19%     | 24.83%        | 88.33%     |
| PROMPT A          | ZT-006    | 13.28%     | 29.83%        | 88.40%     |
| PROMPT A          | ZT-007    | 12.30%     | 19.51%        | 87.48%     |
| PROMPT A          | ZT-008    | 25.27%     | 35.25%        | 89.51%     |
| PROMPT B          | ZT-001    | 15.15%     | 40.00%        | 91.29%     |
| PROMPT B          | ZT-002    | 22.01%     | 32.48%        | 91.14%     |
| PROMPT B          | ZT-003    | 27.88%     | 39.66%        | 92.49%     |
| PROMPT B          | ZT-004    | 31.96%     | 48.22%        | 91.53%     |
| PROMPT B          | ZT-005    | 11.62%     | 21.22%        | 87.81%     |
| PROMPT B          | ZT-006    | 5.72%      | 28.32%        | 88.44%     |
| PROMPT B          | ZT-007    | 4.33%      | 20.90%        | 86.29%     |
| PROMPT B          | ZT-008    | 13.34%     | 21.58%        | 88.83%     |
| PROMPT C          | ZT-001    | 13.68%     | 31.84%        | 89.97%     |
| PROMPT C          | ZT-002    | 16.03%     | 40.00%        | 91.27%     |
| PROMPT C          | ZT-003    | 13.85%     | 37.84%        | 91.26%     |
| PROMPT C          | ZT-004    | 25.15%     | 50.47%        | 91.30%     |
| PROMPT C          | ZT-005    | 14.06%     | 21.60%        | 87.76%     |
| PROMPT C          | ZT-006    | 6.36%      | 25.33%        | 87.66%     |
| PROMPT C          | ZT-007    | 0.92%      | 16.08%        | 86.09%     |
| PROMPT C          | ZT-008    | 14.64%     | 23.58%        | 88.24%     |
| PROMPT D          | ZT-001    | 15.04%     | 39.70%        | 91.30%     |
| PROMPT D          | ZT-002    | 20.41%     | 28.12%        | 90.48%     |
| PROMPT D          | ZT-003    | 26.55%     | 38.17%        | 92.03%     |
| PROMPT D          | ZT-004    | 32.62%     | 41.35%        | 92.14%     |
| PROMPT D          | ZT-005    | 6.56%      | 19.16%        | 87.23%     |
| PROMPT D          | ZT-006    | 1.73%      | 25.62%        | 87.47%     |
| PROMPT D          | ZT-007    | 3.94%      | 15.73%        | 85.89%     |
| PROMPT D          | ZT-008    | 8.64%      | 17.89%        | 87.14%     |
