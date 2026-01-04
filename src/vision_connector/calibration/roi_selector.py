"""
ROI (Region of Interest) selector for calibrating vision capture.

Provides both interactive GUI selection (when display available)
and programmatic ROI management.
Works headless when using programmatic methods.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image

from vision_connector.utils.image_utils import load_image


class ROISelector:
    """
    Region of Interest selector for calibrating data extraction.

    Provides methods for defining, saving, and loading ROI configurations.
    GUI methods require a display; programmatic methods work headless.

    Example (headless):
        >>> selector = ROISelector()
        >>> selector.add_region("temperature", x=100, y=200, w=80, h=30)
        >>> selector.save_config("config.json")

    Example (with display):
        >>> selector = ROISelector()
        >>> selector.select_interactive("image.png")
        >>> selector.save_config("config.json")
    """

    def __init__(self):
        """Initialize the ROI selector."""
        self.regions: Dict[str, Dict] = {}
        self._image: Optional[np.ndarray] = None

    def add_region(
        self,
        name: str,
        x: int,
        y: int,
        w: int,
        h: int,
        region_type: str = "auto",
    ) -> None:
        """
        Add a region programmatically.

        Args:
            name: Field name for this region.
            x: X coordinate of top-left corner.
            y: Y coordinate of top-left corner.
            w: Width of region.
            h: Height of region.
            region_type: Type of data ("number", "text", or "auto").
        """
        if w <= 0 or h <= 0:
            raise ValueError(f"Region dimensions must be positive: w={w}, h={h}")

        self.regions[name] = {
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "type": region_type,
        }

    def remove_region(self, name: str) -> bool:
        """
        Remove a region by name.

        Args:
            name: Field name to remove.

        Returns:
            True if region was removed, False if not found.
        """
        if name in self.regions:
            del self.regions[name]
            return True
        return False

    def get_region(self, name: str) -> Optional[Dict]:
        """
        Get a region by name.

        Args:
            name: Field name.

        Returns:
            Region dict or None if not found.
        """
        return self.regions.get(name)

    def list_regions(self) -> List[str]:
        """
        List all region names.

        Returns:
            List of region names.
        """
        return list(self.regions.keys())

    def select_interactive(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
    ) -> Dict[str, Dict]:
        """
        Interactively select multiple regions using GUI.

        REQUIRES a display. For headless environments, use add_region() instead.

        Args:
            image: Image to select regions from.

        Returns:
            Dictionary of selected regions.

        Raises:
            RuntimeError: If no display is available.
        """
        # Check for display
        if not self._has_display():
            raise RuntimeError(
                "No display available for interactive ROI selection.\n"
                "In headless environments (Docker, CI, SSH), use programmatic methods:\n\n"
                "  selector = ROISelector()\n"
                "  selector.add_region('temperature', x=100, y=200, w=80, h=30)\n"
                "  selector.add_region('pressure', x=100, y=250, w=80, h=30)\n"
                "  selector.save_config('config.json')\n\n"
                "Or load from existing config:\n"
                "  selector.load_config('config.json')"
            )

        self._image = load_image(image)

        print("Interactive ROI Selection")
        print("=" * 40)
        print("Instructions:")
        print("  - Draw a rectangle around each region")
        print("  - Press ENTER to confirm selection")
        print("  - Press 'c' to cancel current selection")
        print("  - Press 'q' to quit and save")
        print("=" * 40)

        window_name = "ROI Selection - Press Q to finish"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        while True:
            # Get region name
            name = input("\nEnter region name (or 'done' to finish): ").strip()

            if name.lower() == "done" or name.lower() == "q":
                break

            if not name:
                print("Region name cannot be empty.")
                continue

            if name in self.regions:
                print(f"Region '{name}' already exists. Choose a different name.")
                continue

            # Select ROI
            print(f"Select region for '{name}' in the image window...")
            roi = cv2.selectROI(window_name, self._image, fromCenter=False, showCrosshair=True)

            x, y, w, h = roi

            if w == 0 or h == 0:
                print("Selection cancelled.")
                continue

            # Get region type
            region_type = input("Region type (number/text/auto) [auto]: ").strip().lower()
            if region_type not in ("number", "text", "auto", ""):
                region_type = "auto"
            if not region_type:
                region_type = "auto"

            self.add_region(name, int(x), int(y), int(w), int(h), region_type)
            print(f"Added region '{name}': x={x}, y={y}, w={w}, h={h}, type={region_type}")

        cv2.destroyWindow(window_name)

        return self.regions

    def select_single(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        name: str = "region",
    ) -> Dict:
        """
        Select a single region interactively.

        REQUIRES a display.

        Args:
            image: Image to select from.
            name: Name for the region.

        Returns:
            Region dict with x, y, w, h keys.
        """
        if not self._has_display():
            raise RuntimeError(
                "No display available. Use add_region() programmatically:\n"
                f"  selector.add_region('{name}', x=100, y=200, w=80, h=30)"
            )

        img = load_image(image)

        window_name = f"Select '{name}' - Press ENTER when done"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        roi = cv2.selectROI(window_name, img, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow(window_name)

        x, y, w, h = roi

        if w == 0 or h == 0:
            raise ValueError("No region selected.")

        region = {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
        self.regions[name] = region

        return region

    def save_config(
        self,
        filepath: Union[str, Path],
        include_capture: bool = False,
        image_path: Optional[str] = None,
    ) -> None:
        """
        Save regions to a JSON config file.

        Args:
            filepath: Path to save config file.
            include_capture: Whether to include capture section.
            image_path: Optional image path for capture section.
        """
        config = {"regions": self.regions}

        if include_capture and image_path:
            config["capture"] = {
                "source": "image",
                "path": image_path,
            }

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w") as f:
            json.dump(config, f, indent=2)

    def load_config(self, filepath: Union[str, Path]) -> Dict[str, Dict]:
        """
        Load regions from a JSON config file.

        Args:
            filepath: Path to config file.

        Returns:
            Dictionary of loaded regions.

        Raises:
            FileNotFoundError: If config file doesn't exist.
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")

        with open(filepath, "r") as f:
            config = json.load(f)

        if "regions" in config:
            self.regions = config["regions"]
        else:
            # Assume the entire config is regions
            self.regions = config

        return self.regions

    def validate_regions(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
    ) -> List[str]:
        """
        Validate that all regions fit within the image.

        Args:
            image: Image to validate against.

        Returns:
            List of validation error messages (empty if all valid).
        """
        img = load_image(image)
        height, width = img.shape[:2]

        errors = []

        for name, region in self.regions.items():
            x, y, w, h = region["x"], region["y"], region["w"], region["h"]

            if x < 0 or y < 0:
                errors.append(f"Region '{name}': Position cannot be negative (x={x}, y={y})")

            if x + w > width:
                errors.append(
                    f"Region '{name}': Extends beyond image width "
                    f"(x={x} + w={w} = {x+w} > {width})"
                )

            if y + h > height:
                errors.append(
                    f"Region '{name}': Extends beyond image height "
                    f"(y={y} + h={h} = {y+h} > {height})"
                )

        return errors

    def preview_regions(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        output_path: Optional[Union[str, Path]] = None,
    ) -> np.ndarray:
        """
        Create a preview image with regions drawn.

        Works headless - saves to file if no display.

        Args:
            image: Source image.
            output_path: Optional path to save preview image.

        Returns:
            Image with regions drawn.
        """
        img = load_image(image).copy()

        colors = [
            (0, 255, 0),    # Green
            (255, 0, 0),    # Blue
            (0, 0, 255),    # Red
            (255, 255, 0),  # Cyan
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Yellow
        ]

        for i, (name, region) in enumerate(self.regions.items()):
            color = colors[i % len(colors)]
            x, y, w, h = region["x"], region["y"], region["w"], region["h"]

            # Draw rectangle
            cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)

            # Draw label
            label = f"{name}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1

            (label_w, label_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

            # Draw label background
            cv2.rectangle(
                img,
                (x, y - label_h - 5),
                (x + label_w + 4, y),
                color,
                -1,
            )

            # Draw label text
            cv2.putText(
                img,
                label,
                (x + 2, y - 3),
                font,
                font_scale,
                (255, 255, 255),
                thickness,
            )

        if output_path:
            cv2.imwrite(str(output_path), img)

        return img

    def _has_display(self) -> bool:
        """Check if a display is available."""
        # Check DISPLAY environment variable on Linux/macOS
        if os.name == "posix":
            return bool(os.environ.get("DISPLAY"))

        # On Windows, display is typically available
        return os.name == "nt"

    def clear(self) -> None:
        """Clear all regions."""
        self.regions.clear()

    def __len__(self) -> int:
        """Return number of regions."""
        return len(self.regions)

    def __contains__(self, name: str) -> bool:
        """Check if region exists."""
        return name in self.regions
