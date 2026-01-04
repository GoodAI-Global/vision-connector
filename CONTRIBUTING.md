# Contributing to Vision Connector

Thank you for your interest in contributing to vision-connector!

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/goodai/vision-connector.git
cd vision-connector
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

4. Install Tesseract OCR:
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from https://github.com/UB-Mannheim/tesseract/wiki
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=vision_connector

# Run specific test file
pytest tests/test_hmi_reader.py
```

## Code Style

We use Black for code formatting:

```bash
# Format code
black src/ tests/

# Check formatting
black --check src/ tests/
```

## Type Checking

We use mypy for type checking:

```bash
mypy src/vision_connector
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Format code with Black
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## Commit Messages

- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Remove, etc.)
- Keep the first line under 50 characters
- Add details in the body if needed

## Reporting Issues

When reporting issues, please include:

- Python version
- Operating system
- Tesseract version (`tesseract --version`)
- Steps to reproduce
- Expected vs actual behavior
- Error messages and tracebacks

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
