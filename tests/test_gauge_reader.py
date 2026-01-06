"""Tests for Gauge Reader functionality."""

from pathlib import Path

import numpy as np
import pytest

from vision_connector import GaugeReader

# Get project root for sample files
PROJECT_ROOT = Path(__file__).parent.parent
SAMPLE_GAUGE = PROJECT_ROOT / "sample_images" / "analog_gauge.png"


@pytest.fixture
def gauge_reader():
    """Create a gauge reader instance."""
    return GaugeReader()


class TestGaugeReaderBasic:
    """Basic Gauge Reader tests."""

    def test_reader_initialization(self, gauge_reader):
        """Test that reader initializes correctly."""
        assert gauge_reader is not None
        assert gauge_reader.min_angle == 45
        assert gauge_reader.max_angle == 315

    def test_reader_custom_angles(self):
        """Test reader with custom angle range."""
        reader = GaugeReader(min_angle=30, max_angle=330)
        assert reader.min_angle == 30
        assert reader.max_angle == 330


class TestGaugeReaderReadGauge:
    """Tests for read_analog_gauge functionality."""

    @pytest.mark.skipif(
        not SAMPLE_GAUGE.exists(), reason="Sample gauge image not found"
    )
    def test_read_analog_gauge(self, gauge_reader):
        """Test reading an analog gauge image."""
        result = gauge_reader.read_analog_gauge(
            SAMPLE_GAUGE, min_value=0, max_value=100, unit="PSI"
        )

        assert isinstance(result, dict)
        assert "value" in result
        assert "unit" in result
        assert "confidence" in result

        # Value should be a number or None
        assert result["value"] is None or isinstance(result["value"], (int, float))
        assert result["unit"] == "PSI"

    @pytest.mark.skipif(
        not SAMPLE_GAUGE.exists(), reason="Sample gauge image not found"
    )
    def test_read_gauge_returns_reasonable_value(self, gauge_reader):
        """Test that gauge reading returns value in expected range."""
        result = gauge_reader.read_analog_gauge(
            SAMPLE_GAUGE, min_value=0, max_value=100, unit="PSI"
        )

        if result["value"] is not None:
            # Value should be within the gauge range
            assert 0 <= result["value"] <= 100
            # Confidence should be between 0 and 1
            assert 0 <= result["confidence"] <= 1

    def test_read_gauge_with_numpy_array(self, gauge_reader):
        """Test reading from numpy array input."""
        # Create a simple test image
        img = np.ones((200, 200, 3), dtype=np.uint8) * 200

        result = gauge_reader.read_analog_gauge(
            img, min_value=0, max_value=100, unit="TEST"
        )

        # Should return a result dict (may not find a valid reading)
        assert isinstance(result, dict)
        assert "value" in result
        assert "unit" in result


class TestGaugeReaderAngleCalculation:
    """Tests for angle-to-value conversion."""

    def test_angle_to_value_min(self):
        """Test angle at minimum position."""
        reader = GaugeReader(min_angle=45, max_angle=315)
        # At min_angle, value should be min_value
        value = reader._angle_to_value(45, 0, 100)
        assert value == pytest.approx(0, abs=1)

    def test_angle_to_value_max(self):
        """Test angle at maximum position."""
        reader = GaugeReader(min_angle=45, max_angle=315)
        # At max_angle, value should be max_value
        value = reader._angle_to_value(315, 0, 100)
        assert value == pytest.approx(100, abs=1)

    def test_angle_to_value_mid(self):
        """Test angle at middle position."""
        reader = GaugeReader(min_angle=45, max_angle=315)
        # At midpoint angle, value should be midpoint
        mid_angle = (45 + 315) / 2  # 180 degrees
        value = reader._angle_to_value(mid_angle, 0, 100)
        assert value == pytest.approx(50, abs=5)


class TestGaugeReaderCalibration:
    """Tests for calibration functionality."""

    @pytest.mark.skipif(
        not SAMPLE_GAUGE.exists(), reason="Sample gauge image not found"
    )
    def test_calibration(self, gauge_reader):
        """Test gauge calibration."""
        result = gauge_reader.calibrate(
            SAMPLE_GAUGE, known_value=67.5, min_value=0, max_value=100
        )

        assert isinstance(result, dict)
        # Should have detected angle or error
        assert "detected_angle" in result or "error" in result
