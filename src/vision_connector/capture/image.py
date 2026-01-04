"""
Image capture module for file-based image sources.

Provides utilities for loading images from files and directories.
Works headless - no display required.
"""

import time
from pathlib import Path
from typing import Generator, List, Optional, Union

import cv2
import numpy as np
from PIL import Image


class ImageCapture:
    """
    Image capture from files and directories.

    Provides a consistent interface for loading images from various
    file sources, with optional watch mode for monitoring directories.

    Example:
        >>> # Single image
        >>> cap = ImageCapture("screenshot.png")
        >>> img = cap.read()
        >>>
        >>> # Directory of images
        >>> cap = ImageCapture("images/", pattern="*.png")
        >>> for img, path in cap.iterate():
        ...     process(img)
    """

    SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}

    def __init__(
        self,
        source: Union[str, Path],
        pattern: str = "*",
    ):
        """
        Initialize image capture.

        Args:
            source: Path to image file or directory.
            pattern: Glob pattern for filtering files in directory mode.
        """
        self.source = Path(source)
        self.pattern = pattern

        if not self.source.exists():
            raise FileNotFoundError(f"Image source not found: {self.source}")

    def read(self) -> np.ndarray:
        """
        Read a single image.

        For files, returns the image.
        For directories, returns the first matching image.

        Returns:
            Image as numpy array (BGR).

        Raises:
            ValueError: If source is a directory with no matching images.
        """
        if self.source.is_file():
            return self._load_image(self.source)

        # Directory - get first matching file
        images = self._list_images()
        if not images:
            raise ValueError(
                f"No images found in {self.source} matching pattern '{self.pattern}'"
            )

        return self._load_image(images[0])

    def read_all(self) -> List[np.ndarray]:
        """
        Read all images from source.

        Returns:
            List of images as numpy arrays.
        """
        if self.source.is_file():
            return [self._load_image(self.source)]

        images = []
        for path in self._list_images():
            images.append(self._load_image(path))

        return images

    def iterate(self) -> Generator[tuple, None, None]:
        """
        Iterate over images in source.

        Yields:
            Tuples of (image_array, path).
        """
        if self.source.is_file():
            yield self._load_image(self.source), self.source
            return

        for path in self._list_images():
            yield self._load_image(path), path

    def watch(
        self,
        interval: float = 1.0,
        process_existing: bool = True,
    ) -> Generator[tuple, None, None]:
        """
        Watch directory for new images.

        Monitors the source directory and yields new images as they appear.

        Args:
            interval: Check interval in seconds.
            process_existing: Whether to process existing files first.

        Yields:
            Tuples of (image_array, path) for new files.
        """
        if self.source.is_file():
            raise ValueError("Watch mode only works with directories")

        seen = set()

        if process_existing:
            for path in self._list_images():
                seen.add(path)
                yield self._load_image(path), path

        while True:
            current = set(self._list_images())
            new_files = current - seen

            for path in sorted(new_files):
                seen.add(path)
                try:
                    yield self._load_image(path), path
                except Exception:
                    # File might be still being written
                    continue

            time.sleep(interval)

    def _list_images(self) -> List[Path]:
        """List image files in directory."""
        if self.source.is_file():
            return [self.source]

        files = []
        for path in self.source.glob(self.pattern):
            if path.is_file() and path.suffix.lower() in self.SUPPORTED_FORMATS:
                files.append(path)

        return sorted(files)

    def _load_image(self, path: Path) -> np.ndarray:
        """Load image from file."""
        img = cv2.imread(str(path))

        if img is None:
            raise ValueError(f"Failed to load image: {path}")

        return img

    def get_info(self) -> dict:
        """
        Get information about the image source.

        Returns:
            Dictionary with source information.
        """
        if self.source.is_file():
            img = self._load_image(self.source)
            return {
                "type": "file",
                "path": str(self.source),
                "width": img.shape[1],
                "height": img.shape[0],
                "channels": img.shape[2] if len(img.shape) > 2 else 1,
            }

        images = self._list_images()
        return {
            "type": "directory",
            "path": str(self.source),
            "pattern": self.pattern,
            "file_count": len(images),
            "files": [str(p) for p in images[:10]],  # First 10 files
        }


def load_image(source: Union[str, Path, np.ndarray, Image.Image]) -> np.ndarray:
    """
    Load an image from various sources.

    Convenience function that handles multiple input types.

    Args:
        source: Image path, numpy array, or PIL Image.

    Returns:
        Image as numpy array (BGR).
    """
    if isinstance(source, np.ndarray):
        return source

    if isinstance(source, Image.Image):
        img = np.array(source)
        if len(img.shape) == 3 and img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        elif len(img.shape) == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        return img

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Failed to load image: {path}")

    return img
