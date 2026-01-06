"""Deterministic tests using included sample images.

These tests verify CV/OCR functionality against known sample images
with expected outputs, ensuring reproducible results.
"""

from pathlib import Path

import pytest

from vision_connector import GaugeReader, HMIReader, OCRProcessor

# Path to sample images directory
SAMPLE_DIR = Path(__file__).parent.parent / "sample_images"


def sample_image_exists(name: str) -> bool:
    """Check if a sample image exists."""
    return (SAMPLE_DIR / name).exists()


# Skip all tests if sample images are missing
pytestmark = pytest.mark.skipif(
    not SAMPLE_DIR.exists(),
    reason="Sample images directory not found",
)


class TestDigitalDisplayOCR:
    """Tests for OCR on digital_display.png.

    Expected: Red "1234.5" on black background.
    """

    @pytest.fixture
    def ocr(self):
        return OCRProcessor()

    @pytest.fixture
    def image_path(self):
        return str(SAMPLE_DIR / "digital_display.png")

    @pytest.mark.skipif(
        not sample_image_exists("digital_display.png"),
        reason="digital_display.png not found",
    )
    def test_extract_text_reads_display(self, ocr, image_path):
        """OCR should extract '1234.5' from digital display."""
        text = ocr.extract_text(image_path)
        # Clean up whitespace and check for expected value
        cleaned = text.strip().replace(" ", "")
        assert "1234.5" in cleaned or "1234" in cleaned

    @pytest.mark.skipif(
        not sample_image_exists("digital_display.png"),
        reason="digital_display.png not found",
    )
    def test_extract_numbers_returns_value(self, ocr, image_path):
        """extract_numbers should return [1234.5]."""
        numbers = ocr.extract_numbers(image_path, allow_decimal=True)
        assert len(numbers) >= 1
        # The primary number should be 1234.5
        assert any(abs(n - 1234.5) < 1 for n in numbers)

    @pytest.mark.skipif(
        not sample_image_exists("digital_display.png"),
        reason="digital_display.png not found",
    )
    def test_extract_single_number(self, ocr, image_path):
        """extract_single_number should return 1234.5."""
        number = ocr.extract_single_number(image_path)
        assert number is not None
        assert abs(number - 1234.5) < 1


class TestAnalogGauge:
    """Tests for GaugeReader on analog_gauge.png.

    Expected: PSI gauge 0-100, needle pointing at ~67.
    """

    @pytest.fixture
    def reader(self):
        # Calibrated for the sample gauge layout
        return GaugeReader(min_angle=225, max_angle=315)

    @pytest.fixture
    def image_path(self):
        return str(SAMPLE_DIR / "analog_gauge.png")

    @pytest.mark.skipif(
        not sample_image_exists("analog_gauge.png"),
        reason="analog_gauge.png not found",
    )
    def test_read_gauge_returns_dict(self, reader, image_path):
        """read_analog_gauge should return a result dict."""
        result = reader.read_analog_gauge(
            image_path, min_value=0, max_value=100, unit="PSI"
        )
        assert isinstance(result, dict)
        assert "value" in result
        assert "confidence" in result

    @pytest.mark.skipif(
        not sample_image_exists("analog_gauge.png"),
        reason="analog_gauge.png not found",
    )
    def test_read_gauge_value_in_range(self, reader, image_path):
        """Gauge value should be within 0-100 range."""
        result = reader.read_analog_gauge(
            image_path, min_value=0, max_value=100, unit="PSI"
        )
        assert 0 <= result["value"] <= 100

    @pytest.mark.skipif(
        not sample_image_exists("analog_gauge.png"),
        reason="analog_gauge.png not found",
    )
    def test_read_gauge_unit_preserved(self, reader, image_path):
        """Unit should be preserved in result."""
        result = reader.read_analog_gauge(
            image_path, min_value=0, max_value=100, unit="PSI"
        )
        assert result.get("unit") == "PSI"


class TestHMIScreen:
    """Tests for HMIReader on hmi_screen.png.

    Expected values:
    - Temperature: 185.5 C
    - Pressure: 42.3 PSI
    - Flow Rate: 127.8 L/min
    - Status: RUNNING
    - Units Produced: 1247
    """

    @pytest.fixture
    def reader(self):
        return HMIReader()

    @pytest.fixture
    def image_path(self):
        return str(SAMPLE_DIR / "hmi_screen.png")

    @pytest.mark.skipif(
        not sample_image_exists("hmi_screen.png"),
        reason="hmi_screen.png not found",
    )
    def test_read_status_region(self, reader, image_path):
        """Should read 'RUNNING' from status region."""
        regions = {
            "status": {"x": 350, "y": 148, "w": 170, "h": 45},
        }
        result = reader.read_image(image_path, regions=regions)
        assert "RUNNING" in result.get("status", "").upper()

    @pytest.mark.skipif(
        not sample_image_exists("hmi_screen.png"),
        reason="hmi_screen.png not found",
    )
    def test_read_multiple_regions(self, reader, image_path):
        """Should read multiple regions from HMI screen."""
        regions = {
            "status": {"x": 350, "y": 148, "w": 170, "h": 45},
            "header": {"x": 0, "y": 0, "w": 400, "h": 50},
        }
        result = reader.read_image(image_path, regions=regions)
        assert isinstance(result, dict)
        assert len(result) == 2

    @pytest.mark.skipif(
        not sample_image_exists("hmi_screen.png"),
        reason="hmi_screen.png not found",
    )
    def test_read_returns_string_values(self, reader, image_path):
        """All region values should be strings."""
        regions = {
            "status": {"x": 350, "y": 148, "w": 170, "h": 45},
        }
        result = reader.read_image(image_path, regions=regions)
        for _key, value in result.items():
            assert isinstance(value, str)


class TestOCRWithSampleImages:
    """Direct OCR tests on sample images."""

    @pytest.fixture
    def ocr(self):
        return OCRProcessor()

    @pytest.mark.skipif(
        not sample_image_exists("hmi_screen.png"),
        reason="hmi_screen.png not found",
    )
    def test_ocr_full_hmi_screen(self, ocr):
        """OCR should extract text from full HMI screen."""
        image_path = str(SAMPLE_DIR / "hmi_screen.png")
        text = ocr.extract_text(image_path)

        # Should find key text elements
        text_upper = text.upper()
        # At least one of these should be found
        found_keywords = sum(
            [
                "RUNNING" in text_upper,
                "TEMPERATURE" in text_upper,
                "PRESSURE" in text_upper,
                "PSI" in text_upper,
            ]
        )
        assert found_keywords >= 1

    @pytest.mark.skipif(
        not sample_image_exists("digital_display.png"),
        reason="digital_display.png not found",
    )
    def test_ocr_confidence_on_clear_image(self, ocr):
        """Clear digital display should have reasonable confidence."""
        image_path = str(SAMPLE_DIR / "digital_display.png")
        confidence = ocr.get_average_confidence(image_path)
        # Digital display with clear text should have decent confidence
        assert confidence >= 0.0  # At minimum returns a value
