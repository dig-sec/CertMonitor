# Makefile

# Variables
VENV_DIR := venv
PYTHON := python3
REQUIREMENTS := requirements.txt

# Default target
.DEFAULT_GOAL := help

## help: Show this help message
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

## venv: Create a virtual environment
venv: $(VENV_DIR)/bin/activate
$(VENV_DIR)/bin/activate: 
	$(PYTHON) -m venv $(VENV_DIR)

## install: Install dependencies into the virtual environment
install: venv
	$(VENV_DIR)/bin/pip install --upgrade pip
	$(VENV_DIR)/bin/pip install -r $(REQUIREMENTS)

## run: Run the application
run: install
	$(VENV_DIR)/bin/python app.py

## lint: Run code linters (flake8)
lint: install
	$(VENV_DIR)/bin/flake8 .

## clean: Remove the virtual environment and other temporary files
clean:
	rm -rf $(VENV_DIR)
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete

## test: Run tests using pytest
test: install
	$(VENV_DIR)/bin/pytest

.PHONY: help venv install run lint clean test