install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt

run:
	uvicorn promptforge.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=promptforge --cov-report=html

lint:
	ruff check promptforge/ tests/
	black --check promptforge/ tests/

format:
	black promptforge/ tests/
	ruff check --fix promptforge/ tests/

typecheck:
	mypy promptforge/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf .coverage htmlcov/ .mypy_cache/

all: format lint typecheck test
