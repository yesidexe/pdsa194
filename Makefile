.PHONY: install run test lint format reset test-votes

install:
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt -r requirements-dev.txt

run:
	./venv/bin/python -m src.main

test:
	./venv/bin/pytest tests/ -q --cov=src --cov-report=term-missing --cov-fail-under=80

lint:
	./venv/bin/ruff check src tests scripts

format:
	./venv/bin/ruff format src tests scripts

reset:
	./venv/bin/python scripts/reset_db.py

test-votes:
	./venv/bin/python scripts/cast_test_votes.py
