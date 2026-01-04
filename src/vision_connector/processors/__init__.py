"""Image processing modules for vision-connector."""

from vision_connector.processors.ocr import OCRProcessor
from vision_connector.processors.hmi_reader import HMIReader
from vision_connector.processors.gauge_reader import GaugeReader
from vision_connector.processors.display_reader import DisplayReader

__all__ = [
    "OCRProcessor",
    "HMIReader",
    "GaugeReader",
    "DisplayReader",
]
