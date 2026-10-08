.PHONY: install test eval scan clean-corpus

install: ## engine + CLI, editable, with test tools (use a venv: python3 -m venv .venv && . .venv/bin/activate)
	python3 -m pip install -e ".[dev]"

test: ## lint, format check, tests
	ruff check . && ruff format --check . && python3 -m pytest -q

eval: ## red-team suite (gated) + zoning accuracy
	python3 eval/redteam/run.py --check && python3 eval/zoning/run.py

scan: ## try the CLI offline: make scan DOC=path/to/file.pdf
	lectern scan "$(DOC)" --no-llm

clean-corpus: ## remove generated eval corpora
	rm -rf eval/results/local
