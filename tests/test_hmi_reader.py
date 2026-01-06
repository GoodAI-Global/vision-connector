"""Tests for HMI Reader functionality."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from vision_connector import HMIReader
from vision_connector.exceptions import NoDisplayError, RegionError

# Get project root for sample files
PROJECT_ROOT = Path(__file__).parent.parent
SAMPLE_IMAGE = PROJECT_ROOT / "sample_images" / "hmi_screen.png"
SAMPLE_CONFIG = PROJECT_ROOT / "config" / "sample_config.json"


@pytest.fixture
def hmi_reader():
    """Create an HMI reader instance."""
    return HMIReader()


@pytest.fixture
def hmi_reader_with_config():
    """Create an HMI reader with sample config."""
    return HMIReader(config=SAMPLE_CONFIG)


class TestHMIReaderBasic:
    """Basic HMI Reader tests."""

    def test_reader_initialization(self, hmi_reader):
        """Test that reader initializes correctly."""
        assert hmi_reader is not None
        assert hmi_reader.ocr is not None

    def test_reader_with_config_file(self, hmi_reader_with_config):
        """Test reader initialization with config file."""
        assert hmi_reader_with_config is not None
        assert len(hmi_reader_with_config.default_regions) > 0

    def test_reader_with_config_dict(self):
        """Test reader initialization with config dictionary."""
        config = {"regions": {"test_field": {"x": 0, "y": 0, "w": 100, "h": 50}}}
        reader = HMIReader(config=config)
        assert "test_field" in reader.default_regions

    def test_missing_config_file_raises_error(self):
        """Test that missing config file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            HMIReader(config="nonexistent_config.json")


class TestHMIReaderReadImage:
    """Tests for read_image functionality."""

    @pytest.mark.skipif(not SAMPLE_IMAGE.exists(), reason="Sample image not found")
    def test_read_image_with_regions(self, hmi_reader):
        """Test reading image with inline region definitions."""
        regions = {
            "temperature": {"x": 40, "y": 130, "w": 95, "h": 40, "type": "number"},
        }
        result = hmi_reader.read_image(SAMPLE_IMAGE, regions=regions)

        assert isinstance(result, dict)
        assert "temperature" in result

    @pytest.mark.skipif(
        not SAMPLE_IMAGE.exists() or not SAMPLE_CONFIG.exists(),
        reason="Sample files not found",
    )
    def test_read_image_with_config(self, hmi_reader_with_config):
        """Test reading image using config file regions."""
        result = hmi_reader_with_config.read_image(SAMPLE_IMAGE)

        assert isinstance(result, dict)
        assert len(result) > 0

    def test_read_image_no_regions_raises_error(self, hmi_reader):
        """Test that reading without regions raises ValueError."""
        with pytest.raises(RegionError) as exc_info:
            hmi_reader.read_image(SAMPLE_IMAGE)

        assert "No regions specified" in str(exc_info.value)

    def test_read_nonexistent_image_raises_error(self, hmi_reader):
        """Test that nonexistent image raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            hmi_reader.read_image(
                "nonexistent.png", regions={"test": {"x": 0, "y": 0, "w": 10, "h": 10}}
            )


class TestHMIReaderMetadata:
    """Tests for metadata functionality."""

    @pytest.mark.skipif(not SAMPLE_IMAGE.exists(), reason="Sample image not found")
    def test_read_image_with_metadata(self, hmi_reader):
        """Test reading with confidence metadata."""
        regions = {
            "temperature": {"x": 40, "y": 130, "w": 95, "h": 40, "type": "number"},
        }
        result = hmi_reader.read_image_with_metadata(SAMPLE_IMAGE, regions=regions)

        assert isinstance(result, dict)
        assert "temperature" in result
        assert "value" in result["temperature"]
        assert "confidence" in result["temperature"]
        assert "region" in result["temperature"]


class TestHMIReaderConfig:
    """Tests for config file handling."""

    def test_config_loading_from_json(self):
        """Test that JSON config loads correctly."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "regions": {
                    "field1": {"x": 10, "y": 20, "w": 30, "h": 40},
                    "field2": {"x": 50, "y": 60, "w": 70, "h": 80},
                }
            }
            json.dump(config, f)
            f.flush()

            reader = HMIReader(config=f.name)
            assert "field1" in reader.default_regions
            assert "field2" in reader.default_regions
            assert reader.default_regions["field1"]["x"] == 10

            os.unlink(f.name)

    def test_create_sample_config(self):
        """Test sample config creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.json"
            HMIReader.create_sample_config(config_path)

            assert config_path.exists()

            with open(config_path) as f:
                config = json.load(f)

            assert "regions" in config
            assert "capture" in config


class TestHeadlessOperation:
    """Tests for headless operation."""

    def test_no_display_roi_selection_error(self, hmi_reader):
        """Test that interactive ROI selection fails in headless environment."""
        # Temporarily unset DISPLAY
        original_display = os.environ.get("DISPLAY")
        os.environ.pop("DISPLAY", None)

        try:
            # Should raise NoDisplayError in headless environment
            with pytest.raises(NoDisplayError) as exc_info:
                hmi_reader.select_roi_interactive(SAMPLE_IMAGE)

            assert "No display available" in str(exc_info.value)
            assert "config" in str(exc_info.value).lower()

        finally:
            # Restore DISPLAY
            if original_display:
                os.environ["DISPLAY"] = original_display
