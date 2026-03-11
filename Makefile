.PHONY: install test clean run

install:
	pip install -e .

test:
	pytest

clean:
	rm -rf output/ logs/ .pytest_cache/ *.egg-info/ __pycache__/
	find . -type d -name __pycache__ -exec rm -r {} +

run:
	pv-optimizer