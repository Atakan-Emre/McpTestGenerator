# QA-MCP developer and CI entry points.
#
# Every CI stage shells out to a target defined here, so the exact command a
# Jenkins agent runs can be reproduced locally with `make <target>`.

PYTHON       ?= python3
VENV         ?= .venv
BIN          := $(VENV)/bin
REPORTS      := reports

# Analysis targets exit non-zero on findings. CI needs the report file written
# first so it can be archived and fed to SonarQube, then decides whether to
# fail. `-` on the report-producing command keeps make going; the follow-up
# command re-runs the check to set the real exit status.
.PHONY: help venv install install-ci reports clean \
        lint format-check typecheck test security audit build sonar ci quality

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

venv: ## Create the virtual environment
	$(PYTHON) -m venv $(VENV)

install: venv ## Install the package with development dependencies
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev]"

install-ci: venv ## Install development and CI analysis dependencies
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev,ci]"

reports: ## Create the report output directory
	@mkdir -p $(REPORTS)

lint: reports ## Ruff lint, emitting a SonarQube-importable JSON report
	-$(BIN)/ruff check --output-format=json --output-file=$(REPORTS)/ruff.json src/ tests/
	$(BIN)/ruff check src/ tests/

format-check: ## Fail if any file is not formatted
	$(BIN)/ruff format --check src/ tests/

typecheck: reports ## MyPy static type check, with a report for SonarQube
	-$(BIN)/mypy src/qa_mcp --ignore-missing-imports > $(REPORTS)/mypy.txt
	@cat $(REPORTS)/mypy.txt
	$(BIN)/mypy src/qa_mcp --ignore-missing-imports

test: reports ## Run the test suite with JUnit and coverage reports
	$(BIN)/pytest tests/ \
		--junitxml=$(REPORTS)/junit.xml \
		--cov=qa_mcp \
		--cov-report=xml:$(REPORTS)/coverage.xml \
		--cov-report=html:$(REPORTS)/htmlcov \
		--cov-report=term-missing

security: reports ## Bandit security scan (report + gate on medium severity)
	-$(BIN)/bandit -r src/qa_mcp -f json -o $(REPORTS)/bandit.json
	$(BIN)/bandit -r src/qa_mcp -ll

audit: reports ## Check installed dependencies for known vulnerabilities
	-$(BIN)/pip-audit --format=json --output=$(REPORTS)/pip-audit.json
	$(BIN)/pip-audit

build: ## Build the sdist and wheel
	$(BIN)/python -m build

sonar: ## Run the SonarQube scanner (requires sonar-scanner on PATH)
	sonar-scanner -Dsonar.projectVersion=$$($(BIN)/python -c "import qa_mcp; print(qa_mcp.__version__)")

quality: lint format-check typecheck ## All static analysis

ci: quality test security ## Everything a CI build runs before packaging

clean: ## Remove build and report artifacts
	rm -rf $(REPORTS) dist build .pytest_cache .ruff_cache .mypy_cache .coverage
	find . -type d -name __pycache__ -not -path "./$(VENV)/*" -exec rm -rf {} +
