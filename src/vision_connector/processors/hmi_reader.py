"""
HMI Screen Reader for extracting data from industrial HMI screens.

Reads values from defined regions on HMI screens, SCADA displays,
and other industrial interfaces using computer vision and OCR.
Works headless - no display required.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
from PIL import Image

from vision_connector.exceptions import (
    ImageProcessingError,
    NoDisplayError,
    RegionError,
)
from vision_connector.logging import get_logger
from vision_connector.processors.ocr import OCRProcessor
from vision_connector.utils.image_utils import load_image

# Module logger
_logger = get_logger(__name__)


class HMIReader:
    """
    Reader for extracting data from HMI (Human-Machine Interface) screens.

    Extracts values from defined regions on industrial display screenshots.
    Supports both numeric and text values with automatic type detection.

    Example:
        >>> reader = HMIReader()
        >>> result = reader.read_image(
        ...     "screenshot.png",
        ...     regions={
        ...         "temperature": {"x": 100, "y": 200, "w": 80, "h": 30},
        ...         "pressure": {"x": 100, "y": 250, "w": 80, "h": 30},
        ...         "status": {"x": 300, "y": 100, "w": 100, "h": 40}
        ...     }
        ... )
        >>> print(result)
        {"temperature": "185.5", "pressure": "42.3", "status": "RUNNING"}
    """

    def __init__(
        self,
        config: Optional[Union[str, Path, Dict]] = None,
        tesseract_cmd: Optional[str] = None,
    ):
        """
        Initialize the HMI reader.

        Args:
            config: Optional configuration. Can be:
                - Path to JSON config file (str or Path)
                - Dictionary with configuration
                - None for manual region specification
            tesseract_cmd: Optional path to tesseract executable.

        Raises:
            FileNotFoundError: If config file path doesn't exist.
            ValueError: If config is invalid.
        """
        _logger.debug("Initializing HMIReader", tesseract_cmd=tesseract_cmd)

        self.ocr = OCRProcessor(tesseract_cmd=tesseract_cmd)
        self.config: Dict[str, Any] = {}
        self.default_regions: Dict[str, Dict] = {}

        if config:
            self._load_config(config)

        _logger.info(
            "HMIReader initialized",
            regions_count=len(self.default_regions),
        )

    def _load_config(self, config: Union[str, Path, Dict]) -> None:
        """Load configuration from file or dictionary."""
        if isinstance(config, dict):
            _logger.debug("Loading config from dictionary")
            self.config = config
        else:
            config_path = Path(config)
            _logger.debug("Loading config from file", path=str(config_path))

            if not config_path.exists():
                _logger.error("Configuration file not found", path=str(config_path))
                raise FileNotFoundError(
                    f"Configuration file not found: {config_path}\n"
                    f"Please provide a valid config file path or use regions parameter."
                )

            with open(config_path, "r") as f:
                self.config = json.load(f)

            _logger.debug("Config loaded successfully", path=str(config_path))

        # Extract default regions from config
        if "regions" in self.config:
            self.default_regions = self.config["regions"]
            _logger.debug(
                "Regions extracted from config",
                region_names=list(self.default_regions.keys()),
            )

    def read_image(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        regions: Optional[Dict[str, Dict]] = None,
    ) -> Dict[str, str]:
        """
        Read values from defined regions in an HMI screen image.

        Args:
            image: Image source (path, numpy array, or PIL Image).
            regions: Dictionary mapping field names to region dicts.
                Each region dict must have: x, y, w, h.
                Optional keys: type ("number" or "text").

        Returns:
            Dictionary mapping field names to extracted values as strings.

        Raises:
            ValueError: If no regions are specified and no default config.
            FileNotFoundError: If image path doesn't exist.
        """
        with _logger.operation("read_image"):
            # Determine which regions to use
            active_regions = regions if regions is not None else self.default_regions

            if not active_regions:
                _logger.error("No regions specified for reading")
                raise RegionError(
                    "No regions specified. Provide regions via:\n"
                    "  1. regions parameter: reader.read_image(img, regions={...})\n"
                    "  2. config file: HMIReader(config='config.json')\n"
                    "  3. config dict: HMIReader(config={'regions': {...}})\n\n"
                    "Region format: {'field_name': {'x': 0, 'y': 0, 'w': 100, 'h': 50}}"
                )

            # Log image source
            image_source = (
                str(image) if isinstance(image, (str, Path)) else type(image).__name__
            )
            _logger.debug(
                "Reading HMI image",
                source=image_source,
                regions_count=len(active_regions),
            )

            # Load the image
            img = load_image(image)
            _logger.debug("Image loaded", shape=img.shape)

            # Extract values from each region
            results: Dict[str, str] = {}

            for field_name, region_config in active_regions.items():
                value = self._extract_region_value(img, region_config)
                results[field_name] = value
                _logger.debug(
                    "Extracted region value",
                    field=field_name,
                    value=value,
                    region=region_config,
                )

            _logger.info(
                "HMI image read complete",
                fields_extracted=len(results),
                field_names=list(results.keys()),
            )

            return results

    def _extract_region_value(
        self,
        image: np.ndarray,
        region_config: Dict,
    ) -> str:
        """Extract value from a single region."""
        # Get region type (default to auto-detect)
        region_type = region_config.get("type", "auto")

        # Extract base region coordinates
        region = {
            "x": region_config["x"],
            "y": region_config["y"],
            "w": region_config["w"],
            "h": region_config["h"],
        }

        if region_type == "number":
            # Use numeric extraction
            number = self.ocr.extract_single_number(image, region=region)
            if number is not None:
                # Format nicely (remove trailing zeros for integers)
                if number == int(number):
                    return str(int(number))
                return str(number)
            return ""

        elif region_type == "text":
            # Use text extraction
            return self.ocr.extract_text(image, region=region)

        else:
            # Auto-detect: try number first, fall back to text
            text = self.ocr.extract_text(image, region=region)
            return text

    def read_image_with_metadata(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        regions: Optional[Dict[str, Dict]] = None,
    ) -> Dict[str, Dict]:
        """
        Read values with confidence scores and metadata.

        Args:
            image: Image source.
            regions: Optional region definitions.

        Returns:
            Dictionary with field names mapping to dicts containing:
                - value: Extracted value
                - confidence: OCR confidence (0-1)
                - region: Region coordinates used
        """
        with _logger.operation("read_image_with_metadata"):
            active_regions = regions if regions is not None else self.default_regions

            if not active_regions:
                _logger.error("No regions specified")
                raise RegionError("No regions specified.")

            img = load_image(image)
            results: Dict[str, Dict] = {}

            for field_name, region_config in active_regions.items():
                region = {
                    "x": region_config["x"],
                    "y": region_config["y"],
                    "w": region_config["w"],
                    "h": region_config["h"],
                }

                value = self._extract_region_value(img, region_config)
                confidence = self.ocr.get_average_confidence(img, region=region)

                results[field_name] = {
                    "value": value,
                    "confidence": round(confidence, 3),
                    "region": region,
                }

                _logger.debug(
                    "Extracted region with metadata",
                    field=field_name,
                    value=value,
                    confidence=confidence,
                )

            _logger.info(
                "HMI image read with metadata complete",
                fields_extracted=len(results),
            )

            return results

    def select_roi_interactive(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
    ) -> Dict[str, int]:
        """
        Interactively select a region of interest (ROI) using GUI.

        This method REQUIRES a display. For headless environments,
        use config files or the regions parameter instead.

        Args:
            image: Image to select ROI from.

        Returns:
            Region dict with x, y, w, h keys.

        Raises:
            RuntimeError: If no display is available.
        """
        _logger.debug("Starting interactive ROI selection")

        # Check for display availability
        display = os.environ.get("DISPLAY")

        if not display and os.name != "nt":  # Not Windows and no DISPLAY
            _logger.error("No display available for interactive ROI selection")
            raise NoDisplayError(
                "No display available for interactive ROI selection.\n"
                "In headless environments, specify ROI via:\n"
                "  1. Config file: HMIReader(config='config.json')\n"
                "  2. Direct regions: reader.read_image(img, regions={...})\n\n"
                "Example region: {'x': 100, 'y': 200, 'w': 80, 'h': 30}"
            )

        # Import cv2 with GUI support (will fail in headless)
        try:
            import cv2
        except ImportError as e:
            _logger.error("OpenCV not available for GUI operations")
            raise ImageProcessingError(
                "OpenCV not available for GUI operations.",
                original_error=e,
            ) from e

        img = load_image(image)

        # Use OpenCV's selectROI
        window_name = "Select Region - Press ENTER when done, C to cancel"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        roi = cv2.selectROI(window_name, img, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow(window_name)

        x, y, w, h = roi

        if w == 0 or h == 0:
            _logger.warning("ROI selection cancelled or invalid")
            raise RegionError("No region selected (cancelled or invalid selection).")

        result = {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
        _logger.info("ROI selected", region=result)

        return result

    @staticmethod
    def create_sample_config(output_path: Union[str, Path]) -> None:
        """
        Create a sample configuration file.

        Args:
            output_path: Path where to write the sample config.
        """
        _logger.debug("Creating sample config", path=str(output_path))

        sample_config = {
            "capture": {
                "source": "image",
                "path": "sample_images/hmi_screen.png",
            },
            "regions": {
                "temperature": {
                    "x": 100,
                    "y": 200,
                    "w": 80,
                    "h": 30,
                    "type": "number",
                },
                "pressure": {
                    "x": 100,
                    "y": 250,
                    "w": 80,
                    "h": 30,
                    "type": "number",
                },
                "status": {
                    "x": 300,
                    "y": 100,
                    "w": 100,
                    "h": 40,
                    "type": "text",
                },
            },
            "output": {
                "type": "csv",
                "path": "output/readings.csv",
            },
        }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(sample_config, f, indent=2)

        _logger.info("Sample config created", path=str(output_path))
