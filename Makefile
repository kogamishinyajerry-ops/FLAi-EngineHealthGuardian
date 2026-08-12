.PHONY: install sync lint format type test test-cov demo clean

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

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache dist build htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.egg-info" -exec rm -rf {} +
