# AI-Enabled Intelligent Ticketing System
# VERSION: 1.0.0
# AUTHOR: Himanth

PYTHONEXE = python3
PIP       = pip3

.PHONY: help setup db-init rag-sync bot-run bot-log eval-run clean

help: ## Show implementations
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Install project dependencies and AI models
	$(PIP) install -r requirements.txt
	$(PYTHONEXE) -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

db-init: ## Initialize Oracle pool and register support agents
	$(PYTHONEXE) -c "import database; database.init_db(); import agent_manager; agent_manager.init_agents()"

rag-sync: ## Synchronize Vector Store with latest articles
	$(PYTHONEXE) -c "import rag_manager; rag_manager.load_documents_to_db()"

bot-run: ## Launch the live Discord AI-Assistant bot
	bash ./run_discord.sh

bot-log: ## Monitor real-time bot application logs
	tail -f app.log

eval-run: ## Generate AI Performance & Mathematical Reports
	$(PYTHONEXE) evaluations/model_comparison_v2.py
	$(PYTHONEXE) evaluations/quantitative_eval.py

clean: ## Wipe temporary cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -f app.log
