# Vision Connector

**Non-invasive industrial data capture using computer vision**

[![CI](https://github.com/GoodAI-Global/vision-connector/actions/workflows/ci.yml/badge.svg)](https://github.com/GoodAI-Global/vision-connector/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/vision-connector.svg)](https://badge.fury.io/py/vision-connector)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## What It Is

Vision Connector extracts data from industrial displays using computer vision and OCR:

- **HMI Screen Reader** - Extract values from SCADA/HMI screen captures
- **Gauge Reader** - Read analog gauges via needle detection
- **Display Reader** - Process 7-segment and LED displays
- **Multiple Outputs** - CSV, MQTT, Webhook

**Use case**: You have a legacy system with no API access. Point a camera at the screen, define regions of interest, and extract the data programmatically.

## What It Isn't

- **Not a real-time video processing system** - Designed for periodic snapshots, not 60fps streams
- **Not a general-purpose OCR tool** - Optimized for industrial displays, not documents
- **Not production-hardened yet** - v0.1.0 is functional but needs battle-testing
- **Not a screen capture tool** - You provide the images; it extracts the data

## Status

**v0.1.0** - Early release. Core functionality works. Test coverage exists. Not yet battle-tested in production environments.

| Component | Status |
|-----------|--------|
| HMI Reader | Functional |
| Gauge Reader | Functional |
| Display Reader | Functional |
| MQTT Output | Functional |
| Webhook Output | Functional |
| CSV Output | Functional |
| Test Suite | 146 tests passing |

---

## Quickstart (< 5 minutes)

### 1. Install Tesseract OCR

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows: https://github.com/UB-Mannheim/tesseract/wiki
```

### 2. Install vision-connector

```bash
pip install vision-connector

# Or from source
git clone https://github.com/goodai/vision-connector.git
cd vision-connector
pip install -e .
```

### 3. Extract data from an image

```python
from vision_connector import HMIReader

reader = HMIReader()
result = reader.read_image(
    "screenshot.png",
    regions={
        "temperature": {"x": 100, "y": 200, "w": 80, "h": 30},
        "pressure": {"x": 100, "y": 250, "w": 80, "h": 30},
    }
)
print(result)
# {"temperature": "185.5", "pressure": "42.3"}
```

### 4. Run the demo

```bash
python demo_run.py
```

---

## Installation Options

```bash
# Core only
pip install vision-connector

# With Prometheus metrics
pip install vision-connector[metrics]

# With YAML config support
pip install vision-connector[config]

# All optional dependencies
pip install vision-connector[all]
```

---

## Features

### HMI Screen Reader

```python
from vision_connector import HMIReader

reader = HMIReader(config="config.json")  # Or define regions inline
result = reader.read_image("hmi_screenshot.png")
```

### Gauge Reader

```python
from vision_connector import GaugeReader

reader = GaugeReader()
result = reader.read_analog_gauge("gauge.png", min_value=0, max_value=100)
# {"value": 67.5, "confidence": 0.92}
```

### Display Reader

```python
from vision_connector import DisplayReader

reader = DisplayReader()
result = reader.read_display("display.png", display_type="7segment")
# {"value": 1234.5, "confidence": 0.95}
```

### Output Options

```python
from vision_connector.outputs import CSVWriter, MQTTOutput, WebhookOutput

# CSV
csv = CSVWriter("readings.csv")
csv.append({"temperature": 185.5})

# MQTT
mqtt = MQTTOutput("localhost:1883", topic="plant/readings")
mqtt.connect()
mqtt.publish({"temperature": 185.5})

# Webhook
webhook = WebhookOutput("https://api.example.com/readings")
webhook.send({"temperature": 185.5})
```

---

## Enterprise Features (v0.1.0)

- **Structured Logging** - JSON/text formatters, operation tracing
- **Prometheus Metrics** - Optional observability (`pip install vision-connector[metrics]`)
- **Configuration Management** - YAML files + environment variable overrides
- **Custom Exceptions** - Typed error hierarchy for programmatic handling
- **Resilience Patterns** - Retry with backoff, circuit breaker, timeouts

---

## Development

```bash
# Setup
make setup

# Run tests
make test

# Lint
make lint

# Clean
make clean
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

---

## Documentation

- [CHANGELOG.md](CHANGELOG.md) - Version history
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development setup
- [SECURITY.md](SECURITY.md) - Security policy
- [RELEASING.md](RELEASING.md) - Release process

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## About

Built by [Good AI](https://goodai.com) - Enterprise AI Consultancy.
