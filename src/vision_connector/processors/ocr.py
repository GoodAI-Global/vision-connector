"""
OCR Processor for extracting text from images.

Uses Tesseract OCR for text recognition with preprocessing optimizations.
Works headless - no display required.
"""

import re
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
import pytesseract
from PIL import Image

from vision_connector.logging import get_logger
from vision_connector.utils.image_utils import (
    load_image,
    crop_region,
    preprocess_for_ocr,
    detect_text_color_scheme,
)

# Module logger
_logger = get_logger(__name__)


class OCRProcessor:
    """
    OCR processor for extracting text and numbers from images.

    Uses Tesseract OCR with preprocessing optimizations for industrial displays.
    Works entirely headless - no display required.

    Example:
        >>> ocr = OCRProcessor()
        >>> text = ocr.extract_text(image)
        >>> numbers = ocr.extract_numbers(image, region={"x": 0, "y": 0, "w": 100, "h": 50})
    """

    # Tesseract Page Segmentation Modes (PSM)
    PSM_SINGLE_BLOCK = 6  # Assume a single uniform block of text
    PSM_SINGLE_LINE = 7   # Treat the image as a single text line
    PSM_SINGLE_WORD = 8   # Treat the image as a single word
    PSM_SPARSE_TEXT = 11  # Sparse text. Find as much text as possible

    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        lang: str = "eng",
        default_config: str = "--oem 3",
    ):
        """
        Initialize the OCR processor.

        Args:
            tesseract_cmd: Path to tesseract executable. If None, uses system PATH.
            lang: Tesseract language code (default: "eng").
            default_config: Default Tesseract config string.
        """
        _logger.debug("Initializing OCRProcessor", lang=lang)

        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            _logger.debug("Using custom tesseract path", path=tesseract_cmd)

        self.lang = lang
        self.default_config = default_config

        # Verify Tesseract is available
        self._verify_tesseract()

        _logger.info(
            "OCRProcessor initialized",
            tesseract_version=self._tesseract_version,
            lang=self.lang,
        )

    def _verify_tesseract(self) -> None:
        """Verify that Tesseract is installed and accessible."""
        try:
            version = pytesseract.get_tesseract_version()
            self._tesseract_version = str(version)
            _logger.debug("Tesseract verified", version=self._tesseract_version)
        except Exception as e:
            _logger.error("Tesseract OCR not found", error=str(e))
            raise RuntimeError(
                f"Tesseract OCR not found. Please install Tesseract:\n"
                f"  Ubuntu/Debian: sudo apt-get install tesseract-ocr\n"
                f"  macOS: brew install tesseract\n"
                f"  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki\n"
                f"Original error: {e}"
            ) from e

    def extract_text(
        self,
        image: Union[str, np.ndarray, Image.Image],
        region: Optional[Dict] = None,
        preprocess: bool = True,
        psm: int = PSM_SINGLE_BLOCK,
        whitelist: Optional[str] = None,
    ) -> str:
        """
        Extract text from an image or image region.

        Args:
            image: Image source (path, numpy array, or PIL Image).
            region: Optional region dict with x, y, w, h keys.
            preprocess: Whether to apply preprocessing for better OCR.
            psm: Tesseract page segmentation mode.
            whitelist: Optional character whitelist (e.g., "0123456789.").

        Returns:
            Extracted text string, stripped of leading/trailing whitespace.
        """
        with _logger.operation("extract_text"):
            img = load_image(image)

            # Crop to region if specified
            if region:
                img = crop_region(img, region)

            # Preprocess for OCR
            if preprocess:
                # Auto-detect if we need to invert
                color_scheme = detect_text_color_scheme(img)
                invert = color_scheme == "light_on_dark"
                img = preprocess_for_ocr(img, invert=invert)

            # Build Tesseract config
            config = f"{self.default_config} --psm {psm}"
            if whitelist:
                config += f" -c tessedit_char_whitelist={whitelist}"

            # Run OCR
            text = pytesseract.image_to_string(img, lang=self.lang, config=config)

            result = text.strip()
            _logger.debug(
                "Text extracted",
                text_length=len(result),
                has_region=region is not None,
            )
            return result

    def extract_numbers(
        self,
        image: Union[str, np.ndarray, Image.Image],
        region: Optional[Dict] = None,
        allow_decimal: bool = True,
        allow_negative: bool = True,
    ) -> List[float]:
        """
        Extract numeric values from an image.

        Args:
            image: Image source (path, numpy array, or PIL Image).
            region: Optional region dict with x, y, w, h keys.
            allow_decimal: Whether to look for decimal numbers.
            allow_negative: Whether to look for negative numbers.

        Returns:
            List of extracted numbers as floats.
        """
        # Build whitelist for numeric extraction
        whitelist = "0123456789"
        if allow_decimal:
            whitelist += "."
        if allow_negative:
            whitelist += "-"

        text = self.extract_text(
            image,
            region=region,
            preprocess=True,
            psm=self.PSM_SINGLE_LINE,
            whitelist=whitelist,
        )

        # Parse numbers from text
        numbers = []

        # Build regex pattern
        if allow_decimal and allow_negative:
            pattern = r"-?\d+\.?\d*"
        elif allow_decimal:
            pattern = r"\d+\.?\d*"
        elif allow_negative:
            pattern = r"-?\d+"
        else:
            pattern = r"\d+"

        matches = re.findall(pattern, text)

        for match in matches:
            try:
                if "." in match:
                    numbers.append(float(match))
                else:
                    numbers.append(float(int(match)))
            except ValueError:
                continue

        return numbers

    def extract_single_number(
        self,
        image: Union[str, np.ndarray, Image.Image],
        region: Optional[Dict] = None,
        allow_decimal: bool = True,
        allow_negative: bool = True,
    ) -> Optional[float]:
        """
        Extract a single numeric value from an image.

        Args:
            image: Image source (path, numpy array, or PIL Image).
            region: Optional region dict with x, y, w, h keys.
            allow_decimal: Whether to look for decimal numbers.
            allow_negative: Whether to look for negative numbers.

        Returns:
            The first extracted number, or None if no number found.
        """
        numbers = self.extract_numbers(
            image,
            region=region,
            allow_decimal=allow_decimal,
            allow_negative=allow_negative,
        )
        return numbers[0] if numbers else None

    def extract_with_confidence(
        self,
        image: Union[str, np.ndarray, Image.Image],
        region: Optional[Dict] = None,
        preprocess: bool = True,
    ) -> List[Dict]:
        """
        Extract text with word-level confidence scores.

        Args:
            image: Image source (path, numpy array, or PIL Image).
            region: Optional region dict with x, y, w, h keys.
            preprocess: Whether to apply preprocessing.

        Returns:
            List of dicts with 'text', 'confidence', and 'bbox' keys.
        """
        img = load_image(image)

        if region:
            img = crop_region(img, region)

        if preprocess:
            color_scheme = detect_text_color_scheme(img)
            invert = color_scheme == "light_on_dark"
            img = preprocess_for_ocr(img, invert=invert)

        # Get detailed OCR data
        data = pytesseract.image_to_data(
            img,
            lang=self.lang,
            config=self.default_config,
            output_type=pytesseract.Output.DICT,
        )

        results = []
        n_boxes = len(data["text"])

        for i in range(n_boxes):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])

            # Skip empty text and low confidence
            if text and conf > 0:
                results.append({
                    "text": text,
                    "confidence": conf / 100.0,  # Normalize to 0-1
                    "bbox": {
                        "x": data["left"][i],
                        "y": data["top"][i],
                        "w": data["width"][i],
                        "h": data["height"][i],
                    },
                })

        return results

    def get_average_confidence(
        self,
        image: Union[str, np.ndarray, Image.Image],
        region: Optional[Dict] = None,
    ) -> float:
        """
        Get average OCR confidence for an image.

        Args:
            image: Image source.
            region: Optional region dict.

        Returns:
            Average confidence as float between 0 and 1.
        """
        results = self.extract_with_confidence(image, region)

        if not results:
            return 0.0

        return sum(r["confidence"] for r in results) / len(results)
