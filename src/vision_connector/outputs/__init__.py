"""Output modules for vision-connector."""

from vision_connector.outputs.mqtt import MQTTOutput
from vision_connector.outputs.webhook import WebhookOutput
from vision_connector.outputs.csv_writer import CSVWriter

__all__ = [
    "MQTTOutput",
    "WebhookOutput",
    "CSVWriter",
]
