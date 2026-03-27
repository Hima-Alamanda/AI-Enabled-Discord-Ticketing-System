# Model Evaluation Framework

This folder is dedicated to testing and comparing different LLM models (e.g., Google Gemini vs. xAI Grok) for the AI-Enabled Ticketing System.

## Components

1.  **`golden_dataset.json`**: A curated list of 20 realistic support scenarios with "Ground Truth" labels for Topic, Priority, and Intent.
2.  **`eval_runner.py`**: A script to automate the evaluation of multiple models against the golden dataset.
3.  **`results/`**: A directory where model outputs and accuracy scores are saved for managerial review.

## How to used

1.  **Define your Models**: Open `eval_runner.py` and ensure the API calls for both Gemini and Grok are correctly configured.
    *   *Note: Ensure you have the necessary API keys in your environment variables.*
2.  **Run Evaluation**:
    ```bash
    python evaluations/eval_runner.py
    ```
3.  **Review Results**: Check `evaluations/results/summary.csv` for a side-by-side comparison of accuracy and performance.

## Accuracy Metrics (Updated)

The system now automatically tracks professional OCI metrics:

1.  **Success Rate (%)**: The percentage of calls that returned a valid response without API errors.
2.  **Avg Latency (s)**: The average time taken by the model to process a query.
3.  **Faithfulness (%)**: Measured by an LLM-as-a-judge. It verifies that the model's response is grounded in the "Ground Truth" scenario and doesn't hallucinate.
4.  **Topic Accuracy**: Does the model correctly identify the department (HR, IT, etc.)?
5.  **Priority Accuracy**: Does the model assign the correct severity?

## How to use

1.  **Run Evaluation**:
    ```bash
    python evaluations/eval_runner.py
    ```
2.  **Review Results**: Check `evaluations/results/latest_evaluation.csv` for the detailed breakdown.
3.  **Analyze Performance**: Use the final Scorecard in your terminal to see if the model meets production standards.
