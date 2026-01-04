"""
Camera capture module for live video feeds.

Provides a simple interface for capturing frames from cameras,
IP cameras, and video streams.
Works headless - no display required.
"""

from typing import Generator, Optional, Tuple, Union

import cv2
import numpy as np


class CameraCapture:
    """
    Camera capture interface for industrial vision applications.

    Supports USB cameras, IP cameras (RTSP/HTTP), and video files.
    Works entirely headless - no display required.

    Example:
        >>> # USB camera
        >>> cam = CameraCapture(0)
        >>> frame = cam.read()
        >>>
        >>> # IP camera
        >>> cam = CameraCapture("rtsp://192.168.1.100:554/stream")
        >>> for frame in cam.stream():
        ...     process(frame)
    """

    def __init__(
        self,
        source: Union[int, str] = 0,
        resolution: Optional[Tuple[int, int]] = None,
        fps: Optional[int] = None,
    ):
        """
        Initialize camera capture.

        Args:
            source: Camera source. Can be:
                - Integer (0, 1, ...) for USB camera index
                - String URL for IP camera (RTSP, HTTP)
                - String path for video file
            resolution: Optional (width, height) tuple.
            fps: Optional frames per second limit.
        """
        self.source = source
        self.resolution = resolution
        self.fps = fps
        self._cap: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        """
        Open the camera connection.

        Returns:
            True if successfully opened, False otherwise.
        """
        self._cap = cv2.VideoCapture(self.source)

        if not self._cap.isOpened():
            return False

        # Set resolution if specified
        if self.resolution:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

        # Set FPS if specified
        if self.fps:
            self._cap.set(cv2.CAP_PROP_FPS, self.fps)

        return True

    def close(self) -> None:
        """Close the camera connection."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def read(self) -> Optional[np.ndarray]:
        """
        Capture a single frame.

        Returns:
            Frame as numpy array (BGR), or None if capture failed.
        """
        if self._cap is None:
            if not self.open():
                raise RuntimeError(
                    f"Failed to open camera source: {self.source}\n"
                    f"For USB cameras, ensure the camera is connected.\n"
                    f"For IP cameras, verify the URL and network connectivity."
                )

        ret, frame = self._cap.read()

        if not ret:
            return None

        return frame

    def stream(
        self,
        max_frames: Optional[int] = None,
    ) -> Generator[np.ndarray, None, None]:
        """
        Generate continuous stream of frames.

        Args:
            max_frames: Optional limit on number of frames to capture.

        Yields:
            Frames as numpy arrays (BGR).
        """
        if self._cap is None:
            if not self.open():
                raise RuntimeError(f"Failed to open camera source: {self.source}")

        frame_count = 0

        while True:
            ret, frame = self._cap.read()

            if not ret:
                break

            yield frame

            frame_count += 1
            if max_frames and frame_count >= max_frames:
                break

    def get_info(self) -> dict:
        """
        Get camera/stream information.

        Returns:
            Dictionary with camera properties.
        """
        if self._cap is None:
            if not self.open():
                return {"error": "Could not open camera"}

        return {
            "width": int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": self._cap.get(cv2.CAP_PROP_FPS),
            "backend": self._cap.getBackendName(),
            "source": str(self.source),
        }

    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __del__(self):
        """Destructor to ensure camera is released."""
        self.close()


def list_cameras(max_index: int = 10) -> list:
    """
    List available camera indices.

    Args:
        max_index: Maximum camera index to check.

    Returns:
        List of available camera indices.
    """
    available = []

    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available.append(i)
            cap.release()

    return available
