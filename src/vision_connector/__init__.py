"""
Vision Connector - Non-invasive industrial data capture using computer vision.

By Good AI - Premium Enterprise AI Consultancy
https://goodai.com

The Problem:
    PLCs are locked, ERPs are ancient, IT won't give API access.
    Legacy systems hold critical data hostage.

The Solution:
    Point a camera at the screen operators already look at.
    Extract data without touching the underlying systems.

This is non-invasive intelligence - bypass legacy constraints without system integration.
"""

__version__ = "0.1.0"
__author__ = "Good AI"

from vision_connector.processors.hmi_reader import HMIReader
from vision_connector.processors.gauge_reader import GaugeReader
from vision_connector.processors.display_reader import DisplayReader
from vision_connector.processors.ocr import OCRProcessor

__all__ = [
    "HMIReader",
    "GaugeReader",
    "DisplayReader",
    "OCRProcessor",
    "__version__",
]
