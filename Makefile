# AI-Enabled Intelligent Ticketing System
# VERSION: 2.0.0


PYTHONEXE = python3
PIP       = pip3
LOAD_ENV  = from dotenv import load_dotenv; load_dotenv();

.PHONY: help venv setup db-init rag-sync bot-run bot-stop bot-status bot-log git-status git-log eval-run eval-suite eval-report eval-push recursive-eval zoho-eval health zoho-sync zoho-archive clean

help: ## Show implementation dashboard
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'


venv: ## Create the Python virtual environment (.venv)
	$(PYTHONEXE) -m venv .venv
	@echo ""
	@echo "Virtual environment created. Activate it with:"
	@echo "  source .venv/bin/activate   (macOS / Linux)"
	@echo "  .venv\Scripts\activate       (Windows)"
	@echo ""
	@echo "Then run: make setup"

setup: ## Install all dependencies and download required NLTK resources
	$(PIP) install -r requirements.txt
	$(PYTHONEXE) -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"


db-init: ## Initialize Oracle DB pool and seed 18 support agents (2 admin + 16 domain specialists)
	$(PYTHONEXE) -c "$(LOAD_ENV) import database; database.init_db(); import agent_manager; agent_manager.init_agents()"

rag-sync: ## Synchronize Vector Store with latest KB articles
	$(PYTHONEXE) -c "$(LOAD_ENV) import rag_manager; rag_manager.load_documents_to_db()"

health: ## Run system diagnostics for all 4 services (Oracle ADW, OCI GenAI, Vector Search, Discord)
	$(PYTHONEXE) health_manager.py


zoho-sync: ## Sync ACTIVE tickets from Zoho Desk and vectorize into KB
	$(PYTHONEXE) zoho_sync.py

zoho-archive: ## Sync ARCHIVED tickets from Zoho Desk and vectorize into KB
	$(PYTHONEXE) zoho_sync.py --archive


bot-run: ## Launch the live Discord AI-Assistant bot
	bash ./run_discord.sh

bot-stop: ## Stop the running Discord bot process
	@pkill -f discord_bot.py && echo "Bot stopped." || echo "Bot was not running."

bot-status: ## Check whether the Discord bot is currently running
	@pgrep -f discord_bot.py > /dev/null && echo "Bot Status: RUNNING" || echo "Bot Status: STOPPED"

bot-log: ## Monitor real-time bot application logs (Ctrl+C to exit)
	tail -f app.log


git-status: ## Show modified files and development progress
	git status --short

git-log: ## Show the 10 most recent implementation commits
	git log --oneline -n 10


eval-run: ## Run AI Performance & Mathematical Reports (model comparison + quantitative metrics)
	$(PYTHONEXE) evaluations/model_comparison_v2.py
	$(PYTHONEXE) evaluations/quantitative_eval.py

eval-suite: ## Run Comprehensive Prompt Engineering Benchmarking (4 Strategies)
	$(PYTHONEXE) evaluations/prompt_evaluation_suite.py

eval-report: ## Generate Executive Excel Performance Report from latest results
	$(PYTHONEXE) evaluations/generate_excel_report.py

recursive-eval: ## Run Recursive Learning Loop Evaluation (Initial vs Final response quality)
	$(PYTHONEXE) evaluations/recursive_evaluator.py

zoho-eval: ## Run RAG Vector Search Accuracy Evaluation (ROUGE-L / Keyword Overlap)
	$(PYTHONEXE) evaluations/zoho_eval.py

eval-push: eval-run eval-suite eval-report ## Run all benchmarks and push LATEST reports (MD & Excel) to GitHub
	@echo "Staging latest reports..."
	@git add evaluations/results/*latest*
	@git add evaluations/results/PROMPT_REPORT.md
	@git add evaluations/results/EXECUTIVE_PERFORMANCE_REPORT_LATEST.xlsx
	@git add evaluations/results/recursive_learning_report.csv
	@git commit -m "docs: automatic evaluation update $$(date +'%Y-%m-%d %H:%M')" || echo "No changes to commit."
	@git push origin main


clean: ## Wipe temporary cache items (pycache, logs, generated charts)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -f app.log
	rm -f static/charts/*.png static/charts/*.jpg
	@echo "Cleaned: pycache, app.log, static/charts"
