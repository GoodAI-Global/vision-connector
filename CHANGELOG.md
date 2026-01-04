# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-01-01

### Added

- Initial release of vision-connector
- **HMI Screen Reader**: Extract values from industrial HMI screen captures
  - Support for numeric and text regions
  - JSON configuration file support
  - Confidence score reporting
- **Gauge Reader**: Read analog gauges using needle detection
  - Automatic circle detection
  - Configurable min/max angles
  - Calibration support
- **Display Reader**: Process 7-segment and LED digital displays
  - Auto-detection of display type
  - Preprocessing optimizations for OCR
- **OCR Processor**: Tesseract-based text extraction
  - Automatic preprocessing
  - Light/dark background detection
  - Whitelist character filtering
- **Camera Capture**: USB and IP camera support
  - RTSP stream support
  - Resolution and FPS configuration
- **Image Capture**: File and directory-based capture
  - Watch mode for directories
  - Multiple format support
- **MQTT Output**: Stream data to MQTT brokers
  - TLS/SSL encryption support
  - QoS levels 0, 1, 2
  - IPv6 address support
  - paho-mqtt 2.x compatibility
- **Webhook Output**: Send data to HTTP endpoints
  - Retry with exponential backoff
  - SSL verification configuration
  - URL validation
- **CSV Writer**: Log data to CSV files
  - Automatic header management
  - Schema evolution support
- **ROI Selector**: Calibration tool for region selection
  - Programmatic and interactive modes
  - Config file generation
- Full headless operation support (opencv-python-headless)
- Comprehensive test suite (34 tests)
- MIT License

### Security

- TLS support for MQTT connections
- SSL verification for webhooks
- URL scheme validation
- Input validation for regions and coordinates
