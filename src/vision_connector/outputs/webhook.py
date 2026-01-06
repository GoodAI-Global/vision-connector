"""
Webhook output module for sending data to HTTP endpoints.

Provides reliable HTTP POST with retry logic and batching.
Works headless - no display required.
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from vision_connector.exceptions import ValidationError
from vision_connector.logging import get_logger

# Module logger
_logger = get_logger(__name__)


class WebhookOutput:
    """
    Webhook output for sending extracted data to HTTP endpoints.

    Supports authentication, custom headers, retries, SSL verification, and batching.

    Example:
        >>> webhook = WebhookOutput("https://api.example.com/readings")
        >>> webhook.send({"temperature": 185.5, "pressure": 42.3})
    """

    ALLOWED_SCHEMES = {"http", "https"}

    def __init__(
        self,
        url: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None,
        api_key: Optional[str] = None,
        api_key_header: str = "X-API-Key",
        timeout: float = 30.0,
        retries: int = 3,
        retry_delay: float = 1.0,
        verify_ssl: bool = True,
    ):
        """
        Initialize webhook output.

        Args:
            url: Target webhook URL (must be http or https).
            method: HTTP method (POST, PUT, PATCH).
            headers: Optional custom headers.
            auth: Optional (username, password) tuple for basic auth.
            api_key: Optional API key for authentication.
            api_key_header: Header name for API key.
            timeout: Request timeout in seconds.
            retries: Number of retry attempts on failure.
            retry_delay: Delay between retries in seconds.
            verify_ssl: Verify SSL certificates (default True, set False for testing only).
        """
        _logger.debug(
            "Initializing WebhookOutput",
            url=url,
            method=method,
            retries=retries,
        )
        self.url = self._validate_url(url)
        self.method = self._validate_method(method)
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self.verify_ssl = verify_ssl

        # Build headers
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "vision-connector/0.1.0",
        }
        if headers:
            self.headers.update(headers)
        if api_key:
            self.headers[api_key_header] = api_key

        # Authentication
        self.auth = auth

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = verify_ssl
        if auth:
            self.session.auth = auth

        _logger.info(
            "WebhookOutput initialized",
            url=self.url,
            method=self.method,
        )

    def _validate_url(self, url: str) -> str:
        """Validate URL format and scheme."""
        parsed = urlparse(url)

        if not parsed.scheme:
            raise ValidationError(
                f"Invalid URL: missing scheme (http/https): {url}",
                details={"url": url, "issue": "missing_scheme"},
            )

        if parsed.scheme.lower() not in self.ALLOWED_SCHEMES:
            raise ValidationError(
                f"Invalid URL scheme: {parsed.scheme}. "
                f"Allowed: {', '.join(self.ALLOWED_SCHEMES)}",
                details={
                    "url": url,
                    "scheme": parsed.scheme,
                    "allowed": list(self.ALLOWED_SCHEMES),
                },
            )

        if not parsed.netloc:
            raise ValidationError(
                f"Invalid URL: missing host: {url}",
                details={"url": url, "issue": "missing_host"},
            )

        return url

    def _validate_method(self, method: str) -> str:
        """Validate HTTP method."""
        method = method.upper()
        if method not in ("POST", "PUT", "PATCH"):
            raise ValidationError(
                f"Unsupported HTTP method: {method}. Use POST, PUT, or PATCH.",
                details={"method": method, "allowed": ["POST", "PUT", "PATCH"]},
            )
        return method

    def send(
        self,
        data: Dict[str, Any],
        add_timestamp: bool = True,
    ) -> Dict:
        """
        Send data to the webhook endpoint.

        Args:
            data: Dictionary of data to send.
            add_timestamp: Whether to add a timestamp field.

        Returns:
            Response information dict with status_code, success, and response.

        Raises:
            requests.RequestException: If all retries fail.
        """
        # Prepare payload
        payload = dict(data)
        if add_timestamp:
            payload["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Attempt with retries
        last_error = None

        for attempt in range(self.retries + 1):
            try:
                if self.method == "POST":
                    response = self.session.post(
                        self.url,
                        json=payload,
                        timeout=self.timeout,
                    )
                elif self.method == "PUT":
                    response = self.session.put(
                        self.url,
                        json=payload,
                        timeout=self.timeout,
                    )
                elif self.method == "PATCH":
                    response = self.session.patch(
                        self.url,
                        json=payload,
                        timeout=self.timeout,
                    )

                # Return result
                result = {
                    "success": response.ok,
                    "status_code": response.status_code,
                    "response": self._parse_response(response),
                }
                _logger.debug(
                    "Webhook request completed",
                    status_code=response.status_code,
                    success=response.ok,
                )
                return result

            except requests.RequestException as e:
                last_error = e
                _logger.warning(
                    "Webhook request failed, retrying",
                    attempt=attempt + 1,
                    max_retries=self.retries,
                    error=str(e),
                )
                if attempt < self.retries:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                continue

        # All retries failed
        _logger.error(
            "Webhook request failed after all retries",
            attempts=self.retries + 1,
            error=str(last_error),
        )
        raise requests.RequestException(
            f"Webhook request failed after {self.retries + 1} attempts: {last_error}"
        )

    def send_batch(
        self,
        readings: List[Dict[str, Any]],
        batch_key: str = "readings",
    ) -> Dict:
        """
        Send multiple readings in a single request.

        Args:
            readings: List of data dictionaries.
            batch_key: Key name for the readings array in payload.

        Returns:
            Response information dict.
        """
        payload = {
            batch_key: readings,
            "count": len(readings),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return self.send(payload, add_timestamp=False)

    def _parse_response(self, response: requests.Response) -> Any:
        """Parse response body."""
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text

    def test_connection(self) -> bool:
        """
        Test connectivity to the webhook endpoint.

        Returns:
            True if endpoint is reachable.
        """
        try:
            # Send minimal test payload
            result = self.send({"test": True, "_vision_connector_test": True})
            return result["success"]
        except Exception:
            return False

    def close(self) -> None:
        """Close the session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
