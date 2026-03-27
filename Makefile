# AI-Enabled Intelligent Ticketing System
# VERSION: 1.0.0
# AUTHOR: Himanth

PYTHONEXE = python3
PIP       = pip3
LOAD_ENV  = from dotenv import load_dotenv; load_dotenv();

.PHONY: help setup db-init rag-sync bot-run bot-status bot-log git-status git-log eval-run clean

help: ## Show implementation dashboard
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'


setup: ## Install dependencies and download required NLTK resources
	$(PIP) install -r requirements.txt
	$(PYTHONEXE) -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

db-init: ## Initialize Oracle pool and register support agents
	$(PYTHONEXE) -c "$(LOAD_ENV) import database; database.init_db(); import agent_manager; agent_manager.init_agents()"

rag-sync: ## Synchronize Vector Store with latest articles
	$(PYTHONEXE) -c "$(LOAD_ENV) import rag_manager; rag_manager.load_documents_to_db()"


bot-run: ## Launch the live Discord AI-Assistant bot
	bash ./run_discord.sh

bot-status: ## Check whether the Discord bot is running
	@pgrep -f discord_bot.py > /dev/null && echo "Bot Status: RUNNING" || echo "Bot Status: STOPPED"

bot-log: ## Monitor real-time bot application logs
	tail -f app.log


git-status: ## Show modified files and development progress
	git status --short

git-log: ## Show the 10 most recent implementation commits
	git log --oneline -n 10


eval-run: ## Generate AI Performance & Mathematical Reports
	$(PYTHONEXE) evaluations/model_comparison_v2.py
	$(PYTHONEXE) evaluations/quantitative_eval.py

eval-push: eval-run ## Run & Automatically push LATEST reports to GitHub
	@echo "Staging latest reports"
	@git add evaluations/results/*latest*
	@git commit -m "docs: automatic evaluation update $$(date +'%Y-%m-%d %H:%M')" || echo "No changes to commit."
	@git push origin main

clean: ## Wipe temporary cache items
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -f app.log
