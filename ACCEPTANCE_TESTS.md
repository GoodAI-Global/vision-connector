# Acceptance Tests

This document outlines the acceptance criteria and test procedures for Vision Connector.

## Prerequisites

- Python 3.8+
- Tesseract OCR installed on the system

### Installing Tesseract

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

---

## Commands

Run these commands to verify the installation:

### 1. Install the Package

```bash
pip install -e .
```

**Expected Result:**
- Installation completes without errors
- Uses `opencv-python-headless` (not `opencv-python`)
- All dependencies installed

### 2. Run the Demo

```bash
python demo_run.py
```

**Expected Result:**
- Demo runs without errors
- Prints JSON output with extracted values
- Output includes fields like: temperature, pressure, status

Example output:
```
============================================================
  VISION CONNECTOR DEMO
  Version: 0.1.0
  Non-invasive industrial data capture using computer vision
============================================================

Image: sample_images/hmi_screen.png
Config: config/sample_config.json

Initializing HMI Reader...
OK - Reader initialized

Reading values from HMI screen...
----------------------------------------

EXTRACTED VALUES:
----------------------------------------
{
  "temperature": "185.5",
  "pressure": "42.3",
  ...
}

Successfully extracted 6 values
```

### 3. Run Tests

```bash
pytest
```

**Expected Result:**
- All tests pass
- Minimum 4 tests run
- No failures or errors

Example output:
```
tests/test_hmi_reader.py ....
tests/test_gauge_reader.py ...
tests/test_ocr.py ....
```

---

## Functional Tests

### Test 1: HMI Reader with Sample Image

```python
from vision_connector import HMIReader

reader = HMIReader(config="config/sample_config.json")
result = reader.read_image("sample_images/hmi_screen.png")

assert isinstance(result, dict)
assert len(result) > 0
print("HMI Reader: PASS")
```

### Test 2: Gauge Reader

```python
from vision_connector import GaugeReader

reader = GaugeReader()
result = reader.read_analog_gauge(
    "sample_images/analog_gauge.png",
    min_value=0,
    max_value=100,
    unit="PSI"
)

assert "value" in result
assert "confidence" in result
print("Gauge Reader: PASS")
```

### Test 3: Headless Operation

```python
import os
from vision_connector import HMIReader

# Remove DISPLAY to simulate headless
os.environ.pop("DISPLAY", None)

reader = HMIReader(config="config/sample_config.json")
result = reader.read_image("sample_images/hmi_screen.png")

# Should work without display
assert result is not None
print("Headless Operation: PASS")
```

### Test 4: Config Loading

```python
import json
from vision_connector import HMIReader

with open("config/sample_config.json") as f:
    config = json.load(f)

assert "regions" in config
assert "temperature" in config["regions"]

reader = HMIReader(config="config/sample_config.json")
assert len(reader.default_regions) > 0
print("Config Loading: PASS")
```

---

## Headless Requirements

The library MUST work in CI/Docker without a display:

1. **No cv2.imshow calls** in production code paths
2. **Uses opencv-python-headless** (not opencv-python)
3. **ROI selection** has headless fallback (config file or parameters)
4. **Clear error messages** when interactive features require display

### Verify Headless Compatibility

```bash
# Unset DISPLAY and run demo
DISPLAY= python demo_run.py
```

Should complete successfully or provide helpful error message about specifying ROI via config.

---

## Sample Files Checklist

Verify these files exist and are valid:

- [ ] `sample_images/hmi_screen.png` - HMI screen sample
- [ ] `sample_images/analog_gauge.png` - Analog gauge sample
- [ ] `sample_images/digital_display.png` - Digital display sample
- [ ] `config/sample_config.json` - Sample configuration

---

## Definition of Done

- [x] `pip install -e .` works without errors
- [x] `python demo_run.py` outputs extracted values from sample image
- [x] Works headless (no cv2.imshow, no GUI ROI selection required)
- [x] `pytest` passes (minimum 4 tests)
- [x] Sample images included and valid
- [x] README.md with documentation
- [x] MIT LICENSE file

---

## Quick Verification Script

Run this to verify everything works:

```bash
#!/bin/bash
set -e

echo "=== Vision Connector Acceptance Tests ==="

echo "1. Installing package..."
pip install -e . -q

echo "2. Running demo..."
python demo_run.py

echo "3. Running tests..."
pytest -v

echo ""
echo "=== ALL TESTS PASSED ==="
```

Save as `verify.sh` and run with `bash verify.sh`.
