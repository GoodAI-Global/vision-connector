"""
Custom exception hierarchy for vision-connector.

Provides structured exceptions for better error handling and debugging.
Each exception includes context information for troubleshooting.
"""

from typing import Any, Dict, Optional


class VisionConnectorError(Exception):
    """
    Base exception for all vision-connector errors.

    All custom exceptions inherit from this class.

    Attributes:
        message: Human-readable error message.
        details: Optional dictionary with additional context.
        original_error: Optional wrapped exception.
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional context.
            original_error: Optional wrapped exception.
        """
        self.message = message
        self.details = details or {}
        self.original_error = original_error

        # Build full message
        full_message = message
        if details:
            detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
            full_message = f"{message} ({detail_str})"

        super().__init__(full_message)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for logging/serialization.

        Returns:
            Dictionary representation of the exception.
        """
        result = {
            "type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }
        if self.original_error:
            result["original_error"] = {
                "type": type(self.original_error).__name__,
                "message": str(self.original_error),
            }
        return result


# ============================================================================
# Image Processing Exceptions
# ============================================================================


class ImageProcessingError(VisionConnectorError):
    """Base exception for image processing errors."""

    pass


class ImageLoadError(ImageProcessingError):
    """Raised when an image cannot be loaded."""

    def __init__(
        self,
        path: str,
        reason: str = "unknown",
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            f"Failed to load image: {path}",
            details={"path": path, "reason": reason},
            original_error=original_error,
        )


class RegionError(ImageProcessingError):
    """Raised when a region specification is invalid."""

    def __init__(
        self,
        message: str,
        region: Optional[Dict] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message,
            details={"region": region} if region else {},
            original_error=original_error,
        )


class RegionOutOfBoundsError(RegionError):
    """Raised when a region extends beyond image boundaries."""

    def __init__(
        self,
        region: Dict,
        image_size: tuple,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            f"Region {region} extends beyond image boundaries {image_size}",
            region=region,
            original_error=original_error,
        )
        self.details["image_size"] = image_size


# ============================================================================
# OCR Exceptions
# ============================================================================


class OCRError(VisionConnectorError):
    """Base exception for OCR-related errors."""

    pass


class TesseractNotFoundError(OCRError):
    """Raised when Tesseract OCR is not installed or not found."""

    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        message = (
            "Tesseract OCR not found. Please install Tesseract:\n"
            "  Ubuntu/Debian: sudo apt-get install tesseract-ocr\n"
            "  macOS: brew install tesseract\n"
            "  Windows: https://github.com/UB-Mannheim/tesseract/wiki"
        )
        super().__init__(
            message,
            details={"tesseract_cmd": tesseract_cmd},
            original_error=original_error,
        )


class OCRExtractionError(OCRError):
    """Raised when OCR extraction fails."""

    def __init__(
        self,
        message: str = "OCR extraction failed",
        region: Optional[Dict] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message,
            details={"region": region} if region else {},
            original_error=original_error,
        )


class LowConfidenceError(OCRError):
    """Raised when OCR confidence is below threshold."""

    def __init__(
        self,
        confidence: float,
        threshold: float,
        field: Optional[str] = None,
    ):
        message = f"OCR confidence {confidence:.2%} below threshold {threshold:.2%}"
        if field:
            message = f"{field}: {message}"
        super().__init__(
            message,
            details={
                "confidence": confidence,
                "threshold": threshold,
                "field": field,
            },
        )


# ============================================================================
# Gauge Reading Exceptions
# ============================================================================


class GaugeReadingError(VisionConnectorError):
    """Base exception for gauge reading errors."""

    pass


class GaugeDetectionError(GaugeReadingError):
    """Raised when gauge circle cannot be detected."""

    def __init__(
        self,
        message: str = "Could not detect gauge circle",
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message, original_error=original_error)


class NeedleDetectionError(GaugeReadingError):
    """Raised when gauge needle cannot be detected."""

    def __init__(
        self,
        message: str = "Could not detect gauge needle",
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message, original_error=original_error)


# ============================================================================
# Output/Connection Exceptions
# ============================================================================


class OutputError(VisionConnectorError):
    """Base exception for output-related errors."""

    pass


class ConnectionError(OutputError):
    """Raised when a connection fails."""

    def __init__(
        self,
        service: str,
        host: str,
        port: int,
        reason: str = "Connection failed",
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            f"{service} connection failed: {host}:{port}",
            details={
                "service": service,
                "host": host,
                "port": port,
                "reason": reason,
            },
            original_error=original_error,
        )


class MQTTError(OutputError):
    """Raised for MQTT-specific errors."""

    def __init__(
        self,
        message: str,
        broker: Optional[str] = None,
        topic: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message,
            details={"broker": broker, "topic": topic},
            original_error=original_error,
        )


class WebhookError(OutputError):
    """Raised for webhook-specific errors."""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message,
            details={"url": url, "status_code": status_code},
            original_error=original_error,
        )


class RetryExhaustedError(OutputError):
    """Raised when all retry attempts have been exhausted."""

    def __init__(
        self,
        operation: str,
        attempts: int,
        last_error: Optional[Exception] = None,
    ):
        super().__init__(
            f"Retry exhausted for {operation} after {attempts} attempts",
            details={"operation": operation, "attempts": attempts},
            original_error=last_error,
        )


# ============================================================================
# Configuration Exceptions
# ============================================================================


class ConfigurationError(VisionConnectorError):
    """Raised for configuration-related errors."""

    def __init__(
        self,
        message: str,
        key: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message,
            details={"key": key} if key else {},
            original_error=original_error,
        )


class ValidationError(ConfigurationError):
    """Raised when configuration validation fails."""

    def __init__(
        self,
        errors: list,
        original_error: Optional[Exception] = None,
    ):
        message = f"Configuration validation failed: {len(errors)} error(s)"
        super().__init__(
            message,
            original_error=original_error,
        )
        self.details["errors"] = errors
        self.validation_errors = errors


# ============================================================================
# Calibration Exceptions
# ============================================================================


class CalibrationError(VisionConnectorError):
    """Raised for calibration-related errors."""

    pass


class NoDisplayError(CalibrationError):
    """Raised when a display is required but not available."""

    def __init__(self, operation: str):
        super().__init__(
            f"No display available for {operation}. "
            "Use headless alternatives or configure display.",
            details={"operation": operation},
        )
