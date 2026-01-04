"""
MQTT output module for streaming data to MQTT brokers.

Provides reliable message publishing with TLS support and automatic reconnection.
Works headless - no display required.
"""

import json
import re
import ssl
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

import paho.mqtt.client as mqtt


class MQTTOutput:
    """
    MQTT output for streaming extracted data to message brokers.

    Supports TLS encryption, automatic reconnection, QoS levels, and message batching.

    Example:
        >>> mqtt_out = MQTTOutput("localhost:1883", topic="plant/line1/readings")
        >>> mqtt_out.connect()
        >>> mqtt_out.publish({"temperature": 185.5, "pressure": 42.3})
        >>> mqtt_out.disconnect()

    Example with TLS:
        >>> mqtt_out = MQTTOutput(
        ...     "broker.example.com:8883",
        ...     topic="plant/readings",
        ...     use_tls=True,
        ...     tls_ca_certs="/path/to/ca.crt"
        ... )
    """

    # Regex for parsing host:port, supporting IPv6 in brackets
    _HOST_PORT_PATTERN = re.compile(
        r"^(?:\[(?P<ipv6>[^\]]+)\]|(?P<host>[^:\[\]]+))(?::(?P<port>\d+))?$"
    )

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
        use_tls: bool = False,
        tls_ca_certs: Optional[str] = None,
        tls_certfile: Optional[str] = None,
        tls_keyfile: Optional[str] = None,
        tls_insecure: bool = False,
    ):
        """
        Initialize MQTT output.

        Args:
            broker: Broker address. Can include port (e.g., "localhost:1883").
                    IPv6 addresses should use brackets: "[::1]:1883".
            topic: Default topic for publishing.
            port: MQTT port. Overrides port in broker string.
            client_id: MQTT client ID. Auto-generated if not provided.
            username: Optional username for authentication.
            password: Optional password for authentication.
            qos: Quality of Service level (0, 1, or 2).
            retain: Whether to retain messages on the broker.
            use_tls: Enable TLS/SSL encryption.
            tls_ca_certs: Path to CA certificate file for TLS.
            tls_certfile: Path to client certificate for mutual TLS.
            tls_keyfile: Path to client key for mutual TLS.
            tls_insecure: Skip server certificate verification (not recommended).
        """
        # Parse broker address (supports IPv6)
        self.host, parsed_port = self._parse_broker_address(broker)
        default_port = 8883 if use_tls else 1883
        self.port = port if port is not None else (parsed_port or default_port)

        self.topic = topic
        self.qos = self._validate_qos(qos)
        self.retain = retain

        # TLS configuration
        self.use_tls = use_tls
        self.tls_ca_certs = tls_ca_certs
        self.tls_certfile = tls_certfile
        self.tls_keyfile = tls_keyfile
        self.tls_insecure = tls_insecure

        # Create client with unique ID
        self.client_id = client_id or f"vision-connector-{int(time.time() * 1000) % 1000000}"

        # Use callback API version for paho-mqtt 2.x compatibility
        try:
            # paho-mqtt 2.x
            self.client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
                client_id=self.client_id,
            )
        except (AttributeError, TypeError):
            # paho-mqtt 1.x fallback
            self.client = mqtt.Client(client_id=self.client_id)

        # Set credentials if provided
        if username:
            self.client.username_pw_set(username, password)

        # Configure TLS
        if use_tls:
            self._configure_tls()

        # Connection state
        self._connected = False
        self._on_connect_callback: Optional[Callable] = None
        self._on_disconnect_callback: Optional[Callable] = None

        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _parse_broker_address(self, broker: str) -> tuple:
        """
        Parse broker address supporting IPv4, IPv6, and hostnames.

        Args:
            broker: Broker address string.

        Returns:
            Tuple of (host, port) where port may be None.
        """
        match = self._HOST_PORT_PATTERN.match(broker)
        if not match:
            # Fallback: treat entire string as host
            return broker, None

        host = match.group("ipv6") or match.group("host")
        port_str = match.group("port")
        port = int(port_str) if port_str else None

        return host, port

    def _validate_qos(self, qos: int) -> int:
        """Validate QoS level."""
        if qos not in (0, 1, 2):
            raise ValueError(f"Invalid QoS level: {qos}. Must be 0, 1, or 2.")
        return qos

    def _configure_tls(self) -> None:
        """Configure TLS settings."""
        context = ssl.create_default_context()

        if self.tls_ca_certs:
            context.load_verify_locations(self.tls_ca_certs)

        if self.tls_certfile and self.tls_keyfile:
            context.load_cert_chain(self.tls_certfile, self.tls_keyfile)

        if self.tls_insecure:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        self.client.tls_set_context(context)

    def _on_connect(self, client, userdata, flags, rc, *args):
        """Handle connection events."""
        if rc == 0:
            self._connected = True
            if self._on_connect_callback:
                self._on_connect_callback()
        else:
            self._connected = False

    def _on_disconnect(self, client, userdata, rc, *args):
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
            payload["timestamp"] = datetime.now(timezone.utc).isoformat()

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
