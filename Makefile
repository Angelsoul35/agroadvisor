.PHONY: install test lint run demo clean

install:
	pip install -e ".[dev]"

test:
	pytest --cov=agroadvisor --cov-report=term-missing

lint:
	ruff check agroadvisor tests

run:
	uvicorn agroadvisor.main:app --reload --port 8000

demo:
	python -m agroadvisor.cli demo

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
