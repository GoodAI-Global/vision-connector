"""Pytest configuration and fixtures for vision-connector tests."""

import os
import sys
from pathlib import Path

import pytest

# Add src to path for testing
src_path = Path(__file__).parent.parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def sample_images_dir(project_root):
    """Get the sample images directory."""
    return project_root / "sample_images"


@pytest.fixture(scope="session")
def config_dir(project_root):
    """Get the config directory."""
    return project_root / "config"


@pytest.fixture
def headless_env():
    """Fixture that removes DISPLAY for headless testing."""
    original = os.environ.get("DISPLAY")
    os.environ.pop("DISPLAY", None)
    yield
    if original:
        os.environ["DISPLAY"] = original
