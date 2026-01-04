"""
Image utility functions for vision-connector.

Provides common image loading, cropping, and preprocessing operations.
All functions work headless - no display required.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple, Union, TypedDict

import cv2
import numpy as np
from PIL import Image


class Region(TypedDict):
    """Type definition for a region of interest (ROI)."""
    x: int
    y: int
    w: int
    h: int


def load_image(source: Union[str, Path, np.ndarray, Image.Image]) -> np.ndarray:
    """
    Load an image from various sources into a numpy array.

    Args:
        source: Can be a file path (str/Path), numpy array, or PIL Image.

    Returns:
        numpy.ndarray: Image in BGR format (OpenCV standard).

    Raises:
        FileNotFoundError: If file path doesn't exist.
        ValueError: If source type is unsupported or image is invalid.
    """
    if isinstance(source, np.ndarray):
        # Already a numpy array
        if source.size == 0:
            raise ValueError("Empty image array provided")
        return source

    if isinstance(source, Image.Image):
        # Convert PIL Image to numpy array
        img_array = np.array(source)
        # Convert RGB to BGR if it's a color image
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        elif len(img_array.shape) == 3 and img_array.shape[2] == 4:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        return img_array

    # Treat as file path
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Failed to load image: {path}. File may be corrupted or unsupported format.")

    return img


def validate_region(region: Dict, image_shape: Tuple[int, ...]) -> Region:
    """
    Validate and normalize a region dictionary.

    Args:
        region: Dictionary with x, y, w, h keys.
        image_shape: Shape of the image (height, width, ...).

    Returns:
        Validated Region dictionary.

    Raises:
        ValueError: If region is invalid or out of bounds.
    """
    required_keys = {"x", "y", "w", "h"}
    if not required_keys.issubset(region.keys()):
        missing = required_keys - set(region.keys())
        raise ValueError(f"Region missing required keys: {missing}. Required: x, y, w, h")

    x, y, w, h = int(region["x"]), int(region["y"]), int(region["w"]), int(region["h"])

    if w <= 0 or h <= 0:
        raise ValueError(f"Region dimensions must be positive. Got w={w}, h={h}")

    if x < 0 or y < 0:
        raise ValueError(f"Region position cannot be negative. Got x={x}, y={y}")

    img_height, img_width = image_shape[:2]

    if x + w > img_width or y + h > img_height:
        raise ValueError(
            f"Region extends beyond image bounds. "
            f"Region: x={x}, y={y}, w={w}, h={h}. "
            f"Image: {img_width}x{img_height}"
        )

    return Region(x=x, y=y, w=w, h=h)


def crop_region(image: np.ndarray, region: Dict) -> np.ndarray:
    """
    Crop a region from an image.

    Args:
        image: Source image as numpy array.
        region: Dictionary with x, y, w, h keys.

    Returns:
        Cropped image region.

    Raises:
        ValueError: If region is invalid.
    """
    validated = validate_region(region, image.shape)
    x, y, w, h = validated["x"], validated["y"], validated["w"], validated["h"]
    return image[y:y+h, x:x+w].copy()


def preprocess_for_ocr(
    image: np.ndarray,
    invert: bool = False,
    threshold: bool = True,
    denoise: bool = True,
    scale_factor: float = 2.0,
) -> np.ndarray:
    """
    Preprocess an image for better OCR accuracy.

    Args:
        image: Input image (BGR or grayscale).
        invert: Invert colors (useful for light text on dark background).
        threshold: Apply adaptive thresholding.
        denoise: Apply denoising filter.
        scale_factor: Scale up image for better OCR (default 2x).

    Returns:
        Preprocessed grayscale image optimized for OCR.
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Scale up for better OCR accuracy
    if scale_factor != 1.0:
        new_width = int(gray.shape[1] * scale_factor)
        new_height = int(gray.shape[0] * scale_factor)
        gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

    # Denoise
    if denoise:
        gray = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

    # Invert if needed (light text on dark background)
    if invert:
        gray = cv2.bitwise_not(gray)

    # Apply adaptive thresholding for better text extraction
    if threshold:
        gray = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11,
            C=2
        )

    return gray


def detect_text_color_scheme(image: np.ndarray) -> str:
    """
    Detect if image has light text on dark background or vice versa.

    Args:
        image: Input image.

    Returns:
        "light_on_dark" or "dark_on_light"
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Calculate mean brightness
    mean_val = np.mean(gray)

    # If mean is low, background is dark (light text on dark)
    return "light_on_dark" if mean_val < 127 else "dark_on_light"


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    """
    Enhance image contrast using CLAHE.

    Args:
        image: Input image (BGR or grayscale).

    Returns:
        Contrast-enhanced image.
    """
    if len(image.shape) == 3:
        # Convert to LAB color space for better contrast enhancement
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)

        # Merge back
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    else:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(image)
