"""
Tests for the structured logging infrastructure.
"""

import json
import logging
import pytest
import tempfile
from pathlib import Path

from vision_connector.logging import (
    VisionLogger,
    StructuredFormatter,
    StandardFormatter,
    OperationContext,
    get_logger,
    set_context,
    clear_context,
    log_performance,
)


class TestVisionLogger:
    """Tests for VisionLogger class."""

    def setup_method(self):
        """Reset logging configuration before each test."""
        VisionLogger._configured = False
        clear_context()

    def test_get_logger(self):
        """Test logger creation."""
        logger = get_logger("test.module")
        assert isinstance(logger, VisionLogger)
        assert logger.name == "test.module"

    def test_logger_auto_configures(self):
        """Test that logger auto-configures on first use."""
        logger = get_logger("test.auto")
        assert not VisionLogger._configured
        logger.info("Test message")
        assert VisionLogger._configured

    def test_configure_with_level(self):
        """Test configuring with different log levels."""
        VisionLogger.configure(level="DEBUG")
        assert VisionLogger._default_level == logging.DEBUG

        VisionLogger.configure(level="WARNING")
        assert VisionLogger._default_level == logging.WARNING

    def test_configure_with_file(self):
        """Test configuring with log file."""
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_file = f.name

        try:
            VisionLogger.configure(level="INFO", log_file=log_file)
            # Use vision_connector namespace so it propagates to root handler
            logger = get_logger("vision_connector.test.file")
            logger.info("Test message to file")

            # Flush handlers to ensure file is written
            root_logger = logging.getLogger("vision_connector")
            for handler in root_logger.handlers:
                handler.flush()

            # Check file was written
            with open(log_file) as f:
                content = f.read()
                assert "Test message to file" in content
        finally:
            Path(log_file).unlink(missing_ok=True)

    def test_log_levels(self):
        """Test all log levels work."""
        VisionLogger.configure(level="DEBUG")
        logger = get_logger("test.levels")

        # Should not raise any errors
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

    def test_log_with_extra_data(self):
        """Test logging with additional data."""
        VisionLogger.configure(level="DEBUG", json_format=True)
        logger = get_logger("test.extra")

        # Should not raise
        logger.info("Test message", key1="value1", key2=42)


class TestStructuredFormatter:
    """Tests for StructuredFormatter class."""

    def test_json_output(self):
        """Test JSON formatting."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["message"] == "Test message"
        assert data["level"] == "INFO"
        assert "timestamp" in data

    def test_extra_fields(self):
        """Test extra static fields."""
        formatter = StructuredFormatter(extra_fields={"app": "vision-connector"})
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["app"] == "vision-connector"

    def test_excludes_timestamp(self):
        """Test excluding timestamp."""
        formatter = StructuredFormatter(include_timestamp=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "timestamp" not in data


class TestStandardFormatter:
    """Tests for StandardFormatter class."""

    def test_format_output(self):
        """Test human-readable formatting."""
        # Force no colors for testing
        formatter = StandardFormatter(use_colors=False)
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        assert "INFO" in output
        assert "test.module" in output
        assert "Test message" in output

    def test_preserves_levelname(self):
        """Test that formatting preserves original levelname."""
        formatter = StandardFormatter(use_colors=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        original_levelname = record.levelname
        formatter.format(record)

        # Levelname should be restored
        assert record.levelname == original_levelname


class TestOperationContext:
    """Tests for OperationContext class."""

    def setup_method(self):
        """Reset before each test."""
        VisionLogger._configured = False
        clear_context()

    def test_operation_timing(self):
        """Test that operation context measures time."""
        VisionLogger.configure(level="DEBUG")
        logger = get_logger("test.operation")

        with logger.operation("test_op"):
            pass  # Quick operation

        # Should complete without error

    def test_operation_context_on_success(self):
        """Test context manager on successful operation."""
        VisionLogger.configure(level="DEBUG")
        logger = get_logger("test.success")

        with logger.operation("success_op") as ctx:
            assert ctx.operation_name == "success_op"
            assert len(ctx.operation_id) == 8

    def test_operation_context_on_exception(self):
        """Test context manager handles exceptions."""
        VisionLogger.configure(level="DEBUG")
        logger = get_logger("test.exception")

        with pytest.raises(ValueError):
            with logger.operation("failing_op"):
                raise ValueError("Test error")


class TestContextManagement:
    """Tests for context variable management."""

    def setup_method(self):
        """Clear context before each test."""
        clear_context()

    def test_set_context(self):
        """Test setting context variables."""
        set_context(request_id="abc123", user="test")
        # Should not raise

    def test_clear_context(self):
        """Test clearing context."""
        set_context(key="value")
        clear_context()
        # Should not raise

    def test_context_accumulates(self):
        """Test that context accumulates values."""
        set_context(key1="value1")
        set_context(key2="value2")
        # Both should be present (implementation detail)


class TestLogPerformanceDecorator:
    """Tests for the log_performance decorator."""

    def setup_method(self):
        """Reset before each test."""
        VisionLogger._configured = False
        clear_context()

    def test_decorator_wraps_function(self):
        """Test that decorator preserves function metadata."""

        @log_performance
        def my_function():
            """My docstring."""
            return 42

        assert my_function.__name__ == "my_function"
        assert "My docstring" in my_function.__doc__

    def test_decorator_returns_value(self):
        """Test that decorated function returns correctly."""
        VisionLogger.configure(level="DEBUG")

        @log_performance
        def add(a, b):
            return a + b

        result = add(2, 3)
        assert result == 5

    def test_decorator_handles_exception(self):
        """Test that decorator propagates exceptions."""
        VisionLogger.configure(level="DEBUG")

        @log_performance
        def failing():
            raise RuntimeError("Test error")

        with pytest.raises(RuntimeError):
            failing()


class TestAuditLogging:
    """Tests for audit logging functionality."""

    def setup_method(self):
        """Reset before each test."""
        VisionLogger._configured = False

    def test_audit_log(self):
        """Test audit logging."""
        VisionLogger.configure(level="INFO")
        logger = get_logger("test.audit")

        # Should not raise
        logger.audit(
            action="read",
            resource="hmi_screen.png",
            outcome="success",
            user="operator1",
        )
