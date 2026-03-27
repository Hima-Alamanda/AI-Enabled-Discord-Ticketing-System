import json
import time
import pandas as pd
import os
import sys
from datetime import datetime

# Setup Paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.append(PROJECT_ROOT)

import oci_config
import oci_genai
import chatbot_engine

# 1. MODELS TO EVALUATE
MODELS = [
    {"name": "Gemini 2.5 Pro", "id": "google.gemini-2.5-pro"},
    {"name": "Grok 4.20 Reasoning", "id": "xai.grok-4.20-reasoning"}
]

# 2. EVALUATION DATASET
DATASET_FILE = os.path.join(CURRENT_DIR, "benchmark_dataset.json")

# 3. JUDGE PROMPT
JUDGE_SYSTEM_PROMPT = """You are an expert Technical QA Engineer specializing in AI Support systems.
Evaluate the AI's response against the user message, context, ground truth, and any attachment info.

Assign a score from 0 (Failure) to 5 (Excellent) for each metric:
- Correctness: Technically accurate and follows the 'Golden Answer'?
- Faithfulness: Grounded strictly in KB/Context? (No hallucinations)
- Actionability: Clear, easy, numbered steps provided?
- Format Adherence: Did it use the exact four headers in order: ### **Issue Analysis**, ### **Cause**, ### **Resolution Steps**, ### **Next Steps**?
- Ambiguity Handling: Did it correctly ask for info if the query was vague?
- Multimodal Quality: (If image info is provided) How well did it interpret the OCR/UI state?
- Escalation Logic: Correct decision (Solve vs. Create Ticket vs. Clarify)?
- Empathy & Tone: Professional, empathetic, and de-escalating in high-stress cases?

Output ONLY a raw JSON dictionary:
{
  "correctness": int,
  "faithfulness": int,
  "actionability": int,
  "format_adherence": int,
  "ambiguity": int,
  "multimodal": int,
  "escalation": int,
  "empathy": int,
  "reasoning": "brief explanation"
}
"""

def judge_response(query, response, context, ground_truth, expected_action, attachment_info="None"):
    """Calls the LLM-as-a-judge to score the response."""
    # We use Gemini as a judge regardless of which model provided the response
    prompt = f"""
USER QUERY: {query}
ATTACHMENT INFO: {attachment_info}
RETRIEVED KB CONTEXT: {context}
GROUND TRUTH: {ground_truth}
EXPECTED ACTION: {expected_action}
AI RESPONSE: {response}.
    """
    
    # Use Gemini 2.5 Flash as objective "Auditor" to reduce Self-Preference Bias
    original_id = oci_config.CHAT_MODEL_ID
    oci_config.CHAT_MODEL_ID = "google.gemini-2.5-flash"
    
    usage_data = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    try:
        raw, usage = oci_genai.get_chat_response(prompt, system_prompt=JUDGE_SYSTEM_PROMPT, temperature=0.1, include_usage=True)
        usage_data = usage
        # Parse JSON from response
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group()), usage_data
        return None, usage_data
    except Exception as e:
        print(f"   [JUDGE ERROR]: {e}")
        return None, usage_data
    finally:
        oci_config.CHAT_MODEL_ID = original_id

def run_evaluation():
    print("\n" + "="*60)
    print(" COMPLETE ENTERPRISE AI EVALUATION FRAMEWORK ")
    print("="*60)

    if not os.path.exists(DATASET_FILE):
        print(f"Error: Dataset not found at {DATASET_FILE}")
        return

    with open(DATASET_FILE, 'r') as f:
        dataset = json.load(f)

    all_results = []
    
    for model_meta in MODELS:
        model_name = model_meta["name"]
        model_id = model_meta["id"]
        
        print(f"\n EVALUATING MODEL: {model_name} ({model_id})")
        
        # Override model ID in config
        oci_config.CHAT_MODEL_ID = model_id
        
        for i, case in enumerate(dataset, 1):
            query = case["query"]
            print(f"   [{i}/{len(dataset)}] Case ID: {case['id']} | Query: {query[:50]}...")
            
            start_t = time.time()
            try:
                # Call the real bot engine
                resp_data = chatbot_engine.get_chatbot_response(
                    user_message=query,
                    history=[], # Start fresh for logic eval
                    user_context={"name": "Tester", "user_id": "eval_001", "email": "test@pcbapps.com"}
                )
                duration = round(time.time() - start_t, 2)
                
                content = resp_data.get("content", "NO CONTENT")
                sources = resp_data.get("sources", [])
                
                # Retrieve the KB context used for this query (for the judge)
                context_summary = f"Sources: {sources}"
                
                # SCORE with Judge
                ground_truth = case.get("ground_truth", "N/A")
                expected_action = case.get("expected_action", "PROVIDE_SOLUTION")
                attachment_info = case.get("attachment_info", "None")

                scores, judge_usage = judge_response(query, content, context_summary, ground_truth, expected_action, attachment_info)
                
                if scores:
                    scores["model"] = model_name
                    scores["case_id"] = case["id"]
                    scores["query"] = query
                    scores["response"] = content  # Keep the actual bot output
                    scores["latency"] = duration
                    
                    # Store Token Usage (Fetched from global tracking in oci_genai)
                    model_usage = oci_genai.get_total_usage()
                    scores["input_tokens"] = model_usage.get("input_tokens", 0)
                    scores["output_tokens"] = model_usage.get("output_tokens", 0)
                    scores["total_tokens"] = model_usage.get("total_tokens", 0)
                    
                    scores["judge_input_tokens"] = judge_usage.get("input_tokens", 0)
                    scores["judge_output_tokens"] = judge_usage.get("output_tokens", 0)
                    scores["judge_total_tokens"] = judge_usage.get("total_tokens", 0)

                    all_results.append(scores)
                    
                    agg_score = scores['correctness'] + scores['faithfulness'] + scores['actionability'] + \
                                scores['format_adherence'] + scores['ambiguity'] + scores['multimodal'] + \
                                scores['escalation'] + scores['empathy']
                    print(f"      -> Aggregated Score: {agg_score}/40 | Latency: {duration}s | Tokens: {scores['total_tokens']}")
                else:
                    print("      -> [ERROR]: Judge failed to score this response.")
                    
            except Exception as e:
                print(f"      -> [ERROR]: Evaluation failed: {e}")

    # Process and Save Results
    if not all_results:
        print("\nNo results collected. Check connectivity/API keys.")
        return
        
    df = pd.DataFrame(all_results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_json = os.path.join(CURRENT_DIR, f"results/comparison_{timestamp}.json")
    results_csv = os.path.join(CURRENT_DIR, f"results/comparison_{timestamp}.csv")
    
    if not os.path.exists(os.path.join(CURRENT_DIR, "results")):
        os.makedirs(os.path.join(CURRENT_DIR, "results"))
        
    df.to_csv(results_csv, index=False)
    df.to_csv(os.path.join(CURRENT_DIR, "results/comparison_latest.csv"), index=False) # Keep latest for clean git tracking
    
    # Final Table per Model
    summary = df.groupby('model').agg({
        'correctness': 'mean',
        'faithfulness': 'mean',
        'actionability': 'mean',
        'format_adherence': 'mean',
        'ambiguity': 'mean',
        'multimodal': 'mean',
        'escalation': 'mean',
        'empathy': 'mean',
        'latency': 'mean',
        'input_tokens': 'mean',
        'output_tokens': 'mean',
        'total_tokens': 'mean'
    }).round(2)
    
    print("\n" + "="*60)
    print(" FINAL EVALUATION SUMMARY (Averages 0-5)")
    print("="*60)
    print(summary)
    print("="*60)
    print(f"\nDetailed CSV: {results_csv}")
    
    # Generate MD Report
    report_path = os.path.join(CURRENT_DIR, f"results/report_{timestamp}.md")
    with open(report_path, "w") as rf:
        rf.write(f"# Enterprise AI Evaluation Report: Gemini vs. Grok\n\n")
        rf.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        rf.write("## 1. Quality Scores (Avg 0-5)\n\n")
        quality_metrics = summary.drop(['latency', 'input_tokens', 'output_tokens', 'total_tokens'], axis=1)
        rf.write(quality_metrics.to_markdown() + "\n\n")
        
        rf.write("## 2. Performance & Cost Metrics (Avg)\n\n")
        perf_metrics = summary[['latency', 'input_tokens', 'output_tokens', 'total_tokens']]
        perf_metrics.columns = ['Avg Latency (s)', 'Input Tokens', 'Output Tokens', 'Total Tokens']
        rf.write(perf_metrics.to_markdown() + "\n\n")
        
        rf.write("## 3. Key Insights\n\n")
        
        # Simple Insight Generation
        for model in summary.index:
            m_data = summary.loc[model]
            metrics_only = m_data.drop(['latency', 'input_tokens', 'output_tokens', 'total_tokens'])
            strongest = metrics_only.idxmax()
            weakest = metrics_only.idxmin()
            rf.write(f"### {model}\n")
            rf.write(f"- **Strength:** {strongest.capitalize()} ({m_data[strongest]})\n")
            rf.write(f"- **Potential Area for Improvement:** {weakest.capitalize()} ({m_data[weakest]})\n")
            rf.write(f"- **Avg Turnaround:** {m_data['latency']}s\n")
            rf.write(f"- **Avg Tokens:** {int(m_data['total_tokens'])} (Input: {int(m_data['input_tokens'])}, Output: {int(m_data['output_tokens'])})\n\n")
            
        rf.write("## 4. Case-by-Case Breakdown\n\n")
        for model in df['model'].unique():
            rf.write(f"### Model: {model}\n")
            temp_df = df[df['model'] == model]
            for _, r in temp_df.iterrows():
                total_score = r['correctness'] + r['faithfulness'] + r['actionability'] + \
                              r['format_adherence'] + r['ambiguity'] + r['multimodal'] + \
                              r['escalation'] + r['empathy']
                
                rf.write(f"#### Case {r['case_id']}: {r['query'][:60]}...\n")
                rf.write(f"- **Total Score:** {total_score}/40\n")
                rf.write(f"- **Latency:** {r['latency']}s | **Tokens:** {int(r['total_tokens'])}\n")
                rf.write(f"- **Judge Reasoning:** *{r['reasoning']}*\n")
                rf.write(f"\n**AI Response:**\n```\n{r['response']}\n```\n")
                rf.write("---\n\n")
            rf.write("\n")

    print(f"Full Report: {report_path}")

    # Also save as latest for git
    latest_path = os.path.join(CURRENT_DIR, "results/report_latest.md")
    with open(latest_path, "w") as lf:
        with open(report_path, "r") as rf:
            lf.write(rf.read())

if __name__ == "__main__":
    run_evaluation()
