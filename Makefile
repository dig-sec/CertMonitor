# Variables
VENV_DIR := .venv
PYTHON := python3
REQUIREMENTS := requirements.txt
APP := src/main.py

# Default target
.DEFAULT_GOAL := help

## help: Show this help message
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

## venv: Create a virtual environment
venv: $(VENV_DIR)/bin/activate
$(VENV_DIR)/bin/activate:
	$(PYTHON) -m venv $(VENV_DIR)

## install: Install dependencies into the virtual environment
install: venv
	$(VENV_DIR)/bin/pip install --upgrade pip
	$(VENV_DIR)/bin/pip install -r $(REQUIREMENTS)

## run: Run the app using virtual environment
run:
	$(VENV_DIR)/bin/python $(APP)

## docker-run: Run CertMonitor container with docker-compose
docker-run: ## Run the certmonitor container using docker-compose
	docker compose run --rm certmonitor

## docker-build: Build the certmonitor Docker container
docker-build: ## Build the certmonitor container
	docker compose build certmonitor

## clean: Remove the virtual environment and temp files
clean: ## Clean virtualenv and .pyc files
	rm -rf $(VENV_DIR)
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete

## test: Run basic test commands (placeholder)
test: ## Run test (placeholder)
	@echo "No tests defined yet!"
