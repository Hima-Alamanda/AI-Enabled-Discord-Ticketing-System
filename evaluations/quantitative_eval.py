import pandas as pd
import json
import os
import sys
import glob
import argparse
from datetime import datetime

# Try to import evaluation libraries, handle missing ones
try:
    import nltk
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
    from rouge_score import rouge_scorer
except ImportError:
    print("\n[ERROR]: Missing required libraries for quantitative evaluation.")
    print("Please run: pip install nltk rouge-score\n")
    sys.exit(1)

# Ensure NLTK data is available for tokenization
for resource in ['punkt', 'punkt_tab']:
    try:
        nltk.data.find(f'tokenizers/{resource}')
    except LookupError:
        nltk.download(resource, quiet=True)

# Setup Paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(CURRENT_DIR, "results")
DATASET_GENERIC = os.path.join(CURRENT_DIR, "benchmark_dataset.json")
DATASET_ZOHO    = os.path.join(CURRENT_DIR, "zoho_benchmark_dataset.json")

def calculate_bleu(reference, candidate):
    """Calculates BLEU-4 score with smoothing."""
    ref_tokens = nltk.word_tokenize(reference.lower())
    cand_tokens = nltk.word_tokenize(candidate.lower())
    
    # Using smoothing function to handle short sentences / cases with zero n-gram overlap
    smoothie = SmoothingFunction().method1
    score = sentence_bleu([ref_tokens], cand_tokens, smoothing_function=smoothie)
    return round(score, 4)

def calculate_rouge(reference, candidate):
    """Calculates ROUGE-L score (Longest Common Subsequence)."""
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    scores = scorer.score(reference, candidate)
    return round(scores['rougeL'].fmeasure, 4)

def run_quantitative_analysis(dataset_mode="generic"):
    dataset_file = DATASET_ZOHO if dataset_mode == "zoho" else DATASET_GENERIC
    report_label = "Zoho Tickets" if dataset_mode == "zoho" else "Generic Benchmark"
    
    print("\n" + "="*60)
    print(f" QUANTITATIVE AI EVALUATION (BLEU & ROUGE) ")
    print(f" Dataset: {report_label}")
    print("="*60)

    # 1. Find the latest comparison CSV
    csv_files = glob.glob(os.path.join(RESULTS_DIR, "comparison_*.csv"))
    if not csv_files:
        print("Error: No evaluation results found in 'results/'. Run model_comparison_v2.py first.")
        return

    latest_csv = max(csv_files, key=os.path.getctime)
    print(f"Loading latest results: {os.path.basename(latest_csv)}")
    df = pd.read_csv(latest_csv)

    # 2. Load Ground Truth from correct dataset
    if not os.path.exists(dataset_file):
        print(f"Error: Dataset {dataset_file} not found.")
        return
        
    with open(dataset_file, 'r') as f:
        dataset = json.load(f)
    
    # Create mapping: case_id -> ground_truth
    gt_map = {item['id']: item.get('ground_truth', '') for item in dataset}

    # 3. Calculate Metrics
    print("\nCalculating mathematical alignment scores...")
    bleu_scores = []
    rouge_l_scores = []

    for idx, row in df.iterrows():
        case_id = str(row['case_id'])
        response = str(row['response'])
        ground_truth = gt_map.get(case_id, "")

        if not ground_truth:
            bleu_scores.append(0.0)
            rouge_l_scores.append(0.0)
            continue

        bleu = calculate_bleu(ground_truth, response)
        rouge_l = calculate_rouge(ground_truth, response)

        bleu_scores.append(bleu)
        rouge_l_scores.append(rouge_l)

    df['bleu_score'] = bleu_scores
    df['rouge_l_score'] = rouge_l_scores

    # 4. Summary Table per Model
    summary = df.groupby('model').agg({
        'bleu_score': 'mean',
        'rouge_l_score': 'mean',
        'latency': 'mean'
    }).round(4)

    print("\nSummary Results (Averages):")
    print(summary)

    # 5. Save Quantitative Report
    csv_out_path = os.path.join(RESULTS_DIR, "quantitative_latest.csv")
    df.to_csv(csv_out_path, index=False)

    report_path = os.path.join(RESULTS_DIR, "math_report_latest.md")

    with open(report_path, "w") as f:
        f.write(f"# Quantitative Model Performance Report ({report_label})\n\n")
        f.write(f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Dataset:** {report_label}\n")
        f.write(f"**Source Data:** {os.path.basename(latest_csv)}\n\n")
        
        f.write("## 1. Mathematical Metric Definitions\n")
        f.write("*   **BLEU Score (Precision):** Measures how many phrases the bot used that match the reference exactly.\n")
        f.write("*   **ROUGE-L Score (Recall):** Measures how much of the structure of the summary was captured by the bot.\n\n")
        f.write("> **Note:** For support bots, scores between **10% and 30% are excellent**. Bots provide detailed, conversational answers, while the ground truth is usually a very short summary. A low percentage here just means the bot isn't a carbon-copy of the database, but can still be highly accurate.\n\n")

        f.write("## 2. Model Comparison (Avg %)\n\n")
        # Format the summary table for markdown
        display_summary = summary.copy()
        display_summary['bleu_score'] = (display_summary['bleu_score'] * 100).map('{:,.2f}%'.format)
        display_summary['rouge_l_score'] = (display_summary['rouge_l_score'] * 100).map('{:,.2f}%'.format)
        f.write(display_summary.to_markdown() + "\n\n")

        f.write("## 3. Case-by-Case (%) \n\n")
        for model in df['model'].unique():
            f.write(f"### Model: {model}\n")
            temp_df = df[df['model'] == model].copy()
            temp_df['bleu_pct'] = (temp_df['bleu_score'] * 100).map('{:,.2f}%'.format)
            temp_df['rouge_l_pct'] = (temp_df['rouge_l_score'] * 100).map('{:,.2f}%'.format)
            subset = temp_df[['case_id', 'bleu_pct', 'rouge_l_pct']]
            f.write(subset.to_markdown(index=False) + "\n\n")

    print(f"Results saved to: evaluations/results/")
    print(f"  - math_report_latest.md")
    print(f"  - quantitative_latest.csv")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run BLEU & ROUGE quantitative analysis")
    parser.add_argument(
        "--dataset",
        choices=["generic", "zoho"],
        default="generic",
        help="Dataset to use for ground truth: 'generic' or 'zoho'"
    )
    args = parser.parse_args()
    run_quantitative_analysis(dataset_mode=args.dataset)
