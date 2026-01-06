.PHONY: setup lint test clean build help

# Default target
help:
	@echo "Available targets:"
	@echo "  setup    - Install development dependencies"
	@echo "  lint     - Run linters (ruff, black)"
	@echo "  test     - Run test suite"
	@echo "  clean    - Remove build artifacts"
	@echo "  build    - Build distribution packages"

# Setup development environment
setup:
	python -m pip install --upgrade pip
	pip install -e ".[dev]"
	@echo ""
	@echo "Setup complete. Don't forget to install Tesseract OCR:"
	@echo "  Ubuntu/Debian: sudo apt-get install tesseract-ocr"
	@echo "  macOS: brew install tesseract"

# Run linters
lint:
	@echo "Running Black..."
	black --check src/ tests/ || (echo "Run 'black src/ tests/' to fix" && exit 1)
	@echo "Running Ruff..."
	ruff check src/ tests/

# Format code
format:
	black src/ tests/
	ruff check --fix src/ tests/

# Run tests
test:
	pytest tests/ -v --tb=short

# Run tests with coverage
test-cov:
	pytest tests/ --cov=vision_connector --cov-report=term-missing --cov-report=html

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Build distribution packages
build: clean
	python -m build

# Check package before upload
check: build
	twine check dist/*

# Run type checking
typecheck:
	mypy src/vision_connector --ignore-missing-imports
