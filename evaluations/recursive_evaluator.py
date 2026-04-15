import json
import os
import sys
import time
import csv
from datetime import datetime

# Add the parent directory to sys.path so we can import chatbot_engine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import chatbot_engine

def run_recursive_evaluation():
    """
    Runs a batch of queries from the ZOHO benchmark dataset through the 
    recursive learning pipeline and captures the results into a CSV.
    """
    dataset_path = "evaluations/zoho_benchmark_dataset.json"
    results_dir = "evaluations/results"
    csv_file = os.path.join(results_dir, "recursive_learning_report.csv")
    
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        
    print(f"\n" + "="*60)
    print(f"   ZOHO RECURSIVE LEARNING EVALUATION")
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"="*60)
    
    try:
        with open(dataset_path, 'r') as f:
            test_cases = json.load(f)
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return

    # Filter for technical cases (best for recursive testing)
    tech_cases = [tc for tc in test_cases if tc.get('expected_action') == "PROVIDE_SOLUTION"]
    print(f"Found {len(tech_cases)} technical cases to process.\n")

    user_context = {
        "user_id": "eval_user",
        "name": "Zoho Evaluator",
        "email": "zoho_eval@pcbapps.com"
    }

    headers = [
        "Timestamp", "ID", "Category", "Query", 
        "Iter1_C", "Iter1_F", "Iter1_A", "Iter1_Latency", "Iter1_Response",
        "Iter2_C", "Iter2_F", "Iter2_A", "Iter2_Latency", "Iter2_Response",
        "C_Improvement", "F_Improvement", "A_Improvement", "Total_Latency", "Status"
    ]

    results_to_log = []

    print(f"{'ID':<10} | {'Status':<12} | {'Progress'}")
    print("-" * 40)

    for i, tc in enumerate(tech_cases):
        query = tc['query']
        tc_id = tc.get('id', f"ZT-{i:03}")
        
        # Reset engine state for a clean test
        chatbot_engine.close_issue_session(user_context['email'], None)
        
        print(f"{tc_id:<10} | Processing... ", end="", flush=True)
        
        response = chatbot_engine.get_chatbot_response(
            user_message=query,
            history=[],
            user_context=user_context
        )
        
        # Extract metrics and data
        final_eval = response.get("eval_metrics", {})
        initial_eval = response.get("initial_eval", {})
        steps = response.get("recursive_steps", 1)
        latencies = response.get("iteration_latencies", {})
        responses = response.get("iteration_responses", {})
        
        # Clean responses for CSV
        def clean(r):
            if not r: return ""
            return r.replace("\n", " ").replace("\r", " ").strip()

        i1_resp = clean(responses.get(1, ""))
        i2_resp = clean(responses.get(2, ""))
        
        i1_lat = latencies.get(1, 0.0)
        i2_lat = latencies.get(2, 0.0)
        
        i1_c, i1_f, i1_a = initial_eval.get('correctness', 0), initial_eval.get('faithfulness', 0), initial_eval.get('actionability', 0)
        i2_c, i2_f, i2_a = final_eval.get('correctness', 0), final_eval.get('faithfulness', 0), final_eval.get('actionability', 0)
        
        status = "Improved" if steps > 1 else "Direct"
        print(f"[{status}]")
        
        results_to_log.append({
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ID": tc_id,
            "Category": tc.get('category', 'N/A'),
            "Query": clean(query),
            "Iter1_C": i1_c,
            "Iter1_F": i1_f,
            "Iter1_A": i1_a,
            "Iter1_Latency": f"{i1_lat:.2f}s",
            "Iter1_Response": i1_resp,
            "Iter2_C": i2_c if steps > 1 else "N/A",
            "Iter2_F": i2_f if steps > 1 else "N/A",
            "Iter2_A": i2_a if steps > 1 else "N/A",
            "Iter2_Latency": f"{i2_lat:.2f}s" if steps > 1 else "N/A",
            "Iter2_Response": i2_resp,
            "C_Improvement": (i2_c - i1_c) if steps > 1 else 0,
            "F_Improvement": (i2_f - i1_f) if steps > 1 else 0,
            "A_Improvement": (i2_a - i1_a) if steps > 1 else 0,
            "Total_Latency": f"{(i1_lat + i2_lat):.2f}s",
            "Status": status
        })

    # Write to CSV
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(results_to_log)

    print("\n" + "="*60)
    print(f"EVALUATION COMPLETE")
    print(f"CSV Report: {csv_file}")
    print("="*60)

if __name__ == "__main__":
    run_recursive_evaluation()
