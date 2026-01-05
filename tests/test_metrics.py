"""
Tests for the Prometheus metrics infrastructure.
"""

import pytest
import time

from vision_connector.metrics import (
    VisionMetrics,
    MetricsStub,
    track_operation,
    track_duration,
    metrics,
)


class TestMetricsStub:
    """Tests for MetricsStub class (used when prometheus_client not installed)."""

    def test_stub_labels(self):
        """Test stub labels method returns self."""
        stub = MetricsStub()
        result = stub.labels(key="value")
        assert result is stub

    def test_stub_inc(self):
        """Test stub inc method does nothing."""
        stub = MetricsStub()
        stub.inc()  # Should not raise
        stub.inc(5)  # Should not raise

    def test_stub_dec(self):
        """Test stub dec method does nothing."""
        stub = MetricsStub()
        stub.dec()  # Should not raise

    def test_stub_set(self):
        """Test stub set method does nothing."""
        stub = MetricsStub()
        stub.set(42)  # Should not raise

    def test_stub_observe(self):
        """Test stub observe method does nothing."""
        stub = MetricsStub()
        stub.observe(0.5)  # Should not raise

    def test_stub_time_context_manager(self):
        """Test stub time method returns context manager."""
        stub = MetricsStub()
        with stub.time():
            pass  # Should not raise


class TestVisionMetrics:
    """Tests for VisionMetrics class."""

    def test_metrics_instance_exists(self):
        """Test global metrics instance exists."""
        assert metrics is not None
        assert isinstance(metrics, VisionMetrics)

    def test_metrics_has_expected_attributes(self):
        """Test metrics has expected counter/histogram attributes."""
        assert hasattr(metrics, 'ocr_operations')
        assert hasattr(metrics, 'gauge_readings')
        assert hasattr(metrics, 'hmi_readings')
        assert hasattr(metrics, 'errors')
        assert hasattr(metrics, 'processing_duration')
        assert hasattr(metrics, 'ocr_duration')
        assert hasattr(metrics, 'ocr_confidence')
        assert hasattr(metrics, 'mqtt_messages')
        assert hasattr(metrics, 'webhook_requests')
        assert hasattr(metrics, 'csv_rows')
        assert hasattr(metrics, 'active_connections')
        assert hasattr(metrics, 'info')

    def test_get_metrics_returns_bytes(self):
        """Test get_metrics returns bytes."""
        result = metrics.get_metrics()
        assert isinstance(result, bytes)

    def test_content_type_is_string(self):
        """Test content_type is a string."""
        assert isinstance(metrics.content_type, str)


class TestTrackDuration:
    """Tests for track_duration context manager."""

    def test_track_duration_context_manager(self):
        """Test tracking duration of operations."""
        with track_duration("test_operation"):
            time.sleep(0.01)  # Small delay
        # Should complete without error

    def test_track_duration_on_exception(self):
        """Test tracking duration when exception occurs."""
        with pytest.raises(ValueError):
            with track_duration("failing_operation"):
                raise ValueError("Test error")


class TestTrackOperationDecorator:
    """Tests for track_operation decorator."""

    def test_decorator_preserves_function(self):
        """Test decorator preserves function metadata."""

        @track_operation("test_op")
        def my_function():
            """Test docstring."""
            return 42

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ is not None
        assert "Test docstring" in my_function.__doc__

    def test_decorator_returns_value(self):
        """Test decorated function returns correctly."""

        @track_operation("add_op")
        def add(a, b):
            return a + b

        result = add(2, 3)
        assert result == 5

    def test_decorator_handles_exception(self):
        """Test decorator handles exceptions properly."""

        @track_operation("failing_op")
        def failing():
            raise RuntimeError("Test error")

        with pytest.raises(RuntimeError):
            failing()

    def test_decorator_with_args_and_kwargs(self):
        """Test decorator with various arguments."""

        @track_operation("complex_op")
        def complex_fn(a, b, *args, **kwargs):
            return (a, b, args, kwargs)

        result = complex_fn(1, 2, 3, 4, key="value")
        assert result == (1, 2, (3, 4), {"key": "value"})


class TestMetricsIntegration:
    """Integration tests for metrics with stubs (prometheus_client may not be installed)."""

    def test_metrics_operations_dont_raise(self):
        """Test that all metrics operations work (with or without prometheus)."""
        # These should all work without raising, even if prometheus_client is not installed
        metrics.ocr_operations.labels(processor="test", status="success").inc()
        metrics.gauge_readings.labels(status="success").inc()
        metrics.hmi_readings.labels(status="success").inc()
        metrics.errors.labels(error_type="TestError", module="test").inc()
        metrics.processing_duration.labels(operation="test").observe(0.5)
        metrics.ocr_duration.labels(region_count="1").observe(0.3)
        metrics.ocr_confidence.labels(field="temperature").observe(0.95)
        metrics.mqtt_messages.labels(topic="test", status="success").inc()
        metrics.webhook_requests.labels(method="POST", status_code="200").inc()
        metrics.csv_rows.labels(file="test.csv").inc()
        metrics.active_connections.labels(type="mqtt").inc()

    def test_configure_doesnt_raise(self):
        """Test configure method doesn't raise even without prometheus."""
        # Should not raise even if prometheus_client is not installed
        metrics.configure(port=9999, start_server=False, version="0.1.0")
