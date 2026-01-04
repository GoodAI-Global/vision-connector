"""
Gauge Reader for extracting values from analog gauges.

Uses computer vision to detect needle position and calculate values.
Works headless - no display required.
"""

import math
from typing import Dict, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image

from vision_connector.utils.image_utils import load_image, crop_region


class GaugeReader:
    """
    Reader for extracting values from analog gauges.

    Detects the needle position in circular gauges and calculates
    the corresponding value based on min/max range.

    Example:
        >>> reader = GaugeReader()
        >>> result = reader.read_analog_gauge(
        ...     "gauge.png",
        ...     min_value=0,
        ...     max_value=100,
        ...     unit="PSI"
        ... )
        >>> print(result)
        {"value": 67.5, "unit": "PSI", "confidence": 0.92}
    """

    def __init__(
        self,
        min_angle: float = 45,
        max_angle: float = 315,
    ):
        """
        Initialize the gauge reader.

        Args:
            min_angle: Angle (degrees) corresponding to minimum value.
                       0° is right, 90° is down, measured clockwise.
                       Default: 45° (typical gauge minimum position).
            max_angle: Angle (degrees) corresponding to maximum value.
                       Default: 315° (typical gauge maximum position).
        """
        self.min_angle = min_angle
        self.max_angle = max_angle

    def read_analog_gauge(
        self,
        image: Union[str, np.ndarray, Image.Image],
        min_value: float = 0,
        max_value: float = 100,
        unit: str = "",
        region: Optional[Dict] = None,
    ) -> Dict:
        """
        Read value from an analog gauge image.

        Args:
            image: Image source (path, numpy array, or PIL Image).
            min_value: Value at minimum position (default: 0).
            max_value: Value at maximum position (default: 100).
            unit: Unit label for the reading (default: "").
            region: Optional region to crop before processing.

        Returns:
            Dictionary with:
                - value: Extracted gauge value
                - unit: Unit label
                - confidence: Confidence score (0-1)
                - angle: Detected needle angle in degrees
        """
        img = load_image(image)

        if region:
            img = crop_region(img, region)

        # Find gauge center and radius
        center, radius = self._find_gauge_circle(img)

        if center is None:
            return {
                "value": None,
                "unit": unit,
                "confidence": 0.0,
                "angle": None,
                "error": "Could not detect gauge circle",
            }

        # Detect needle angle
        angle, confidence = self._detect_needle_angle(img, center, radius)

        if angle is None:
            return {
                "value": None,
                "unit": unit,
                "confidence": 0.0,
                "angle": None,
                "error": "Could not detect needle",
            }

        # Calculate value from angle
        value = self._angle_to_value(angle, min_value, max_value)

        return {
            "value": round(value, 2),
            "unit": unit,
            "confidence": round(confidence, 3),
            "angle": round(angle, 2),
        }

    def _find_gauge_circle(
        self,
        image: np.ndarray,
    ) -> Tuple[Optional[Tuple[int, int]], Optional[int]]:
        """
        Find the main circular outline of the gauge.

        Returns:
            Tuple of (center, radius) or (None, None) if not found.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Apply blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)

        # Detect circles using Hough transform
        height, width = gray.shape[:2]
        min_radius = min(height, width) // 6
        max_radius = min(height, width) // 2

        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=max_radius,
            param1=50,
            param2=30,
            minRadius=min_radius,
            maxRadius=max_radius,
        )

        if circles is None:
            # Fallback: assume gauge is centered in image
            center = (width // 2, height // 2)
            radius = min(height, width) // 2 - 10
            return center, radius

        # Take the largest circle (most likely the gauge)
        circles = np.uint16(np.around(circles))
        largest = max(circles[0], key=lambda c: c[2])

        center = (int(largest[0]), int(largest[1]))
        radius = int(largest[2])

        return center, radius

    def _detect_needle_angle(
        self,
        image: np.ndarray,
        center: Tuple[int, int],
        radius: int,
    ) -> Tuple[Optional[float], float]:
        """
        Detect the angle of the gauge needle.

        Args:
            image: Source image.
            center: Gauge center (x, y).
            radius: Gauge radius.

        Returns:
            Tuple of (angle in degrees, confidence).
            Angle is measured from right (0°), clockwise.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Create mask for the gauge area
        mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.circle(mask, center, int(radius * 0.9), 255, -1)

        # Apply mask
        masked = cv2.bitwise_and(gray, gray, mask=mask)

        # Edge detection
        edges = cv2.Canny(masked, 50, 150)

        # Detect lines using Hough transform
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=30,
            minLineLength=int(radius * 0.3),
            maxLineGap=10,
        )

        if lines is None:
            return None, 0.0

        # Find lines that pass near center (likely the needle)
        needle_candidates = []

        for line in lines:
            x1, y1, x2, y2 = line[0]

            # Calculate distance from line to center
            dist = self._point_to_line_distance(center, (x1, y1), (x2, y2))

            if dist < radius * 0.15:  # Line passes near center
                # Calculate angle of this line
                angle = math.atan2(y2 - y1, x2 - x1)
                angle_deg = math.degrees(angle)

                # Calculate line length
                length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

                # Determine which end is the needle tip (farther from center)
                dist1 = math.sqrt((x1 - center[0]) ** 2 + (y1 - center[1]) ** 2)
                dist2 = math.sqrt((x2 - center[0]) ** 2 + (y2 - center[1]) ** 2)

                if dist2 > dist1:
                    tip = (x2, y2)
                else:
                    tip = (x1, y1)
                    angle_deg += 180  # Flip angle

                # Normalize angle to 0-360
                angle_deg = angle_deg % 360

                needle_candidates.append({
                    "angle": angle_deg,
                    "length": length,
                    "tip": tip,
                })

        if not needle_candidates:
            return None, 0.0

        # Weight by line length (longer lines more likely to be needle)
        total_length = sum(c["length"] for c in needle_candidates)

        weighted_angle = 0
        for c in needle_candidates:
            weight = c["length"] / total_length
            weighted_angle += c["angle"] * weight

        # Calculate confidence based on consistency
        if len(needle_candidates) == 1:
            confidence = 0.7
        else:
            angle_variance = np.var([c["angle"] for c in needle_candidates])
            confidence = max(0.5, 1.0 - angle_variance / 1000)

        return weighted_angle, confidence

    def _point_to_line_distance(
        self,
        point: Tuple[int, int],
        line_start: Tuple[int, int],
        line_end: Tuple[int, int],
    ) -> float:
        """Calculate perpendicular distance from point to line."""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end

        numerator = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
        denominator = math.sqrt((y2 - y1) ** 2 + (x2 - x1) ** 2)

        if denominator == 0:
            return float("inf")

        return numerator / denominator

    def _angle_to_value(
        self,
        angle: float,
        min_value: float,
        max_value: float,
    ) -> float:
        """
        Convert needle angle to gauge value.

        Args:
            angle: Needle angle in degrees (0° = right, clockwise).
            min_value: Value at min_angle.
            max_value: Value at max_angle.

        Returns:
            Calculated gauge value.
        """
        # Calculate the angular range
        if self.max_angle > self.min_angle:
            angle_range = self.max_angle - self.min_angle
        else:
            angle_range = (360 - self.min_angle) + self.max_angle

        # Calculate relative position in angle range
        if angle >= self.min_angle:
            relative_angle = angle - self.min_angle
        else:
            relative_angle = (360 - self.min_angle) + angle

        # Clamp to valid range
        relative_angle = max(0, min(relative_angle, angle_range))

        # Calculate value
        ratio = relative_angle / angle_range
        value = min_value + ratio * (max_value - min_value)

        return value

    def calibrate(
        self,
        image: Union[str, np.ndarray, Image.Image],
        known_value: float,
        min_value: float,
        max_value: float,
    ) -> Dict:
        """
        Calibrate gauge reading using a known value.

        Takes an image where the gauge shows a known value and
        adjusts the angle mapping accordingly.

        Args:
            image: Calibration image.
            known_value: The actual value shown on the gauge.
            min_value: Minimum value of gauge scale.
            max_value: Maximum value of gauge scale.

        Returns:
            Calibration data dict with detected parameters.
        """
        img = load_image(image)
        center, radius = self._find_gauge_circle(img)

        if center is None:
            return {"error": "Could not detect gauge circle"}

        detected_angle, confidence = self._detect_needle_angle(img, center, radius)

        if detected_angle is None:
            return {"error": "Could not detect needle"}

        # Calculate what the angle should be for this value
        expected_ratio = (known_value - min_value) / (max_value - min_value)

        return {
            "detected_angle": detected_angle,
            "expected_ratio": expected_ratio,
            "center": center,
            "radius": radius,
            "confidence": confidence,
        }
