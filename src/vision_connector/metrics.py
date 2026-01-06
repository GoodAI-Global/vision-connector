"""
Prometheus metrics infrastructure for vision-connector.

Provides enterprise-grade observability with:
- Operation counters and histograms
- Error tracking
- Latency monitoring
- Custom business metrics
- Optional metrics server
"""

import functools
import time
from typing import Callable

from vision_connector.logging import get_logger

_logger = get_logger(__name__)

# Track if prometheus_client is available
_prometheus_available = False

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        Info,
        generate_latest,
        start_http_server,
    )

    _prometheus_available = True
except ImportError:
    # Prometheus client not installed - provide stub implementations
    pass


class MetricsStub:
    """Stub class when prometheus_client is not available."""

    def labels(self, **kwargs):
        return self

    def inc(self, amount=1):
        pass

    def dec(self, amount=1):
        pass

    def set(self, value):
        pass

    def observe(self, value):
        pass

    def info(self, value):
        pass

    def time(self):
        """Context manager that does nothing."""
        return NullContextManager()


class NullContextManager:
    """Null context manager for stubs."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class VisionMetrics:
    """
    Prometheus metrics for vision-connector operations.

    Provides counters, histograms, and gauges for monitoring
    OCR operations, gauge readings, and system health.

    Example:
        >>> from vision_connector.metrics import metrics
        >>> metrics.configure()  # Optional: start metrics server
        >>>
        >>> # Metrics are automatically collected by processors
        >>> # Or manually:
        >>> metrics.ocr_operations.labels(status="success").inc()
        >>> metrics.processing_duration.labels(operation="ocr").observe(0.5)
    """

    def __init__(self, prefix: str = "vision_connector"):
        """
        Initialize metrics with optional prefix.

        Args:
            prefix: Prefix for all metric names.
        """
        self._prefix = prefix
        self._enabled = False
        self._server_started = False

        if _prometheus_available:
            self._registry = CollectorRegistry()
            self._init_metrics()
        else:
            self._registry = None
            self._init_stubs()

    def _init_metrics(self):
        """Initialize Prometheus metrics."""
        # Operation counters
        self.ocr_operations = Counter(
            f"{self._prefix}_ocr_operations_total",
            "Total OCR operations",
            ["processor", "status"],
            registry=self._registry,
        )

        self.gauge_readings = Counter(
            f"{self._prefix}_gauge_readings_total",
            "Total gauge reading operations",
            ["status"],
            registry=self._registry,
        )

        self.hmi_readings = Counter(
            f"{self._prefix}_hmi_readings_total",
            "Total HMI screen reading operations",
            ["status"],
            registry=self._registry,
        )

        # Error tracking
        self.errors = Counter(
            f"{self._prefix}_errors_total",
            "Total errors by type",
            ["error_type", "module"],
            registry=self._registry,
        )

        # Processing duration histograms
        self.processing_duration = Histogram(
            f"{self._prefix}_processing_duration_seconds",
            "Processing duration in seconds",
            ["operation"],
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self._registry,
        )

        self.ocr_duration = Histogram(
            f"{self._prefix}_ocr_duration_seconds",
            "OCR extraction duration in seconds",
            ["region_count"],
            buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            registry=self._registry,
        )

        # Confidence metrics
        self.ocr_confidence = Histogram(
            f"{self._prefix}_ocr_confidence",
            "OCR confidence scores",
            ["field"],
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0),
            registry=self._registry,
        )

        # Output metrics
        self.mqtt_messages = Counter(
            f"{self._prefix}_mqtt_messages_total",
            "Total MQTT messages sent",
            ["topic", "status"],
            registry=self._registry,
        )

        self.webhook_requests = Counter(
            f"{self._prefix}_webhook_requests_total",
            "Total webhook requests",
            ["method", "status_code"],
            registry=self._registry,
        )

        self.csv_rows = Counter(
            f"{self._prefix}_csv_rows_total",
            "Total CSV rows written",
            ["file"],
            registry=self._registry,
        )

        # Active connections gauge
        self.active_connections = Gauge(
            f"{self._prefix}_active_connections",
            "Current active connections",
            ["type"],
            registry=self._registry,
        )

        # System info
        self.info = Info(
            f"{self._prefix}_build",
            "Build information",
            registry=self._registry,
        )

        self._enabled = True
        _logger.debug("Prometheus metrics initialized")

    def _init_stubs(self):
        """Initialize stub metrics when prometheus_client is not available."""
        stub = MetricsStub()
        self.ocr_operations = stub
        self.gauge_readings = stub
        self.hmi_readings = stub
        self.errors = stub
        self.processing_duration = stub
        self.ocr_duration = stub
        self.ocr_confidence = stub
        self.mqtt_messages = stub
        self.webhook_requests = stub
        self.csv_rows = stub
        self.active_connections = stub
        self.info = stub

        _logger.debug(
            "Prometheus client not installed, using stub metrics. "
            "Install with: pip install prometheus-client"
        )

    def configure(
        self,
        port: int = 9090,
        start_server: bool = True,
        version: str = "0.1.0",
    ) -> None:
        """
        Configure and optionally start the metrics server.

        Args:
            port: Port for metrics HTTP server (1-65535).
            start_server: Whether to start the HTTP server.
            version: Version to report in build info.

        Raises:
            ValueError: If port is out of valid range.
        """
        if not _prometheus_available:
            _logger.warning(
                "Cannot configure metrics: prometheus_client not installed. "
                "Install with: pip install prometheus-client"
            )
            return

        # Validate port range
        if not (1 <= port <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {port}")

        # Set build info
        self.info.info(
            {
                "version": version,
                "component": "vision-connector",
            }
        )

        if start_server and not self._server_started:
            try:
                start_http_server(port, registry=self._registry)
                self._server_started = True
                _logger.info(
                    "Metrics server started",
                    port=port,
                    endpoint=f"http://localhost:{port}/metrics",
                )
            except Exception as e:
                _logger.error("Failed to start metrics server", error=str(e))

    def get_metrics(self) -> bytes:
        """
        Get metrics in Prometheus text format.

        Returns:
            Metrics as bytes in Prometheus exposition format.
        """
        if not _prometheus_available:
            return b"# Prometheus client not installed\n"

        return generate_latest(self._registry)

    @property
    def is_enabled(self) -> bool:
        """Check if metrics collection is enabled."""
        return self._enabled

    @property
    def content_type(self) -> str:
        """Get Prometheus content type for HTTP responses."""
        if _prometheus_available:
            return CONTENT_TYPE_LATEST
        return "text/plain"


# Global metrics instance
metrics = VisionMetrics()


def track_operation(operation_name: str):
    """
    Decorator to track operation metrics with processing duration and errors.

    Tracks:
    - Processing duration in seconds
    - Error counts by type

    Args:
        operation_name: Name of the operation for labels.

    Example:
        >>> @track_operation("extract_text")
        ... def extract_text(image):
        ...     return ocr.process(image)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                metrics.errors.labels(
                    error_type=type(e).__name__,
                    module=func.__module__,
                ).inc()
                raise
            finally:
                duration = time.perf_counter() - start_time
                metrics.processing_duration.labels(
                    operation=operation_name,
                ).observe(duration)

        return wrapper

    return decorator


def track_duration(operation_name: str):
    """
    Context manager to track operation duration.

    Args:
        operation_name: Name of the operation.

    Example:
        >>> with track_duration("image_processing"):
        ...     process_image(img)
    """
    return DurationTracker(operation_name)


class DurationTracker:
    """Context manager for tracking operation duration."""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time: float = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.perf_counter() - self.start_time
        metrics.processing_duration.labels(
            operation=self.operation_name,
        ).observe(duration)

        if exc_type is not None:
            metrics.errors.labels(
                error_type=exc_type.__name__,
                module="unknown",
            ).inc()
