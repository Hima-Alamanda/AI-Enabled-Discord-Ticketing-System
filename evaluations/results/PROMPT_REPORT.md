# Evaluation Report
**Generated:** 2026-04-01 15:20:00

## 1. Executive Summary
We have tested 4 distinct technical prompt strategies across Gemini and Grok models using 7 benchmark cases from Zoho.

### PROMPT Definitions
- **PROMPT A:** The current live system prompt used in the AI engine bot.
- **PROMPT B: Balanced :** Optimized for a polished, professional, and empathetic helpdesk experience.
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
| Prompt_Strategy   | Model               |   Correctness |   Faithfulness |   Actionability |   Format_Adherence |   Ambiguity |   Multimodal |   Escalation |   Empathy |
|:------------------|:--------------------|--------------:|---------------:|----------------:|-------------------:|------------:|-------------:|-------------:|----------:|
| PROMPT A          | Gemini 2.5 Pro      |          1.86 |           2    |            1.57 |               4.43 |        4.57 |         3.57 |         2    |      4.29 |
| PROMPT A          | Grok 4.20 Reasoning |          1.71 |           1.29 |            3.14 |               4.71 |        4.43 |         3.57 |         3.71 |      4.86 |
| PROMPT B          | Gemini 2.5 Pro      |          2    |           2.14 |            1.86 |               4.14 |        4.29 |         1.43 |         2.43 |      4.57 |
| PROMPT B          | Grok 4.20 Reasoning |          1.43 |           1.29 |            2.14 |               3.57 |        2.71 |         2.86 |         1.71 |      3.29 |
| PROMPT C          | Gemini 2.5 Pro      |          2.14 |           2.57 |            3.14 |               4.43 |        4.86 |         2.86 |         3.43 |      4.43 |
| PROMPT C          | Grok 4.20 Reasoning |          1    |           1    |            2.14 |               3    |        2.86 |         2.86 |         1.29 |      2.71 |
| PROMPT D          | Gemini 2.5 Pro      |          2.29 |           3.14 |            2.43 |               4.71 |        3.43 |         2.86 |         2.71 |      4.86 |
| PROMPT D          | Grok 4.20 Reasoning |          1.29 |           1.71 |            1.71 |               3.14 |        2.71 |         1.43 |         1.29 |      3.43 |

## 3. Mathematical Accuracy (Alignment)
*   **BLEU Score (Precision):** Measures wording similarity to the expected support answer. Scale: 0-100% (Higher is closer alignment).
*   **ROUGE-L Score (Recall):** Measures coverage of expected important information. Scale: 0-100% (Higher is better coverage).

### Model Comparison (Avg %)
| Prompt   | Model               | bleu_score   | rouge_l_score   |   latency |
|:---------|:--------------------|:-------------|:----------------|----------:|
| PROMPT A | Gemini 2.5 Pro      | 7.65%        | 28.01%          |   24.5301 |
| PROMPT A | Grok 4.20 Reasoning | 17.91%       | 29.12%          |   12.9746 |
| PROMPT B | Gemini 2.5 Pro      | 10.68%       | 28.56%          |   22.5896 |
| PROMPT B | Grok 4.20 Reasoning | 12.97%       | 25.90%          |   12.9987 |
| PROMPT C | Gemini 2.5 Pro      | 5.62%        | 24.32%          |   22.1463 |
| PROMPT C | Grok 4.20 Reasoning | 7.70%        | 22.21%          |   19.6266 |
| PROMPT D | Gemini 2.5 Pro      | 6.89%        | 25.05%          |   24.402  |
| PROMPT D | Grok 4.20 Reasoning | 10.07%       | 24.21%          |   13.7371 |


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
| PROMPT A | Gemini 2.5 Pro      |             24.53 |        2783.14 |          392.71 |        5927.29 |
| PROMPT A | Grok 4.20 Reasoning |             12.97 |        3108.14 |          438.71 |        7824.57 |
| PROMPT B | Gemini 2.5 Pro      |             22.59 |        2723.43 |          417.43 |        6144.14 |
| PROMPT B | Grok 4.20 Reasoning |             13    |        2807.29 |          415.71 |        7423.29 |
| PROMPT C | Gemini 2.5 Pro      |             22.15 |        2627.71 |          373.43 |        6197.86 |
| PROMPT C | Grok 4.20 Reasoning |             19.63 |        2691    |          365    |        7632.29 |
| PROMPT D | Gemini 2.5 Pro      |             24.4  |        2766.43 |          456.57 |        6310.86 |
| PROMPT D | Grok 4.20 Reasoning |             13.74 |        2794.14 |          429.14 |        7545    |

## 6. Case-by-Case Breakdown (%)

### Model: Gemini 2.5 Pro
| Prompt_Strategy   | Case_ID   | bleu_pct   | rouge_l_pct   |
|:------------------|:----------|:-----------|:--------------|
| PROMPT A          | ZT-001    | 0.00%      | 8.48%         |
| PROMPT A          | ZT-002    | 7.89%      | 36.77%        |
| PROMPT A          | ZT-003    | 6.45%      | 28.06%        |
| PROMPT A          | ZT-004    | 4.88%      | 24.19%        |
| PROMPT A          | ZT-005    | 4.24%      | 28.33%        |
| PROMPT A          | ZT-006    | 16.40%     | 36.21%        |
| PROMPT A          | ZT-007    | 13.70%     | 34.04%        |
| PROMPT B          | ZT-001    | 9.83%      | 33.76%        |
| PROMPT B          | ZT-002    | 16.47%     | 31.03%        |
| PROMPT B          | ZT-003    | 8.67%      | 25.91%        |
| PROMPT B          | ZT-004    | 3.01%      | 25.17%        |
| PROMPT B          | ZT-005    | 12.50%     | 25.56%        |
| PROMPT B          | ZT-006    | 10.23%     | 30.04%        |
| PROMPT B          | ZT-007    | 14.04%     | 28.45%        |
| PROMPT C          | ZT-001    | 2.89%      | 29.60%        |
| PROMPT C          | ZT-002    | 10.36%     | 26.88%        |
| PROMPT C          | ZT-003    | 12.78%     | 23.43%        |
| PROMPT C          | ZT-004    | 2.71%      | 22.50%        |
| PROMPT C          | ZT-005    | 4.76%      | 22.54%        |
| PROMPT C          | ZT-006    | 4.06%      | 22.22%        |
| PROMPT C          | ZT-007    | 1.78%      | 23.08%        |
| PROMPT D          | ZT-001    | 8.43%      | 27.15%        |
| PROMPT D          | ZT-002    | 7.71%      | 27.41%        |
| PROMPT D          | ZT-003    | 0.99%      | 17.12%        |
| PROMPT D          | ZT-004    | 9.04%      | 25.81%        |
| PROMPT D          | ZT-005    | 2.91%      | 23.27%        |
| PROMPT D          | ZT-006    | 6.73%      | 26.25%        |
| PROMPT D          | ZT-007    | 12.44%     | 28.32%        |

### Model: Grok 4.20 Reasoning
| Prompt_Strategy   | Case_ID   | bleu_pct   | rouge_l_pct   |
|:------------------|:----------|:-----------|:--------------|
| PROMPT A          | ZT-001    | 19.04%     | 28.07%        |
| PROMPT A          | ZT-002    | 22.04%     | 26.26%        |
| PROMPT A          | ZT-003    | 17.44%     | 34.03%        |
| PROMPT A          | ZT-004    | 28.04%     | 36.84%        |
| PROMPT A          | ZT-005    | 14.86%     | 23.41%        |
| PROMPT A          | ZT-006    | 13.91%     | 34.29%        |
| PROMPT A          | ZT-007    | 10.05%     | 20.92%        |
| PROMPT B          | ZT-001    | 16.44%     | 28.12%        |
| PROMPT B          | ZT-002    | 23.40%     | 28.81%        |
| PROMPT B          | ZT-003    | 7.73%      | 27.14%        |
| PROMPT B          | ZT-004    | 18.10%     | 25.62%        |
| PROMPT B          | ZT-005    | 13.99%     | 20.53%        |
| PROMPT B          | ZT-006    | 6.16%      | 29.39%        |
| PROMPT B          | ZT-007    | 4.97%      | 21.69%        |
| PROMPT C          | ZT-001    | 5.26%      | 25.68%        |
| PROMPT C          | ZT-002    | 9.93%      | 21.57%        |
| PROMPT C          | ZT-003    | 6.05%      | 25.51%        |
| PROMPT C          | ZT-004    | 11.43%     | 23.53%        |
| PROMPT C          | ZT-005    | 10.78%     | 19.35%        |
| PROMPT C          | ZT-006    | 9.47%      | 27.03%        |
| PROMPT C          | ZT-007    | 0.97%      | 12.83%        |
| PROMPT D          | ZT-001    | 9.62%      | 31.41%        |
| PROMPT D          | ZT-002    | 9.01%      | 18.53%        |
| PROMPT D          | ZT-003    | 9.84%      | 21.92%        |
| PROMPT D          | ZT-004    | 16.07%     | 25.91%        |
| PROMPT D          | ZT-005    | 11.29%     | 24.48%        |
| PROMPT D          | ZT-006    | 12.66%     | 33.06%        |
| PROMPT D          | ZT-007    | 2.00%      | 14.16%        |
