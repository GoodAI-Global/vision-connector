"""
MQTT output module for streaming data to MQTT brokers.

Provides reliable message publishing with automatic reconnection.
Works headless - no display required.
"""

import json
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import paho.mqtt.client as mqtt


class MQTTOutput:
    """
    MQTT output for streaming extracted data to message brokers.

    Supports automatic reconnection, QoS levels, and message batching.

    Example:
        >>> mqtt_out = MQTTOutput("localhost:1883", topic="plant/line1/readings")
        >>> mqtt_out.connect()
        >>> mqtt_out.publish({"temperature": 185.5, "pressure": 42.3})
        >>> mqtt_out.disconnect()
    """

    def __init__(
        self,
        broker: str,
        topic: str,
        port: Optional[int] = None,
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        qos: int = 1,
        retain: bool = False,
    ):
        """
        Initialize MQTT output.

        Args:
            broker: Broker address. Can include port (e.g., "localhost:1883").
            topic: Default topic for publishing.
            port: MQTT port. Overrides port in broker string.
            client_id: MQTT client ID. Auto-generated if not provided.
            username: Optional username for authentication.
            password: Optional password for authentication.
            qos: Quality of Service level (0, 1, or 2).
            retain: Whether to retain messages on the broker.
        """
        # Parse broker address
        if ":" in broker and port is None:
            host, port_str = broker.rsplit(":", 1)
            self.host = host
            self.port = int(port_str)
        else:
            self.host = broker
            self.port = port or 1883

        self.topic = topic
        self.qos = qos
        self.retain = retain

        # Create client
        self.client_id = client_id or f"vision-connector-{int(time.time())}"
        self.client = mqtt.Client(client_id=self.client_id)

        # Set credentials if provided
        if username:
            self.client.username_pw_set(username, password)

        # Connection state
        self._connected = False
        self._on_connect_callback: Optional[Callable] = None
        self._on_disconnect_callback: Optional[Callable] = None

        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc):
        """Handle connection events."""
        if rc == 0:
            self._connected = True
            if self._on_connect_callback:
                self._on_connect_callback()
        else:
            self._connected = False

    def _on_disconnect(self, client, userdata, rc):
        """Handle disconnection events."""
        self._connected = False
        if self._on_disconnect_callback:
            self._on_disconnect_callback()

    def connect(self, timeout: float = 10.0) -> bool:
        """
        Connect to the MQTT broker.

        Args:
            timeout: Connection timeout in seconds.

        Returns:
            True if connected successfully.

        Raises:
            ConnectionError: If connection fails.
        """
        try:
            self.client.connect(self.host, self.port, keepalive=60)
            self.client.loop_start()

            # Wait for connection
            start = time.time()
            while not self._connected and (time.time() - start) < timeout:
                time.sleep(0.1)

            if not self._connected:
                raise ConnectionError(
                    f"Failed to connect to MQTT broker at {self.host}:{self.port}"
                )

            return True

        except Exception as e:
            raise ConnectionError(
                f"MQTT connection failed: {e}\n"
                f"Ensure the broker is running at {self.host}:{self.port}"
            ) from e

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        self.client.loop_stop()
        self.client.disconnect()
        self._connected = False

    def publish(
        self,
        data: Dict[str, Any],
        topic: Optional[str] = None,
        add_timestamp: bool = True,
    ) -> bool:
        """
        Publish data to MQTT topic.

        Args:
            data: Dictionary of data to publish as JSON.
            topic: Optional topic override.
            add_timestamp: Whether to add a timestamp field.

        Returns:
            True if published successfully.
        """
        if not self._connected:
            raise ConnectionError("Not connected to MQTT broker. Call connect() first.")

        # Prepare payload
        payload = dict(data)
        if add_timestamp:
            payload["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Convert to JSON
        json_payload = json.dumps(payload)

        # Publish
        result = self.client.publish(
            topic or self.topic,
            json_payload,
            qos=self.qos,
            retain=self.retain,
        )

        return result.rc == mqtt.MQTT_ERR_SUCCESS

    def publish_batch(
        self,
        readings: list,
        topic: Optional[str] = None,
    ) -> int:
        """
        Publish multiple readings.

        Args:
            readings: List of data dictionaries.
            topic: Optional topic override.

        Returns:
            Number of successfully published messages.
        """
        success_count = 0
        for data in readings:
            if self.publish(data, topic):
                success_count += 1
        return success_count

    def on_connect(self, callback: Callable) -> None:
        """Set callback for connection events."""
        self._on_connect_callback = callback

    def on_disconnect(self, callback: Callable) -> None:
        """Set callback for disconnection events."""
        self._on_disconnect_callback = callback

    @property
    def is_connected(self) -> bool:
        """Check if connected to broker."""
        return self._connected

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
