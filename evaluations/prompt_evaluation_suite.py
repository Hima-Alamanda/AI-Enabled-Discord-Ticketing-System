import json
import time
import pandas as pd
import os
import sys
import nltk
from datetime import datetime
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer

# Setup Paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.append(PROJECT_ROOT)

import oci_config
import oci_genai
import chatbot_engine

# --- 1. PROMPT DEFINITIONS ---

PROMPT_A = """You are "PCB Support AI", a Senior IT Support Engineer for PCB Apps.
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
"""

PROMPT_B_BALANCED = """You are "PCB Support AI", a Senior IT Support Engineer for PCB Apps.
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
"""

PROMPT_C_HIGH_EFFICIENCY = """You are "PCB Support AI", a Senior IT Support Engineer for PCB Apps.
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
"""

PROMPT_D_CAUTIOUS_DIAGNOSTIC = """You are "PCB Support AI", a Senior IT Support Engineer for PCB Apps.
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
"""

PROMPT_STRATEGIES = [
    {"name": "PROMPT A", "content": PROMPT_A},
    {"name": "PROMPT B", "content": PROMPT_B_BALANCED},
    {"name": "PROMPT C", "content": PROMPT_C_HIGH_EFFICIENCY},
    {"name": "PROMPT D", "content": PROMPT_D_CAUTIOUS_DIAGNOSTIC}
]

MODELS = [
    {"name": "Gemini 2.5 Pro", "id": "google.gemini-2.5-pro"},
    {"name": "Grok 4.20 Reasoning", "id": "xai.grok-4.20-reasoning"}
]

DATASET_FILE = os.path.join(CURRENT_DIR, "zoho_benchmark_dataset.json")

# --- 2. EVALUATION FUNCTIONS ---

JUDGE_SYSTEM_PROMPT = """You are an expert Technical QA Engineer specializing in AI Support systems.
Evaluate the AI's response against the user message, context, and ground truth.

Assign a score from 0 (Failure) to 5 (Excellent) for each metric:
- Correctness: Technically accurate and follows the 'Golden Answer'?
- Faithfulness: Grounded strictly in KB/Context? (No hallucinations)
- Actionability: Clear, easy, numbered steps provided?
- Format Adherence: Did it follow the requested style (Natural flow, NO section headers, correct bolding)?
- Ambiguity Handling: Did it correctly ask for info if the query was vague?
- Multimodal Quality: How well did it interpret visual state (if provided)?
- Escalation Logic: Correct decision (Solve vs. Create Ticket vs. Clarify)?
- Empathy & Tone: Professional, polite, and helpful?

Output ONLY a raw JSON dictionary:
{"correctness": int, "faithfulness": int, "actionability": int, "format_adherence": int, "ambiguity": int, "multimodal": int, "escalation": int, "empathy": int, "reasoning": "brief explanation"}
"""

def judge_response(query, response, context, ground_truth, expected_action):
    prompt = f"QUERY: {query}\nKB: {context}\nGROUND TRUTH: {ground_truth}\nEXPECTED ACTION: {expected_action}\nAI RESPONSE: {response}"
    original_id = oci_config.CHAT_MODEL_ID
    oci_config.CHAT_MODEL_ID = "google.gemini-2.5-flash"
    try:
        raw = oci_genai.get_chat_response(prompt, system_prompt=JUDGE_SYSTEM_PROMPT, temperature=0.1)
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match: return json.loads(match.group())
    except: return None
    finally: oci_config.CHAT_MODEL_ID = original_id
    return None

def calculate_bleu(ref, cand):
    smoothie = SmoothingFunction().method1
    return round(sentence_bleu([nltk.word_tokenize(ref.lower())], nltk.word_tokenize(cand.lower()), smoothing_function=smoothie), 4)

def calculate_rouge(ref, cand):
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    return round(scorer.score(ref, cand)['rougeL'].fmeasure, 4)

# --- 3. MASTER EVALUATION LOOP ---

def run_suite():
    if not os.path.exists(DATASET_FILE):
        print("Dataset missing.")
        return

    with open(DATASET_FILE, 'r') as f:
        dataset = json.load(f)

    all_results = []
    print(f"\n STARTING MASTER EVALUATION SUITE\n")

    for strategy in PROMPT_STRATEGIES:
        prompt_name = strategy["name"]
        prompt_content = strategy["content"]
        print(f"\n--- TESTING: {prompt_name} ---")

        for model in MODELS:
            model_name = model["name"]
            model_id = model["id"]
            oci_config.CHAT_MODEL_ID = model_id
            print(f"  > Model: {model_name}")

            for case in dataset:
                query = case["query"]
                print(f"    - Case {case['id']}...", end="", flush=True)

                start_t = time.time()
                try:
                    # 1. Get AI Response with Prompt Override
                    resp_data = chatbot_engine.get_chatbot_response(
                        user_message=query,
                        history=[],
                        user_context={"name": "Tester", "user_id": "eval_001", "email": "test@pcbapps.com"},
                        system_prompt_override=prompt_content
                    )
                    duration_ms = round((time.time() - start_t) * 1000, 0)
                    
                    content = resp_data.get("content", "")
                    sources = resp_data.get("sources", [])
                    kb_context = f"Sources: {sources}"

                    # 2. Score with Judge
                    scores = judge_response(query, content, kb_context, case["ground_truth"], case["expected_action"])
                    
                    # 3. Calculate Math Metrics
                    bleu = calculate_bleu(case["ground_truth"], content)
                    rouge = calculate_rouge(case["ground_truth"], content)

                    # 4. Usage Metrics
                    usage = oci_genai.get_total_usage()

                    # 5. Compile Row
                    result = {
                        "Prompt_Strategy": prompt_name,
                        "Model": model_name,
                        "Case_ID": case["id"],
                        "Query": query,
                        "Latency_MS": duration_ms,
                        "In_Tokens": usage.get("input_tokens", 0),
                        "Out_Tokens": usage.get("output_tokens", 0),
                        "Total_Tokens": usage.get("total_tokens", 0),
                        "BLEU_Score": bleu,
                        "ROUGE_L": rouge,
                        "Correctness": scores.get("correctness", 0) if scores else 0,
                        "Faithfulness": scores.get("faithfulness", 0) if scores else 0,
                        "Actionability": scores.get("actionability", 0) if scores else 0,
                        "Format_Adherence": scores.get("format_adherence", 0) if scores else 0,
                        "Ambiguity": scores.get("ambiguity", 0) if scores else 0,
                        "Multimodal": scores.get("multimodal", 0) if scores else 0,
                        "Escalation": scores.get("escalation", 0) if scores else 0,
                        "Empathy": scores.get("empathy", 0) if scores else 0,
                        "Judge_Reasoning": scores.get("reasoning", "") if scores else "Judge Failed",
                        "AI_Response": content,
                        "KB_Context_Used": kb_context
                    }
                    all_results.append(result)
                    print(" Done.")

                except Exception as e:
                    print(f" Failed: {e}")

    # Output Results
    df = pd.DataFrame(all_results)
    results_path = os.path.join(CURRENT_DIR, "results/prompt_comparison.csv")
    df.to_csv(results_path, index=False)
    print(f"\n SUCCESS: CSV Report saved to {results_path}")

    # --- 4. GENERATE MARKDOWN REPORT FOR MANAGEMENT ---
    summary_md_path = os.path.join(CURRENT_DIR, "results/PROMPT_REPORT.md")
    
    # Calculate Quality Stats
    quality_stats = df.groupby(['Prompt_Strategy', 'Model']).agg({
        'Correctness': 'mean',
        'Faithfulness': 'mean',
        'Actionability': 'mean',
        'Format_Adherence': 'mean',
        'Ambiguity': 'mean',
        'Multimodal': 'mean',
        'Escalation': 'mean',
        'Empathy': 'mean'
    }).reset_index().round(2)

    # Calculate Performance Stats
    perf_stats = df.groupby(['Prompt_Strategy', 'Model']).agg({
        'Latency_MS': lambda x: round(x.mean() / 1000, 2),
        'In_Tokens': 'mean',
        'Out_Tokens': 'mean',
        'Total_Tokens': 'mean'
    }).reset_index()
    perf_stats.columns = ['Prompt', 'Model', 'Avg Latency (s)', 'Input Tokens', 'Output Tokens', 'Total Tokens']

    # Calculate Math Accuracy Stats (as percentages)
    math_stats = df.groupby(['Prompt_Strategy', 'Model']).agg({
        'BLEU_Score': lambda x: f"{x.mean()*100:.2f}%",
        'ROUGE_L': lambda x: f"{x.mean()*100:.2f}%",
        'Latency_MS': lambda x: round(x.mean() / 1000, 4)
    }).reset_index()
    math_stats.columns = ['Prompt', 'Model', 'bleu_score', 'rouge_l_score', 'latency']

    with open(summary_md_path, 'w') as f:
        f.write("# Evaluation Report\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        f.write("\n## 1. Executive Summary\n")
        f.write("We have tested 4 distinct technical prompt strategies across Gemini and Grok models using 7 benchmark cases from Zoho.\n")
        
        f.write("\n### PROMPT Definitions\n")
        f.write("- **PROMPT A: Production:** The current live system prompt used in the AI engine bot.\n")
        f.write("- **PROMPT B: Balanced Expert:** Optimized for a polished, professional, and empathetic helpdesk experience.\n")
        f.write("- **PROMPT C: High-Efficiency:** Focused on pure technical resolution speed by removing all filler words.\n")
        f.write("- **PROMPT D: Cautious Diagnostic:** Prioritizes thorough investigation and root-cause mapping before suggesting a fix.\n")

        f.write("\n### Prompt Instructions (Technical Detail)\n")
        f.write("Below is the exact system instruction text used for each PROMPT strategy:\n\n")
        for strategy in PROMPT_STRATEGIES:
            f.write(f"#### {strategy['name']}\n")
            f.write("```text\n")
            f.write(strategy['content'])
            f.write("\n```\n\n")


        f.write("\n---\n")

        f.write("## 2. Quality Metrics (0-5 Scale)\n")
        f.write("Each model's response is scored by an independent AI Auditor based on this scale:\n\n")
        f.write("| Score | Rating | Description |\n")
        f.write("|:---:|:---|:---|\n")
        f.write("| **5** | **Excellent** | Fully correct, clear, well-structured, and follows all required rules |\n")
        f.write("| **4** | **Good** | Correct and helpful, with only minor issues in wording, tone, or formatting. |\n")
        f.write("| **3** | **Acceptable** | Mostly correct, but missing some details or clarity. |\n")
        f.write("| **1-2** | **Poor** | Contains important mistakes, unclear steps, or does not fully address the user’s issue. |\n")
        f.write("| **0** | **Failure** | Incorrect, misleading, made up facts, or failed to answer the query. |\n\n")

        f.write("### The 8 Quality Categories\n")
        f.write("1. **Correctness:** Whether the bot gives the right answer based on past resolved tickets or known support information.\n")
        f.write("2. **Faithfulness:** Whether the bot stays accurate and does not make up information.\n")
        f.write("3. **Actionability:** Whether the bot gives clear steps that the user can actually follow.\n")
        f.write("4. **Format Adherence:** Whether the bot follows the expected response structure or headings.\n")
        f.write("5. **Ambiguity:** Whether the bot asks for more details when the issue is unclear instead of guessing.\n")
        f.write("6. **Multimodal:** Whether the bot can correctly use information from attached images or screenshots.\n")
        f.write("7. **Escalation:** Whether the bot correctly decides to solve the issue itself or hand it over to a human technician.\n")
        f.write("8. **Empathy:** Whether the bot sounds professional, polite, and helpful.\n\n")
        
        f.write("### Quality Results (Avg)\n")
        f.write(quality_stats.to_markdown(index=False))

        f.write("\n\n## 3. Mathematical Accuracy (Alignment)\n")
        f.write("*   **BLEU Score (Precision):** Measures wording similarity to the expected support answer. Scale: 0-100% (Higher is closer alignment).\n")
        f.write("*   **ROUGE-L Score (Recall):** Measures coverage of expected important information. Scale: 0-100% (Higher is better coverage).\n\n")

        f.write("### Model Comparison (Avg %)\n")
        f.write(math_stats.to_markdown(index=False))

        f.write("\n## 4. Model Capacity (Context Window)\n")
        f.write("| Feature | xAI Grok 4.20 (Reasoning) | Google Gemini 2.5 Pro |\n")
        f.write("|:---|:---|:---|\n")
        f.write("| **Total Context Window** | **2,000,000 tokens** | **1,000,000 tokens** |\n")
        f.write("| **Max Output Tokens** | 30,000 tokens | ~65,535 tokens |\n\n")

        f.write("\n\n## 5. Performance & Efficiency\n")
        f.write("1. **Latency:** Time-to-reply in seconds (User Experience).\n")
        f.write("2. **Token Usage:** Computational volume (Input + Output). Directly dictates OCI operational costs.\n\n")
        
        f.write("### Performance & Cost Metrics (Avg)\n")
        f.write(perf_stats.round(2).to_markdown(index=False))

        f.write("\n\n## 6. Case-by-Case Breakdown (%)\n")
        for model in df['Model'].unique():
            f.write(f"\n### Model: {model}\n")
            model_df = df[df['Model'] == model].copy()
            model_df['bleu_pct'] = model_df['BLEU_Score'].apply(lambda x: f"{x*100:.2f}%")
            model_df['rouge_l_pct'] = model_df['ROUGE_L'].apply(lambda x: f"{x*100:.2f}%")
            f.write(model_df[['Prompt_Strategy', 'Case_ID', 'bleu_pct', 'rouge_l_pct']].to_markdown(index=False))
            f.write("\n")

    # Add Legend to CSV as technical notes
    with open(results_path, 'a') as csv_f:

        csv_f.write("Quality Scores: Scaled 0 to 5 (5 = Excellent; 0 = Failure)\n")
        csv_f.write("BLEU/ROUGE-L: Mathematical alignment (0.0 to 1.0; 1.0 = Perfect Word Match)\n")
        csv_f.write("Tokens: Volume of data units. Capacity: Gemini Pro (1M); Grok 4.20 (2M)\n")

    print(f"Executive summary saved to {summary_md_path}")

if __name__ == "__main__":
    run_suite()
