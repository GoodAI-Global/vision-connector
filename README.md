# Vision Connector

**Non-invasive industrial data capture using computer vision**

*By Good AI - Premium Enterprise AI Consultancy*

---

## The Problem

In industrial environments, critical operational data is often locked away:

- **PLCs are locked** — Proprietary protocols, vendor lock-in, security restrictions
- **ERPs are ancient** — No APIs, no integrations, COBOL from the 80s
- **IT won't give access** — Months of approval processes, security reviews, budget constraints

Meanwhile, operators stare at screens full of valuable data every day.

## The Solution

**Point a camera at the screen operators already look at.**

Vision Connector extracts data from HMI screens, gauges, and digital displays using computer vision and OCR — without touching the underlying systems.

This is **non-invasive intelligence**: bypass legacy constraints without system integration.

---

## Why Non-Invasive?

| Traditional Integration | Vision Connector |
|------------------------|------------------|
| Months of planning | Deploy in hours |
| IT approval required | No system access needed |
| Risk of downtime | Zero production impact |
| Vendor dependencies | Works with any display |
| Expensive integrations | Low-cost cameras |

**Augment first, automate later.** Digitize manual processes before committing to expensive automation projects.

---

## Quick Start

### Installation

```bash
# Install the library
pip install vision-connector

# Or install from source
git clone https://github.com/goodai/vision-connector.git
cd vision-connector
pip install -e .
```

### System Requirements

Tesseract OCR must be installed:

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

### Run the Demo

```bash
python demo_run.py
```

### Basic Usage

```python
from vision_connector import HMIReader

# Read values from an HMI screen
reader = HMIReader()
result = reader.read_image(
    "screenshot.png",
    regions={
        "temperature": {"x": 100, "y": 200, "w": 80, "h": 30},
        "pressure": {"x": 100, "y": 250, "w": 80, "h": 30},
        "status": {"x": 300, "y": 100, "w": 100, "h": 40}
    }
)

print(result)
# {"temperature": "185.5", "pressure": "42.3", "status": "RUNNING"}
```

---

## Features

### HMI Screen Reader

Extract data from industrial HMI screens and SCADA displays.

```python
from vision_connector import HMIReader

# Using config file
reader = HMIReader(config="config.json")
result = reader.read_image("hmi_screenshot.png")

# Or define regions inline
reader = HMIReader()
result = reader.read_image(
    "screenshot.png",
    regions={
        "temperature": {"x": 100, "y": 200, "w": 80, "h": 30, "type": "number"},
        "status": {"x": 300, "y": 100, "w": 100, "h": 40, "type": "text"}
    }
)
```

### Gauge Reader

Read analog gauges with needle detection.

```python
from vision_connector import GaugeReader

reader = GaugeReader()
result = reader.read_analog_gauge(
    "gauge.png",
    min_value=0,
    max_value=100,
    unit="PSI"
)
# {"value": 67.5, "unit": "PSI", "confidence": 0.92}
```

### Display Reader

Read 7-segment and LED digital displays.

```python
from vision_connector import DisplayReader

reader = DisplayReader()
result = reader.read_display(
    "display.png",
    display_type="7segment"
)
# {"value": 1234.5, "raw_text": "1234.5", "confidence": 0.95}
```

### OCR Processor

Direct OCR access for custom applications.

```python
from vision_connector.processors import OCRProcessor

ocr = OCRProcessor()
text = ocr.extract_text(image, region={"x": 0, "y": 0, "w": 100, "h": 50})
numbers = ocr.extract_numbers(image)
```

---

## Output Options

### CSV Logging

```python
from vision_connector.outputs import CSVWriter

csv = CSVWriter("readings.csv")
csv.append({"temperature": 185.5, "pressure": 42.3})
```

### MQTT Streaming

```python
from vision_connector.outputs import MQTTOutput

mqtt = MQTTOutput("localhost:1883", topic="plant/line1/readings")
mqtt.connect()
mqtt.publish({"temperature": 185.5, "pressure": 42.3})
mqtt.disconnect()
```

### Webhook

```python
from vision_connector.outputs import WebhookOutput

webhook = WebhookOutput("https://api.example.com/readings")
webhook.send({"temperature": 185.5, "pressure": 42.3})
```

---

## Configuration

### Config File Format

```json
{
  "capture": {
    "source": "image",
    "path": "sample_images/hmi_screen.png"
  },
  "regions": {
    "temperature": {"x": 100, "y": 200, "w": 80, "h": 30, "type": "number"},
    "pressure": {"x": 100, "y": 250, "w": 80, "h": 30, "type": "number"},
    "status": {"x": 300, "y": 100, "w": 100, "h": 40, "type": "text"}
  },
  "output": {
    "type": "csv",
    "path": "output/readings.csv"
  }
}
```

### Region Types

- `number` — Extract numeric values (integers and decimals)
- `text` — Extract text strings
- `auto` — Automatically detect content type

---

## Headless Operation

Vision Connector is designed to work in headless environments (Docker, CI, servers).

```python
# ROI can be specified via config or parameters - no GUI required
reader = HMIReader(config="config.json")
result = reader.read_image("screenshot.png")

# Interactive selection only when display is available
import os
if os.environ.get("DISPLAY"):
    roi = reader.select_roi_interactive(image)
else:
    # Use config-based regions
    pass
```

---

## Capture Options

### From Image File

```python
from vision_connector.capture import ImageCapture

cap = ImageCapture("screenshot.png")
img = cap.read()
```

### From Camera

```python
from vision_connector.capture import CameraCapture

# USB camera
cam = CameraCapture(0)
frame = cam.read()

# IP camera
cam = CameraCapture("rtsp://192.168.1.100:554/stream")
for frame in cam.stream():
    process(frame)
```

---

## Calibration

### ROI Selector

Define regions of interest programmatically or interactively.

```python
from vision_connector.calibration import ROISelector

selector = ROISelector()

# Programmatic (works headless)
selector.add_region("temperature", x=100, y=200, w=80, h=30)
selector.add_region("pressure", x=100, y=250, w=80, h=30)
selector.save_config("config.json")

# Interactive (requires display)
if os.environ.get("DISPLAY"):
    selector.select_interactive("screenshot.png")
```

---

## Examples

See the `examples/` directory for complete working examples:

- `read_hmi_from_image.py` — Read HMI screen from image file
- `read_gauge.py` — Read analog gauge
- `continuous_monitor.py` — Continuous monitoring with CSV output

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=vision_connector

# Run specific test file
pytest tests/test_hmi_reader.py
```

---

## Dependencies

- `opencv-python-headless` — Computer vision (headless, no GUI)
- `pytesseract` — OCR engine wrapper
- `numpy` — Array operations
- `Pillow` — Image handling
- `paho-mqtt` — MQTT client
- `requests` — HTTP client

**System requirement:** Tesseract OCR

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## About Good AI

**Good AI** is a premium enterprise AI consultancy specializing in:

- **Non-invasive Intelligence** — Extract value from legacy systems without integration
- **Augment First** — Digitize manual processes before automation
- **Industrial AI** — Computer vision, predictive maintenance, process optimization

*Unlock the value in your operations without the complexity of traditional integrations.*

---

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

---

## Support

- GitHub Issues: [Report bugs or request features](https://github.com/goodai/vision-connector/issues)
- Documentation: [Full documentation](https://github.com/goodai/vision-connector#readme)
