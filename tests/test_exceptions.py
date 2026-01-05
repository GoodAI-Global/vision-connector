"""
Tests for the custom exception hierarchy.
"""

import pytest

from vision_connector.exceptions import (
    VisionConnectorError,
    ImageProcessingError,
    ImageLoadError,
    RegionError,
    RegionOutOfBoundsError,
    OCRError,
    TesseractNotFoundError,
    OCRExtractionError,
    LowConfidenceError,
    GaugeReadingError,
    GaugeDetectionError,
    NeedleDetectionError,
    OutputError,
    MQTTError,
    WebhookError,
    RetryExhaustedError,
    ConfigurationError,
    ValidationError,
    CalibrationError,
    NoDisplayError,
)


class TestVisionConnectorError:
    """Tests for base VisionConnectorError."""

    def test_basic_creation(self):
        """Test basic exception creation."""
        error = VisionConnectorError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}
        assert error.original_error is None

    def test_with_details(self):
        """Test exception with details."""
        error = VisionConnectorError(
            "Test error",
            details={"key": "value", "count": 42},
        )
        assert "key=value" in str(error)
        assert "count=42" in str(error)
        assert error.details["key"] == "value"

    def test_with_original_error(self):
        """Test exception wrapping another exception."""
        original = ValueError("Original error")
        error = VisionConnectorError(
            "Wrapped error",
            original_error=original,
        )
        assert error.original_error is original

    def test_to_dict(self):
        """Test conversion to dictionary."""
        original = ValueError("Original")
        error = VisionConnectorError(
            "Test error",
            details={"key": "value"},
            original_error=original,
        )

        result = error.to_dict()
        assert result["type"] == "VisionConnectorError"
        assert result["message"] == "Test error"
        assert result["details"]["key"] == "value"
        assert result["original_error"]["type"] == "ValueError"


class TestExceptionHierarchy:
    """Tests for exception inheritance."""

    def test_image_processing_inherits(self):
        """Test ImageProcessingError inherits from VisionConnectorError."""
        error = ImageProcessingError("Test")
        assert isinstance(error, VisionConnectorError)

    def test_ocr_error_inherits(self):
        """Test OCRError inherits from VisionConnectorError."""
        error = OCRError("Test")
        assert isinstance(error, VisionConnectorError)

    def test_output_error_inherits(self):
        """Test OutputError inherits from VisionConnectorError."""
        error = OutputError("Test")
        assert isinstance(error, VisionConnectorError)


class TestImageLoadError:
    """Tests for ImageLoadError."""

    def test_creation(self):
        """Test ImageLoadError creation."""
        error = ImageLoadError(
            path="/path/to/image.png",
            reason="file not found",
        )
        assert "Failed to load image" in str(error)
        assert "/path/to/image.png" in str(error)
        assert error.details["path"] == "/path/to/image.png"
        assert error.details["reason"] == "file not found"


class TestRegionErrors:
    """Tests for region-related errors."""

    def test_region_error(self):
        """Test RegionError creation."""
        region = {"x": 0, "y": 0, "w": 100, "h": 50}
        error = RegionError("Invalid region", region=region)
        assert error.details["region"] == region

    def test_region_out_of_bounds(self):
        """Test RegionOutOfBoundsError creation."""
        region = {"x": 100, "y": 100, "w": 200, "h": 200}
        error = RegionOutOfBoundsError(
            region=region,
            image_size=(150, 150),
        )
        assert "extends beyond" in str(error)
        assert error.details["image_size"] == (150, 150)


class TestOCRErrors:
    """Tests for OCR-related errors."""

    def test_tesseract_not_found(self):
        """Test TesseractNotFoundError creation."""
        error = TesseractNotFoundError(tesseract_cmd="/custom/path")
        assert "not found" in str(error).lower()
        assert "apt-get" in str(error) or "brew" in str(error)
        assert error.details["tesseract_cmd"] == "/custom/path"

    def test_low_confidence_error(self):
        """Test LowConfidenceError creation."""
        error = LowConfidenceError(
            confidence=0.45,
            threshold=0.80,
            field="temperature",
        )
        assert "45" in str(error)  # 45%
        assert "80" in str(error)  # 80%
        assert "temperature" in str(error)


class TestOutputErrors:
    """Tests for output-related errors."""

    def test_mqtt_error(self):
        """Test MQTTError creation."""
        error = MQTTError(
            "Connection refused",
            broker="localhost:1883",
            topic="test/topic",
        )
        assert error.details["broker"] == "localhost:1883"
        assert error.details["topic"] == "test/topic"

    def test_webhook_error(self):
        """Test WebhookError creation."""
        error = WebhookError(
            "Request failed",
            url="https://example.com/webhook",
            status_code=500,
        )
        assert error.details["url"] == "https://example.com/webhook"
        assert error.details["status_code"] == 500

    def test_retry_exhausted(self):
        """Test RetryExhaustedError creation."""
        last_error = ConnectionError("timeout")
        error = RetryExhaustedError(
            operation="publish",
            attempts=3,
            last_error=last_error,
        )
        assert "3 attempts" in str(error)
        assert error.details["operation"] == "publish"
        assert error.original_error is last_error


class TestConfigurationErrors:
    """Tests for configuration-related errors."""

    def test_configuration_error(self):
        """Test ConfigurationError creation."""
        error = ConfigurationError(
            "Missing required key",
            key="mqtt.broker",
        )
        assert error.details["key"] == "mqtt.broker"

    def test_validation_error(self):
        """Test ValidationError creation."""
        errors = ["Missing key: a", "Invalid type: b"]
        error = ValidationError(errors=errors)
        assert "2 error(s)" in str(error)
        assert error.validation_errors == errors


class TestCalibrationErrors:
    """Tests for calibration-related errors."""

    def test_no_display_error(self):
        """Test NoDisplayError creation."""
        error = NoDisplayError(operation="ROI selection")
        assert "No display available" in str(error)
        assert error.details["operation"] == "ROI selection"


class TestExceptionUsage:
    """Tests for exception usage in try/except blocks."""

    def test_catch_specific_error(self):
        """Test catching specific error type."""
        with pytest.raises(ImageLoadError):
            raise ImageLoadError("/path/to/image.png")

    def test_catch_base_error(self):
        """Test catching base error catches specific errors."""
        with pytest.raises(VisionConnectorError):
            raise ImageLoadError("/path/to/image.png")

    def test_catch_ocr_error(self):
        """Test catching OCR error hierarchy."""
        with pytest.raises(OCRError):
            raise TesseractNotFoundError()

    def test_catch_with_attributes(self):
        """Test catching error and accessing attributes."""
        try:
            raise LowConfidenceError(0.3, 0.8, "pressure")
        except OCRError as e:
            assert e.details["confidence"] == 0.3
            assert e.details["threshold"] == 0.8
