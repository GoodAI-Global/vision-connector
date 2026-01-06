"""
Structured logging infrastructure for vision-connector.

Provides enterprise-grade logging with:
- Configurable log levels and formats
- JSON structured output for log aggregation
- Context injection for tracing
- Performance timing utilities
- Audit logging for compliance
"""

import functools
import json
import logging
import sys
import threading
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Union

# Context variable for request/operation tracking
_request_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "request_context", default=None
)


class StructuredFormatter(logging.Formatter):
    """
    JSON structured log formatter for log aggregation systems.

    Outputs logs in JSON format compatible with ELK, Splunk, CloudWatch, etc.
    """

    def __init__(
        self,
        include_timestamp: bool = True,
        include_level: bool = True,
        include_logger: bool = True,
        include_context: bool = True,
        extra_fields: Optional[Dict[str, Any]] = None,
    ):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.include_logger = include_logger
        self.include_context = include_context
        self.extra_fields = extra_fields or {}

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {}

        if self.include_timestamp:
            log_data["timestamp"] = datetime.now(timezone.utc).isoformat()

        if self.include_level:
            log_data["level"] = record.levelname

        if self.include_logger:
            log_data["logger"] = record.name

        log_data["message"] = record.getMessage()

        # Add context from context var
        if self.include_context:
            ctx = _request_context.get()
            if ctx:
                log_data["context"] = ctx

        # Add extra fields from record
        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data

        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add static extra fields
        log_data.update(self.extra_fields)

        # Add source location for debug
        if record.levelno <= logging.DEBUG:
            log_data["source"] = {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
            }

        return json.dumps(log_data, default=str)


class StandardFormatter(logging.Formatter):
    """
    Human-readable log formatter for development/console output.
    """

    FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True):
        super().__init__(fmt=self.FORMAT, datefmt=self.DATE_FORMAT)
        self.use_colors = use_colors and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with optional colors."""
        # Create a copy to avoid modifying the original record
        # (which can cause issues with multiple handlers)
        if self.use_colors and record.levelname in self.COLORS:
            # Store original levelname
            original_levelname = record.levelname
            record.levelname = (
                f"{self.COLORS[original_levelname]}{original_levelname}{self.RESET}"
            )
            result = super().format(record)
            # Restore original levelname
            record.levelname = original_levelname
            return result
        return super().format(record)


class VisionLogger:
    """
    Enterprise logging wrapper for vision-connector.

    Provides structured logging with context injection and performance tracking.

    Example:
        >>> logger = VisionLogger("vision_connector.hmi")
        >>> logger.info("Reading HMI screen", image_path="screen.png", regions=3)
        >>>
        >>> with logger.operation("ocr_extraction"):
        ...     result = ocr.extract_text(image)
        >>> # Automatically logs duration
    """

    _configured = False
    _default_level = logging.INFO
    _config_lock = threading.Lock()

    def __init__(self, name: str):
        """
        Initialize logger with name.

        Args:
            name: Logger name (typically module path).
        """
        self.logger = logging.getLogger(name)
        self.name = name

    @classmethod
    def configure(
        cls,
        level: Union[int, str] = logging.INFO,
        json_format: bool = False,
        log_file: Optional[str] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Configure global logging settings.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            json_format: Use JSON structured output.
            log_file: Optional file path for log output.
            extra_fields: Extra fields to include in every log entry.
        """
        with cls._config_lock:
            if isinstance(level, str):
                level = getattr(logging, level.upper(), logging.INFO)

            cls._default_level = level

            # Get root vision_connector logger
            root_logger = logging.getLogger("vision_connector")
            root_logger.setLevel(level)

            # Remove existing handlers
            root_logger.handlers.clear()

            # Create formatter
            if json_format:
                formatter = StructuredFormatter(extra_fields=extra_fields)
            else:
                formatter = StandardFormatter()

            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

            # File handler
            if log_file:
                file_formatter = StructuredFormatter(extra_fields=extra_fields)
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(level)
                file_handler.setFormatter(file_formatter)
                root_logger.addHandler(file_handler)

            cls._configured = True

    def _log(
        self,
        level: int,
        message: str,
        exc_info: bool = False,
        **kwargs: Any,
    ) -> None:
        """Internal logging method with extra data support."""
        if not self._configured:
            # Auto-configure with defaults on first use
            self.configure()

        # Create log record with extra data
        extra = {"extra_data": kwargs} if kwargs else {}
        self.logger.log(level, message, exc_info=exc_info, extra=extra)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs: Any) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, exc_info=exc_info, **kwargs)

    def critical(self, message: str, exc_info: bool = False, **kwargs: Any) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, message, exc_info=exc_info, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self._log(logging.ERROR, message, exc_info=True, **kwargs)

    def operation(self, operation_name: str) -> "OperationContext":
        """
        Create operation context for timing and tracing.

        Args:
            operation_name: Name of the operation being performed.

        Returns:
            Context manager that logs operation timing.

        Example:
            >>> with logger.operation("ocr_extraction"):
            ...     result = ocr.extract_text(image)
        """
        return OperationContext(self, operation_name)

    def audit(
        self,
        action: str,
        resource: str,
        outcome: str = "success",
        **details: Any,
    ) -> None:
        """
        Log audit event for compliance.

        Args:
            action: Action performed (read, write, delete, etc.).
            resource: Resource affected.
            outcome: Outcome (success, failure, denied).
            **details: Additional audit details.
        """
        self._log(
            logging.INFO,
            f"AUDIT: {action} on {resource}",
            audit=True,
            action=action,
            resource=resource,
            outcome=outcome,
            **details,
        )


class OperationContext:
    """Context manager for operation timing and tracing."""

    def __init__(self, logger: VisionLogger, operation_name: str):
        self.logger = logger
        self.operation_name = operation_name
        self.operation_id = str(uuid.uuid4())[:8]
        self.start_time: float = 0

    def __enter__(self) -> "OperationContext":
        self.start_time = time.perf_counter()

        # Set context for nested logging
        existing = _request_context.get()
        ctx = existing.copy() if existing else {}
        ctx["operation_id"] = self.operation_id
        ctx["operation"] = self.operation_name
        _request_context.set(ctx)

        self.logger.debug(
            f"Starting operation: {self.operation_name}",
            operation_id=self.operation_id,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        duration_ms = (time.perf_counter() - self.start_time) * 1000

        if exc_type is not None:
            self.logger.error(
                f"Operation failed: {self.operation_name}",
                operation_id=self.operation_id,
                duration_ms=round(duration_ms, 2),
                error=str(exc_val),
            )
        else:
            self.logger.debug(
                f"Completed operation: {self.operation_name}",
                operation_id=self.operation_id,
                duration_ms=round(duration_ms, 2),
            )

        # Clear operation from context
        existing = _request_context.get()
        ctx = existing.copy() if existing else {}
        ctx.pop("operation_id", None)
        ctx.pop("operation", None)
        _request_context.set(ctx)


def set_context(**kwargs: Any) -> None:
    """
    Set context variables for all subsequent log messages.

    Args:
        **kwargs: Context key-value pairs.

    Example:
        >>> set_context(request_id="abc123", user="operator1")
        >>> logger.info("Processing request")  # Includes context
    """
    existing = _request_context.get()
    ctx = existing.copy() if existing else {}
    ctx.update(kwargs)
    _request_context.set(ctx)


def clear_context() -> None:
    """Clear all context variables."""
    _request_context.set({})


def get_logger(name: str) -> VisionLogger:
    """
    Get a VisionLogger instance.

    Args:
        name: Logger name (typically __name__).

    Returns:
        VisionLogger instance.
    """
    return VisionLogger(name)


def log_performance(func: Callable) -> Callable:
    """
    Decorator to log function performance.

    Args:
        func: Function to wrap.

    Returns:
        Wrapped function with performance logging.

    Example:
        >>> @log_performance
        ... def extract_text(image):
        ...     return ocr.process(image)
    """
    logger = get_logger(func.__module__)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with logger.operation(func.__name__):
            return func(*args, **kwargs)

    return wrapper
