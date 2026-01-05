"""
Display Reader for extracting values from digital displays.

Optimized for reading 7-segment displays, LED readouts, and
other digital numeric displays.
Works headless - no display required.
"""

from typing import Dict, List, Optional, Union

import cv2
import numpy as np
from PIL import Image

from vision_connector.logging import get_logger
from vision_connector.processors.ocr import OCRProcessor
from vision_connector.utils.image_utils import (
    load_image,
    crop_region,
    detect_text_color_scheme,
)

# Module logger
_logger = get_logger(__name__)


class DisplayReader:
    """
    Reader for digital displays (7-segment, LED, LCD).

    Optimized preprocessing for reading numeric values from
    digital display panels commonly found in industrial equipment.

    Example:
        >>> reader = DisplayReader()
        >>> result = reader.read_display(
        ...     "display.png",
        ...     region={"x": 10, "y": 10, "w": 200, "h": 60}
        ... )
        >>> print(result)
        {"value": 1234.5, "raw_text": "1234.5", "confidence": 0.95}
    """

    def __init__(self, tesseract_cmd: Optional[str] = None):
        """
        Initialize the display reader.

        Args:
            tesseract_cmd: Optional path to tesseract executable.
        """
        _logger.debug("Initializing DisplayReader")
        self.ocr = OCRProcessor(tesseract_cmd=tesseract_cmd)
        _logger.info("DisplayReader initialized")

    def read_display(
        self,
        image: Union[str, np.ndarray, Image.Image],
        region: Optional[Dict] = None,
        display_type: str = "auto",
    ) -> Dict:
        """
        Read value from a digital display.

        Args:
            image: Image source (path, numpy array, or PIL Image).
            region: Optional region dict with x, y, w, h keys.
            display_type: Type of display - "7segment", "led", "lcd", or "auto".

        Returns:
            Dictionary with:
                - value: Parsed numeric value (float or None)
                - raw_text: Raw OCR text
                - confidence: OCR confidence score
        """
        _logger.debug("Reading display", display_type=display_type, has_region=region is not None)
        img = load_image(image)

        if region:
            img = crop_region(img, region)

        # Apply display-specific preprocessing
        if display_type == "7segment":
            processed = self._preprocess_7segment(img)
        elif display_type == "led":
            processed = self._preprocess_led(img)
        elif display_type == "lcd":
            processed = self._preprocess_lcd(img)
        else:
            # Auto-detect and try best preprocessing
            processed = self._auto_preprocess(img)

        # Extract text using numeric whitelist
        raw_text = self.ocr.extract_text(
            processed,
            preprocess=False,  # Already preprocessed
            psm=OCRProcessor.PSM_SINGLE_LINE,
            whitelist="0123456789.-",
        )

        # Parse numeric value
        value = self._parse_number(raw_text)

        # Get confidence
        confidence = self.ocr.get_average_confidence(processed)

        result = {
            "value": value,
            "raw_text": raw_text,
            "confidence": round(confidence, 3),
        }
        _logger.debug("Display read complete", value=value, confidence=round(confidence, 3))
        return result

    def read_multi_digit(
        self,
        image: Union[str, np.ndarray, Image.Image],
        digit_regions: List[Dict],
    ) -> Dict:
        """
        Read a number from multiple individual digit regions.

        Useful when digits are in separate display segments.

        Args:
            image: Image source.
            digit_regions: List of region dicts, one per digit, left to right.

        Returns:
            Dictionary with combined value and per-digit results.
        """
        img = load_image(image)

        digits = []
        confidences = []

        for region in digit_regions:
            digit_img = crop_region(img, region)
            processed = self._auto_preprocess(digit_img)

            text = self.ocr.extract_text(
                processed,
                preprocess=False,
                psm=OCRProcessor.PSM_SINGLE_WORD,
                whitelist="0123456789.-",
            )

            # Take first character if multiple detected
            digit = text[0] if text else ""
            digits.append(digit)

            conf = self.ocr.get_average_confidence(processed)
            confidences.append(conf)

        combined = "".join(digits)
        value = self._parse_number(combined)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return {
            "value": value,
            "digits": digits,
            "raw_text": combined,
            "confidence": round(avg_confidence, 3),
        }

    def _preprocess_7segment(self, image: np.ndarray) -> np.ndarray:
        """Preprocess for 7-segment displays."""
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Scale up
        gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

        # Determine if we need to invert (light digits on dark background)
        color_scheme = detect_text_color_scheme(gray)

        if color_scheme == "light_on_dark":
            gray = cv2.bitwise_not(gray)

        # Apply morphological operations to clean up segments
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)

        # Threshold
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return thresh

    def _preprocess_led(self, image: np.ndarray) -> np.ndarray:
        """Preprocess for LED displays (often red/green on black)."""
        if len(image.shape) == 3:
            # Convert to HSV to better detect colored LEDs
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            # Create mask for bright colored areas (LEDs)
            # High saturation and value = LED segments
            lower = np.array([0, 50, 100])
            upper = np.array([180, 255, 255])
            mask = cv2.inRange(hsv, lower, upper)

            # Also capture very bright areas regardless of color
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, bright = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

            # Combine masks
            combined = cv2.bitwise_or(mask, bright)
        else:
            combined = image.copy()
            _, combined = cv2.threshold(combined, 127, 255, cv2.THRESH_BINARY)

        # Scale up
        combined = cv2.resize(combined, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)

        # Clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)

        return combined

    def _preprocess_lcd(self, image: np.ndarray) -> np.ndarray:
        """Preprocess for LCD displays."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Scale up
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # Adaptive threshold works well for LCD
        thresh = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=15,
            C=5,
        )

        return thresh

    def _auto_preprocess(self, image: np.ndarray) -> np.ndarray:
        """Auto-detect display type and apply best preprocessing."""
        if len(image.shape) == 3:
            # Check for colored display (LED-like)
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            saturation = hsv[:, :, 1].mean()

            if saturation > 50:
                # Likely colored LED display
                return self._preprocess_led(image)

        # Check background brightness
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        mean_brightness = gray.mean()

        if mean_brightness < 80:
            # Dark background - likely 7-segment or LED
            return self._preprocess_7segment(image)
        else:
            # Light background - likely LCD
            return self._preprocess_lcd(image)

    def _parse_number(self, text: str) -> Optional[float]:
        """Parse numeric value from OCR text."""
        if not text:
            return None

        # Clean up common OCR errors
        text = text.strip()
        text = text.replace(" ", "")
        text = text.replace("O", "0")  # Common OCR error
        text = text.replace("o", "0")
        text = text.replace("l", "1")
        text = text.replace("I", "1")
        text = text.replace(",", ".")  # European decimal

        try:
            return float(text)
        except ValueError:
            # Try to extract just the numeric parts
            import re
            match = re.search(r"-?\d+\.?\d*", text)
            if match:
                try:
                    return float(match.group())
                except ValueError:
                    pass
            return None
