"""
Vision Connector - Non-invasive industrial data capture using computer vision.

By Good AI - Premium Enterprise AI Consultancy
https://goodai.com

The Problem:
    PLCs are locked, ERPs are ancient, IT won't give API access.
    Legacy systems hold critical data hostage.

The Solution:
    Point a camera at the screen operators already look at.
    Extract data without touching the underlying systems.

This is non-invasive intelligence - bypass legacy constraints without system integration.
"""

__version__ = "0.1.0"
__author__ = "Good AI"

# Configure logging at package import (can be reconfigured later)
from typing import Optional as _Optional

from vision_connector.config import Config, config, load_config
from vision_connector.exceptions import (
    CalibrationError,
    ConfigurationError,
    GaugeDetectionError,
    GaugeReadingError,
    ImageLoadError,
    ImageProcessingError,
    LowConfidenceError,
    MQTTError,
    NeedleDetectionError,
    NoDisplayError,
    OCRError,
    OCRExtractionError,
    OutputError,
    RegionError,
    RegionOutOfBoundsError,
    RetryExhaustedError,
    TesseractNotFoundError,
    ValidationError,
    VisionConnectorError,
    WebhookError,
)
from vision_connector.logging import (
    VisionLogger,
    clear_context,
    get_logger,
    set_context,
)
from vision_connector.metrics import metrics, track_duration, track_operation
from vision_connector.processors.display_reader import DisplayReader
from vision_connector.processors.gauge_reader import GaugeReader
from vision_connector.processors.hmi_reader import HMIReader
from vision_connector.processors.ocr import OCRProcessor
from vision_connector.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    CircuitState,
    RetryConfig,
    retry,
    with_fallback,
    with_timeout,
)


def configure_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: _Optional[str] = None,
    **kwargs,
):
    """
    Configure vision-connector logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_format: Use JSON structured output for log aggregation.
        log_file: Optional file path for log output.
        **kwargs: Additional fields to include in every log entry.
    """
    VisionLogger.configure(
        level=level,
        json_format=json_format,
        log_file=log_file,
        extra_fields=kwargs if kwargs else None,
    )


__all__ = [
    # Processors
    "HMIReader",
    "GaugeReader",
    "DisplayReader",
    "OCRProcessor",
    # Logging
    "configure_logging",
    "get_logger",
    "set_context",
    "clear_context",
    # Metrics
    "metrics",
    "track_operation",
    "track_duration",
    # Configuration
    "Config",
    "config",
    "load_config",
    # Resilience
    "retry",
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "CircuitState",
    "with_timeout",
    "with_fallback",
    "RetryConfig",
    "CircuitBreakerConfig",
    # Exceptions
    "VisionConnectorError",
    "ImageProcessingError",
    "ImageLoadError",
    "RegionError",
    "RegionOutOfBoundsError",
    "OCRError",
    "TesseractNotFoundError",
    "OCRExtractionError",
    "LowConfidenceError",
    "GaugeReadingError",
    "GaugeDetectionError",
    "NeedleDetectionError",
    "OutputError",
    "MQTTError",
    "WebhookError",
    "RetryExhaustedError",
    "ConfigurationError",
    "ValidationError",
    "CalibrationError",
    "NoDisplayError",
    # Version
    "__version__",
]
