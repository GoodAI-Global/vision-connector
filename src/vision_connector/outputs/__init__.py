"""Output modules for vision-connector."""

from vision_connector.outputs.csv_writer import CSVWriter
from vision_connector.outputs.mqtt import MQTTOutput
from vision_connector.outputs.webhook import WebhookOutput

__all__ = [
    "MQTTOutput",
    "WebhookOutput",
    "CSVWriter",
]
