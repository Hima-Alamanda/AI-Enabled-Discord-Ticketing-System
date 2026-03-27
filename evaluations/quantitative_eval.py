import pandas as pd
import json
import os
import glob
import sys
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
DATASET_FILE = os.path.join(CURRENT_DIR, "benchmark_dataset.json")

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

def run_quantitative_analysis():
    print("\n" + "="*60)
    print(" QUANTITATIVE AI EVALUATION (BLEU & ROUGE) ")
    print("="*60)

    # 1. Find the latest comparison CSV
    csv_files = glob.glob(os.path.join(RESULTS_DIR, "comparison_*.csv"))
    if not csv_files:
        print("Error: No evaluation results found in 'results/'. Run model_comparison_v2.py first.")
        return

    latest_csv = max(csv_files, key=os.path.getctime)
    print(f"Loading latest results: {os.path.basename(latest_csv)}")
    df = pd.read_csv(latest_csv)

    # 2. Load Ground Truth from Dataset
    if not os.path.exists(DATASET_FILE):
        print(f"Error: Dataset {DATASET_FILE} not found.")
        return
        
    with open(DATASET_FILE, 'r') as f:
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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(RESULTS_DIR, f"math_report_{timestamp}.md")
    csv_out_path = os.path.join(RESULTS_DIR, f"quantitative_results_{timestamp}.csv")

    df.to_csv(csv_out_path, index=False)
    df.to_csv(os.path.join(RESULTS_DIR, "quantitative_latest.csv"), index=False)

    with open(report_path, "w") as f:
        f.write(f"# Quantitative Model Performance Report\n\n")
        f.write(f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Source Data:** {os.path.basename(latest_csv)}\n\n")
        
        f.write("## 1. Metric Definitions\n")
        f.write("- **BLEU (Bilingual Evaluation Understudy):** Measures n-gram overlap. (0-1 range, higher is closer to ground truth phrases).\n")
        f.write("- **ROUGE-L (Longest Common Subsequence):** Measures structural similarity and recall. (0-1 range, higher is more comprehensive).\n\n")

        f.write("## 2. Model Comparison (Averages)\n\n")
        f.write(summary.to_markdown() + "\n\n")

        f.write("## 3. Case-by-Case Mathematical Alignment\n\n")
        for model in df['model'].unique():
            f.write(f"### Model: {model}\n")
            temp_df = df[df['model'] == model]
            
            # Simple markdown table for cases
            subset = temp_df[['case_id', 'bleu_score', 'rouge_l_score']]
            f.write(subset.to_markdown(index=False) + "\n\n")

    print(f"\n[SUCCESS]: Quantitative report saved to: {report_path}")
    
    # Save a latest copy for git tracking
    latest_md_path = os.path.join(RESULTS_DIR, "math_report_latest.md")
    with open(latest_md_path, "w") as lf:
        with open(report_path, "r") as rf:
            lf.write(rf.read())
    print(f"[SUCCESS]: Detailed data saved to: {csv_out_path}")

if __name__ == "__main__":
    run_quantitative_analysis()
