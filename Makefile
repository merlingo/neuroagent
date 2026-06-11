.PHONY: dev test lint format typecheck

dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest

lint:
	ruff check app tests scripts

format:
	ruff format app tests scripts

typecheck:
	mypy app
