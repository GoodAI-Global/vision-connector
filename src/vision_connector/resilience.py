"""
Resilience patterns for vision-connector.

Provides enterprise-grade reliability with:
- Retry with exponential backoff
- Circuit breaker pattern
- Timeout handling
- Fallback support
"""

import functools
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional, Tuple, Type

from vision_connector.exceptions import RetryExhaustedError
from vision_connector.logging import get_logger

_logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    """Maximum number of retry attempts."""

    base_delay: float = 1.0
    """Base delay between retries in seconds."""

    max_delay: float = 60.0
    """Maximum delay between retries in seconds."""

    exponential_base: float = 2.0
    """Base for exponential backoff calculation."""

    jitter: bool = True
    """Add random jitter to delays."""

    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    """Exception types that should trigger a retry."""

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number.

        Args:
            attempt: Current attempt number (0-indexed).

        Returns:
            Delay in seconds.
        """
        delay = min(
            self.base_delay * (self.exponential_base**attempt),
            self.max_delay,
        )

        if self.jitter:
            import random

            delay = delay * (0.5 + random.random())

        return delay


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5
    """Number of failures before opening circuit."""

    success_threshold: int = 2
    """Number of successes in half-open before closing."""

    timeout: float = 30.0
    """Time in seconds before attempting recovery."""

    half_open_max_calls: int = 1
    """Maximum concurrent calls in half-open state."""


@dataclass
class CircuitBreakerState:
    """State tracking for circuit breaker."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    half_open_calls: int = 0

    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_success(self, config: CircuitBreakerConfig) -> None:
        """Record a successful call."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                self.half_open_calls -= 1
                if self.success_count >= config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    _logger.info("Circuit breaker closed after recovery")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def record_failure(self, config: CircuitBreakerConfig) -> None:
        """Record a failed call."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls -= 1
                self.state = CircuitState.OPEN
                _logger.warning("Circuit breaker opened after half-open failure")
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= config.failure_threshold:
                    self.state = CircuitState.OPEN
                    _logger.warning(
                        "Circuit breaker opened",
                        failures=self.failure_count,
                    )

    def can_execute(self, config: CircuitBreakerConfig) -> bool:
        """Check if a call can be executed."""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                # Check if timeout has passed
                if self.last_failure_time:
                    elapsed = datetime.now() - self.last_failure_time
                    if elapsed > timedelta(seconds=config.timeout):
                        self.state = CircuitState.HALF_OPEN
                        self.success_count = 0
                        self.half_open_calls = 0
                        _logger.info("Circuit breaker entering half-open state")
                        return True
                return False

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls < config.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                return False

            return False


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open and rejecting calls."""

    pass


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
):
    """
    Decorator to add retry logic with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts.
        base_delay: Base delay between retries in seconds.
        max_delay: Maximum delay between retries in seconds.
        exponential_base: Base for exponential backoff.
        jitter: Add random jitter to delays.
        retryable_exceptions: Exception types that trigger retry.
        on_retry: Optional callback called before each retry.

    Example:
        >>> @retry(max_attempts=3, base_delay=1.0)
        ... def fetch_data():
        ...     return api.get("/data")
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
    )

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e

                    if attempt == config.max_attempts - 1:
                        # Last attempt, don't retry
                        break

                    delay = config.get_delay(attempt)

                    _logger.warning(
                        f"Retry attempt {attempt + 1}/{config.max_attempts}",
                        error=str(e),
                        delay=delay,
                    )

                    if on_retry:
                        on_retry(attempt + 1, e)

                    time.sleep(delay)

            raise RetryExhaustedError(
                operation=func.__name__,
                attempts=config.max_attempts,
                last_error=last_exception,
            )

        return wrapper

    return decorator


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    Prevents repeated calls to a failing service, allowing it time to recover.

    Example:
        >>> breaker = CircuitBreaker(failure_threshold=3)
        >>>
        >>> @breaker
        ... def call_service():
        ...     return api.get("/data")
        >>>
        >>> # After 3 failures, circuit opens
        >>> # Calls are rejected for timeout period
        >>> # After timeout, circuit enters half-open
        >>> # If next call succeeds, circuit closes
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 30.0,
        half_open_max_calls: int = 1,
        name: Optional[str] = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening.
            success_threshold: Successes in half-open before closing.
            timeout: Seconds before recovery attempt.
            half_open_max_calls: Max concurrent calls in half-open.
            name: Optional name for logging.
        """
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            timeout=timeout,
            half_open_max_calls=half_open_max_calls,
        )
        self._state = CircuitBreakerState()
        self.name = name

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state.state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._state.failure_count

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap function with circuit breaker."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self.execute(func, *args, **kwargs)

        return wrapper

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Function result.

        Raises:
            CircuitBreakerOpen: If circuit is open.
        """
        if not self._state.can_execute(self.config):
            _logger.debug(f"Circuit breaker {self.name or 'unnamed'} is open")
            raise CircuitBreakerOpen(
                f"Circuit breaker is open for {self.name or func.__name__}"
            )

        try:
            result = func(*args, **kwargs)
            self._state.record_success(self.config)
            return result
        except Exception:
            self._state.record_failure(self.config)
            raise

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        with self._state._lock:
            self._state.state = CircuitState.CLOSED
            self._state.failure_count = 0
            self._state.success_count = 0
            self._state.half_open_calls = 0
            _logger.info(f"Circuit breaker {self.name or 'unnamed'} reset")


def with_timeout(
    seconds: float,
    fallback: Optional[Callable[[], Any]] = None,
):
    """
    Decorator to add timeout to function execution.

    Note: Uses threading, so may not interrupt blocking I/O.

    Args:
        seconds: Timeout in seconds.
        fallback: Optional fallback function if timeout occurs.

    Example:
        >>> @with_timeout(5.0)
        ... def slow_operation():
        ...     return heavy_computation()
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            exception = [None]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout=seconds)

            if thread.is_alive():
                _logger.warning(f"Operation {func.__name__} timed out after {seconds}s")
                if fallback:
                    return fallback()
                raise TimeoutError(
                    f"Operation {func.__name__} timed out after {seconds} seconds"
                )

            if exception[0]:
                raise exception[0]

            return result[0]

        return wrapper

    return decorator


def with_fallback(fallback_func: Callable[[], Any]):
    """
    Decorator to provide fallback on exception.

    Args:
        fallback_func: Function to call if main function fails.

    Example:
        >>> @with_fallback(lambda: {"status": "unknown"})
        ... def get_status():
        ...     return api.get("/status")
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                _logger.warning(
                    f"Using fallback for {func.__name__}",
                    error=str(e),
                )
                return fallback_func()

        return wrapper

    return decorator
