# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-01-06

### Added

- **Core Processors**
  - HMI Screen Reader: Extract values from industrial HMI screen captures
  - Gauge Reader: Read analog gauges using needle detection
  - Display Reader: Process 7-segment and LED digital displays
  - OCR Processor: Tesseract-based text extraction with preprocessing

- **Capture Sources**
  - Image Capture: File and directory-based capture with watch mode
  - Camera Capture: USB and IP camera support (RTSP streams)

- **Output Options**
  - CSV Writer: Log data to CSV files with schema evolution
  - MQTT Output: Stream to MQTT brokers with TLS support
  - Webhook Output: Send to HTTP endpoints with retry logic

- **Enterprise Infrastructure**
  - Structured logging with JSON/text formatters and operation tracing
  - Prometheus metrics integration (optional dependency)
  - YAML configuration with environment variable overrides
  - Custom exception hierarchy for programmatic error handling
  - Resilience patterns: retry with backoff, circuit breaker, timeouts

- **Calibration**
  - ROI Selector: Programmatic and interactive region selection
  - Config file generation

- **Quality**
  - 157 passing tests
  - Full headless operation support (opencv-python-headless)
  - Type hints throughout

### Security

- TLS support for MQTT connections
- SSL verification for webhooks (enabled by default)
- URL scheme validation prevents SSRF
- YAML uses safe_load only
- No command injection vectors

### Documentation

- README with quickstart guide
- CONTRIBUTING guide for developers
- SECURITY policy
- RELEASING process documentation

[Unreleased]: https://github.com/goodai/vision-connector/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/goodai/vision-connector/releases/tag/v0.1.0
