.PHONY: install sync lint format type test test-cov demo gold gold-mro clean

# `uv sync` is the single entrypoint for env + deps (editable install of `ehm`)
install sync:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check --fix .

type:
	uv run mypy src/ehm

test:
	uv run pytest

test-cov:
	uv run pytest --cov=ehm --cov-report=term-missing

# End-to-end vertical slice (synthetic data, offline)
demo:
	uv run python -m scripts.run_egt_demo

# Gold-label loop demo: run pipeline -> seed verdicts -> feedback report
gold:
	uv run python -m scripts.run_egt_demo
	uv run python -m scripts.adjudicate seed-demo
	uv run python -m scripts.adjudicate report

# Gold-label loop with real MRO ground truth: pipeline -> import findings -> report
gold-mro:
	uv run python -m scripts.run_egt_demo
	uv run python -m scripts.adjudicate import-mro tests/fixtures/mro_sample.jsonl
	uv run python -m scripts.adjudicate report

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache dist build htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.egg-info" -exec rm -rf {} +
