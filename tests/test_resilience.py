"""
Tests for the resilience patterns module.
"""

import time

import pytest

from vision_connector.exceptions import RetryExhaustedError
from vision_connector.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    CircuitState,
    RetryConfig,
    retry,
    with_fallback,
    with_timeout,
)


class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0

    def test_get_delay_exponential(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)

        assert config.get_delay(0) == 1.0  # 1 * 2^0 = 1
        assert config.get_delay(1) == 2.0  # 1 * 2^1 = 2
        assert config.get_delay(2) == 4.0  # 1 * 2^2 = 4

    def test_get_delay_max_cap(self):
        """Test delay is capped at max_delay."""
        config = RetryConfig(base_delay=1.0, max_delay=5.0, jitter=False)

        assert config.get_delay(10) == 5.0  # Would be 1024, capped at 5

    def test_get_delay_with_jitter(self):
        """Test delay includes jitter."""
        config = RetryConfig(base_delay=1.0, jitter=True)

        # Get multiple delays - they should vary
        delays = [config.get_delay(0) for _ in range(10)]

        # With jitter, not all delays should be the same
        unique_delays = set(delays)
        assert len(unique_delays) > 1


class TestRetryDecorator:
    """Tests for retry decorator."""

    def test_success_on_first_try(self):
        """Test successful execution doesn't retry."""
        call_count = [0]

        @retry(max_attempts=3, base_delay=0.01)
        def successful():
            call_count[0] += 1
            return "success"

        result = successful()
        assert result == "success"
        assert call_count[0] == 1

    def test_retry_on_failure(self):
        """Test retry on exception."""
        call_count = [0]

        @retry(max_attempts=3, base_delay=0.01)
        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Not yet")
            return "success"

        result = flaky()
        assert result == "success"
        assert call_count[0] == 3

    def test_exhausted_retries(self):
        """Test all retries exhausted raises RetryExhaustedError."""

        @retry(max_attempts=3, base_delay=0.01)
        def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(RetryExhaustedError) as exc_info:
            always_fails()

        assert exc_info.value.details["attempts"] == 3

    def test_specific_exception_types(self):
        """Test only retrying on specific exceptions."""
        call_count = [0]

        @retry(max_attempts=3, base_delay=0.01, retryable_exceptions=(ValueError,))
        def fails_with_type_error():
            call_count[0] += 1
            if call_count[0] == 1:
                raise TypeError("Won't retry on this")

        # TypeError should not be retried
        with pytest.raises(TypeError):
            fails_with_type_error()

        assert call_count[0] == 1

    def test_on_retry_callback(self):
        """Test on_retry callback is called."""
        retries = []

        def on_retry(attempt, error):
            retries.append((attempt, str(error)))

        @retry(max_attempts=3, base_delay=0.01, on_retry=on_retry)
        def flaky():
            if len(retries) < 2:
                raise ValueError("Fail")
            return "success"

        result = flaky()
        assert result == "success"
        assert len(retries) == 2


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_initial_state_closed(self):
        """Test circuit breaker starts closed."""
        breaker = CircuitBreaker()
        assert breaker.state == CircuitState.CLOSED

    def test_opens_after_failures(self):
        """Test circuit opens after threshold failures."""
        breaker = CircuitBreaker(failure_threshold=2)

        @breaker
        def failing():
            raise ValueError("Fail")

        # First failure
        with pytest.raises(ValueError):
            failing()
        assert breaker.state == CircuitState.CLOSED

        # Second failure - should open
        with pytest.raises(ValueError):
            failing()
        assert breaker.state == CircuitState.OPEN

    def test_rejects_when_open(self):
        """Test calls are rejected when circuit is open."""
        breaker = CircuitBreaker(failure_threshold=1, timeout=60)

        @breaker
        def failing():
            raise ValueError("Fail")

        # Trigger open
        with pytest.raises(ValueError):
            failing()

        # Next call should be rejected
        with pytest.raises(CircuitBreakerOpen):
            failing()

    def test_half_open_after_timeout(self):
        """Test circuit enters half-open after timeout."""
        breaker = CircuitBreaker(failure_threshold=1, timeout=0.1)

        @breaker
        def failing():
            raise ValueError("Fail")

        # Trigger open
        with pytest.raises(ValueError):
            failing()
        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Next call should be allowed (half-open)
        with pytest.raises(ValueError):
            failing()
        # After failure in half-open, goes back to open
        assert breaker.state == CircuitState.OPEN

    def test_closes_after_success_in_half_open(self):
        """Test circuit closes after success in half-open."""
        call_count = [0]
        breaker = CircuitBreaker(
            failure_threshold=1,
            success_threshold=1,
            timeout=0.1,
        )

        @breaker
        def sometimes_fails():
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("First call fails")
            return "success"

        # Trigger open
        with pytest.raises(ValueError):
            sometimes_fails()
        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # This should succeed and close the circuit
        result = sometimes_fails()
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    def test_reset(self):
        """Test circuit breaker reset."""
        breaker = CircuitBreaker(failure_threshold=1)

        @breaker
        def failing():
            raise ValueError("Fail")

        # Trigger open
        with pytest.raises(ValueError):
            failing()
        assert breaker.state == CircuitState.OPEN

        # Reset
        breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0


class TestWithTimeout:
    """Tests for with_timeout decorator."""

    def test_fast_operation_succeeds(self):
        """Test fast operation completes normally."""

        @with_timeout(1.0)
        def fast_operation():
            return "success"

        result = fast_operation()
        assert result == "success"

    def test_slow_operation_times_out(self):
        """Test slow operation raises TimeoutError."""

        @with_timeout(0.1)
        def slow_operation():
            time.sleep(1.0)
            return "never returned"

        with pytest.raises(TimeoutError):
            slow_operation()

    def test_timeout_with_fallback(self):
        """Test timeout uses fallback."""

        @with_timeout(0.1, fallback=lambda: "fallback_value")
        def slow_operation():
            time.sleep(1.0)
            return "never returned"

        result = slow_operation()
        assert result == "fallback_value"

    def test_exception_propagates(self):
        """Test exception from operation is propagated."""

        @with_timeout(1.0)
        def failing_operation():
            raise ValueError("Operation failed")

        with pytest.raises(ValueError):
            failing_operation()


class TestWithFallback:
    """Tests for with_fallback decorator."""

    def test_success_doesnt_use_fallback(self):
        """Test successful operation doesn't use fallback."""

        @with_fallback(lambda: "fallback")
        def successful():
            return "success"

        result = successful()
        assert result == "success"

    def test_failure_uses_fallback(self):
        """Test failed operation uses fallback."""

        @with_fallback(lambda: "fallback")
        def failing():
            raise ValueError("Failed")

        result = failing()
        assert result == "fallback"

    def test_fallback_with_complex_return(self):
        """Test fallback with complex return value."""

        @with_fallback(lambda: {"status": "unknown", "data": None})
        def get_data():
            raise ConnectionError("No connection")

        result = get_data()
        assert result["status"] == "unknown"


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.success_threshold == 2
        assert config.timeout == 30.0


class TestIntegration:
    """Integration tests for combined resilience patterns."""

    def test_retry_with_circuit_breaker(self):
        """Test retry decorator with circuit breaker."""
        call_count = [0]
        breaker = CircuitBreaker(failure_threshold=10)

        @retry(max_attempts=3, base_delay=0.01)
        @breaker
        def flaky_service():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Not ready")
            return "success"

        result = flaky_service()
        assert result == "success"
        assert call_count[0] == 3

    def test_fallback_with_timeout(self):
        """Test fallback with timeout."""

        @with_fallback(lambda: "fallback")
        @with_timeout(0.1)
        def slow_with_fallback():
            time.sleep(1.0)
            return "too slow"

        result = slow_with_fallback()
        assert result == "fallback"
