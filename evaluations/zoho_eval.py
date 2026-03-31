import os
import sys
import json
import time
import math
from dotenv import load_dotenv
load_dotenv()


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from database import get_connection, search_kb_vectors
from rag_manager import get_embed_model




TEST_CASES = [
    {
        "id": "ZT-001",
        "query": "I am getting an error message during end of month reporting when posting JE batches. Batch shows status Error.",
        "ticket_subject": "Error message end of month reporting",
        "ground_truth": "The batch had 1523 unposted entries. Support deleted the 1523 entries and reposted the batch. The batch posting error was resolved.",
        "source_hint": "zoho_ticket"
    },
    {
        "id": "ZT-002",
        "query": "I cannot access Zoho tickets for DC33 or JFK with my login. Getting access denied.",
        "ticket_subject": "zoho tickets access issue",
        "ground_truth": "User was unable to access DC33 or JFK tickets in Zoho. Support looked into the access permissions and resolved the login access issue.",
        "source_hint": "zoho_archive"
    },
    {
        "id": "ZT-003",
        "query": "There is an eligibility file issue. Retirees covered under HMO are still active on the eligibility file.",
        "ticket_subject": "Retirees covered under HMO - active on eligibility file",
        "ground_truth": "Retirees under HMO plan were incorrectly showing as active on the eligibility file. Support corrected the eligibility file records.",
        "source_hint": "zoho_archive"
    },
    {
        "id": "ZT-004",
        "query": "Address book issue - unable to add blank values for a field in the system.",
        "ticket_subject": "Address book- Unable to add blank values",
        "ground_truth": "The address book field was not accepting blank values. Support confirmed this is valid and fixed the field to allow blank as a valid value.",
        "source_hint": "zoho_ticket"
    },
    {
        "id": "ZT-005",
        "query": "We need to do a Daiwa fiscal year end close. Can you help with the process?",
        "ticket_subject": "Daiwa Fiscal Year-End Close",
        "ground_truth": "The Daiwa fiscal year-end close process was walked through with the support team. Steps and timing for the close were provided.",
        "source_hint": "zoho_archive"
    }
]


# ROUGE-L Score 

def rouge_l_score(reference: str, hypothesis: str) -> float:
    """Computes ROUGE-L F1 score between reference and hypothesis."""
    ref_tokens = reference.lower().split()
    hyp_tokens = hypothesis.lower().split()
    if not ref_tokens or not hyp_tokens:
        return 0.0
    # Longest Common Subsequence
    m, n = len(ref_tokens), len(hyp_tokens)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ref_tokens[i-1] == hyp_tokens[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    lcs = dp[m][n]
    precision = lcs / n if n > 0 else 0
    recall = lcs / m if m > 0 else 0
    if precision + recall == 0:
        return 0.0
    return round(2 * precision * recall / (precision + recall), 4)


# Keyword Overlap Score (simple relevance check)

def keyword_overlap(query: str, result_content: str) -> float:
    """Measures what % of query keywords appear in the result."""
    stopwords = {"i", "a", "an", "the", "is", "it", "in", "on", "at", "to",
                 "for", "of", "and", "or", "with", "my", "we", "can", "do",
                 "be", "are", "was", "have", "has", "had", "this", "that"}
    query_words = {w.lower().strip(".,?!") for w in query.split() if w.lower() not in stopwords}
    result_lower = result_content.lower()
    matched = sum(1 for w in query_words if w in result_lower)
    return round(matched / len(query_words), 4) if query_words else 0.0

# ─────────────────────────────────────────────
# Main Evaluation Runner
# ─────────────────────────────────────────────
def run_evaluation():
    model = get_embed_model()
    results = []
    
    print("=" * 65)
    print("  ZOHO TICKET RAG EVALUATION — 5 Real Ticket Test Cases")
    print("=" * 65)
    
    for tc in TEST_CASES:
        print(f"\n{'─'*65}")
        print(f"Test: {tc['id']} | {tc['query'][:60]}...")
        
        start = time.time()
        
        # Generate query vector
        query_vector = model.encode(tc["query"])
        
        # Search KB_VECTORS (top 3 results)
        hits = search_kb_vectors(query_vector, n_results=3)
        
        elapsed = round(time.time() - start, 2)
        
        if not hits:
            print("  No results found in KB_VECTORS!")
            results.append({
                "id": tc["id"], "query": tc["query"],
                "top_hit_title": "NONE", "top_hit_source": "NONE",
                "relevance_score": 0, "rouge_l": 0,
                "keyword_overlap": 0, "response_time_s": elapsed
            })
            continue
        
        top = hits[0]
        content = top["content"] if isinstance(top["content"], str) else top["content"].read()
        
        # Metrics
        kw_score = keyword_overlap(tc["query"], content)
        rl_score = rouge_l_score(tc["ground_truth"], content[:500])
        
        print(f"  Top Hit:  [{top['source']}] {top['title']}")
        print(f"  Distance: {round(top['distance'], 4)} (lower = more similar)")
        print(f"  Keyword Overlap: {kw_score*100:.1f}%")
        print(f"  ROUGE-L:  {rl_score}")
        print(f"  Response Time: {elapsed}s")
        print(f"\n  Ground Truth:  {tc['ground_truth'][:100]}...")
        print(f"  Bot Content:   {content[:200]}...")
        
        results.append({
            "id": tc["id"],
            "query": tc["query"],
            "expected_ticket": tc["ticket_subject"],
            "top_hit_title": top["title"],
            "top_hit_source": top["source"],
            "vector_distance": round(top["distance"], 4),
            "keyword_overlap_pct": round(kw_score * 100, 1),
            "rouge_l": rl_score,
            "response_time_s": elapsed,
            "all_hits": [{"title": h["title"], "source": h["source"], "distance": round(h["distance"], 4)} for h in hits]
        })
    

    # Summary Report
   
    print(f"\n{'='*65}")
    print("  EVALUATION SUMMARY")
    print(f"{'='*65}")
    
    avg_kw   = sum(r["keyword_overlap_pct"] for r in results) / len(results)
    avg_rl   = sum(r["rouge_l"] for r in results) / len(results)
    avg_time = sum(r["response_time_s"] for r in results) / len(results)
    avg_dist = sum(r["vector_distance"] for r in results) / len(results)
    
    print(f"  {'Metric':<30} {'Score'}")
    print(f"  {'─'*40}")
    print(f"  {'Avg Keyword Overlap':<30} {avg_kw:.1f}%")
    print(f"  {'Avg ROUGE-L':<30} {avg_rl:.4f}")
    print(f"  {'Avg Vector Distance':<30} {avg_dist:.4f}")
    print(f"  {'Avg Response Time':<30} {avg_time:.2f}s")
    print(f"{'='*65}\n")
    
    # Save JSON report
    report_path = os.path.join(os.path.dirname(__file__), "evaluations", "zoho_eval_results.json")
    with open(report_path, "w") as f:
        json.dump({
            "summary": {
                "avg_keyword_overlap_pct": round(avg_kw, 1),
                "avg_rouge_l": round(avg_rl, 4),
                "avg_vector_distance": round(avg_dist, 4),
                "avg_response_time_s": round(avg_time, 2)
            },
            "test_cases": results
        }, f, indent=2)
    print(f"Full report saved to: evaluations/zoho_eval_results.json")

if __name__ == "__main__":
    run_evaluation()
