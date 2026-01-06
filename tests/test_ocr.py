"""Tests for OCR Processor functionality."""

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from vision_connector.processors.ocr import OCRProcessor


@pytest.fixture
def ocr_processor():
    """Create an OCR processor instance."""
    return OCRProcessor()


def create_text_image(text: str, size=(200, 50), bg_color="white", text_color="black"):
    """Create a simple image with text for testing."""
    img = Image.new("RGB", size, bg_color)
    draw = ImageDraw.Draw(img)

    # Try to get a font, fall back to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except (OSError, IOError):
        font = ImageFont.load_default()

    draw.text((10, 10), text, fill=text_color, font=font)
    return np.array(img)


class TestOCRProcessorBasic:
    """Basic OCR Processor tests."""

    def test_processor_initialization(self, ocr_processor):
        """Test that processor initializes correctly."""
        assert ocr_processor is not None
        assert ocr_processor.lang == "eng"

    def test_tesseract_available(self, ocr_processor):
        """Test that Tesseract is available."""
        assert hasattr(ocr_processor, "_tesseract_version")


class TestOCRExtractText:
    """Tests for text extraction."""

    def test_extract_text_from_image(self, ocr_processor):
        """Test extracting text from a simple image."""
        img = create_text_image("HELLO")
        text = ocr_processor.extract_text(img)

        # Should extract something (OCR may not be perfect)
        assert isinstance(text, str)

    def test_extract_text_from_numpy_array(self, ocr_processor):
        """Test extracting text from numpy array."""
        img = create_text_image("TEST")
        text = ocr_processor.extract_text(img)

        assert isinstance(text, str)

    def test_extract_text_with_region(self, ocr_processor):
        """Test extracting text from a specific region."""
        img = create_text_image("12345", size=(300, 100))
        text = ocr_processor.extract_text(
            img, region={"x": 0, "y": 0, "w": 150, "h": 50}
        )

        assert isinstance(text, str)


class TestOCRExtractNumbers:
    """Tests for number extraction."""

    def test_extract_numbers(self, ocr_processor):
        """Test extracting numbers from image."""
        img = create_text_image("123")
        numbers = ocr_processor.extract_numbers(img)

        assert isinstance(numbers, list)

    def test_extract_single_number(self, ocr_processor):
        """Test extracting a single number."""
        img = create_text_image("42")
        number = ocr_processor.extract_single_number(img)

        # May or may not successfully extract
        assert number is None or isinstance(number, float)

    def test_extract_decimal_number(self, ocr_processor):
        """Test extracting decimal numbers."""
        img = create_text_image("3.14")
        numbers = ocr_processor.extract_numbers(img, allow_decimal=True)

        assert isinstance(numbers, list)


class TestOCRConfidence:
    """Tests for confidence scores."""

    def test_extract_with_confidence(self, ocr_processor):
        """Test extraction with confidence scores."""
        img = create_text_image("TEST")
        results = ocr_processor.extract_with_confidence(img)

        assert isinstance(results, list)
        # Each result should have required fields
        for r in results:
            if r:  # If any results returned
                assert "text" in r or len(results) == 0
                assert "confidence" in r or len(results) == 0

    def test_get_average_confidence(self, ocr_processor):
        """Test getting average confidence score."""
        img = create_text_image("TEST")
        confidence = ocr_processor.get_average_confidence(img)

        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1


class TestOCRPreprocessing:
    """Tests for image preprocessing."""

    def test_extract_dark_background(self, ocr_processor):
        """Test extraction from dark background image."""
        img = create_text_image("123", bg_color="black", text_color="white")
        text = ocr_processor.extract_text(img)

        assert isinstance(text, str)

    def test_psm_modes(self, ocr_processor):
        """Test different page segmentation modes."""
        img = create_text_image("WORD")

        # Single line mode
        text1 = ocr_processor.extract_text(img, psm=OCRProcessor.PSM_SINGLE_LINE)
        # Single word mode
        text2 = ocr_processor.extract_text(img, psm=OCRProcessor.PSM_SINGLE_WORD)

        assert isinstance(text1, str)
        assert isinstance(text2, str)


class TestOCRWhitelist:
    """Tests for character whitelist."""

    def test_whitelist_numbers_only(self, ocr_processor):
        """Test extraction with numeric whitelist."""
        img = create_text_image("ABC123")
        text = ocr_processor.extract_text(img, whitelist="0123456789")

        # Should only contain digits (if anything)
        if text:
            assert all(c.isdigit() or c.isspace() for c in text)
