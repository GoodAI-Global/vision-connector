"""
Tests for the configuration management module.
"""

import os
import pytest
import tempfile
from pathlib import Path

from vision_connector.config import (
    Config,
    ConfigurationError,
    load_config,
    config,
)


class TestConfigBasic:
    """Basic Config class tests."""

    def test_config_creation(self):
        """Test creating a new config instance."""
        cfg = Config()
        assert isinstance(cfg, Config)

    def test_config_with_defaults(self):
        """Test config with default values."""
        defaults = {"key": "value", "nested": {"key": "nested_value"}}
        cfg = Config(defaults=defaults)

        assert cfg.get("key") == "value"
        assert cfg.get("nested.key") == "nested_value"

    def test_global_config_exists(self):
        """Test global config instance exists."""
        assert config is not None
        assert isinstance(config, Config)


class TestConfigGet:
    """Tests for Config.get method."""

    def test_get_simple_key(self):
        """Test getting a simple key."""
        cfg = Config()
        cfg.set("key", "value")

        assert cfg.get("key") == "value"

    def test_get_nested_key(self):
        """Test getting nested keys with dot notation."""
        cfg = Config()
        cfg.set("mqtt.broker", "localhost")
        cfg.set("mqtt.port", 1883)

        assert cfg.get("mqtt.broker") == "localhost"
        assert cfg.get("mqtt.port") == 1883

    def test_get_with_default(self):
        """Test getting with default value."""
        cfg = Config()

        assert cfg.get("missing", default="default") == "default"
        assert cfg.get("missing.nested", default=42) == 42

    def test_get_with_cast(self):
        """Test getting with type casting."""
        cfg = Config()
        cfg.set("port", "8080")
        cfg.set("enabled", "true")

        assert cfg.get("port", cast=int) == 8080
        assert cfg.get("enabled") == "true"

    def test_get_required_missing_raises(self):
        """Test required key missing raises error."""
        cfg = Config()

        with pytest.raises(ConfigurationError):
            cfg.get("missing", required=True)

    def test_get_cast_failure_raises(self):
        """Test invalid cast raises error."""
        cfg = Config()
        cfg.set("port", "not_a_number")

        with pytest.raises(ConfigurationError):
            cfg.get("port", cast=int)


class TestConfigSet:
    """Tests for Config.set method."""

    def test_set_simple_key(self):
        """Test setting a simple key."""
        cfg = Config()
        cfg.set("key", "value")

        assert cfg.get("key") == "value"

    def test_set_nested_key(self):
        """Test setting nested keys."""
        cfg = Config()
        cfg.set("mqtt.broker", "localhost")

        assert cfg.get("mqtt.broker") == "localhost"

    def test_set_overwrites_value(self):
        """Test setting overwrites existing value."""
        cfg = Config()
        cfg.set("key", "value1")
        cfg.set("key", "value2")

        assert cfg.get("key") == "value2"


class TestConfigEnv:
    """Tests for loading from environment variables."""

    def setup_method(self):
        """Clear test environment variables."""
        for key in list(os.environ.keys()):
            if key.startswith("TEST_"):
                del os.environ[key]

    def teardown_method(self):
        """Clear test environment variables."""
        for key in list(os.environ.keys()):
            if key.startswith("TEST_"):
                del os.environ[key]

    def test_load_env_simple(self):
        """Test loading simple environment variable."""
        os.environ["TEST_KEY"] = "value"

        cfg = Config()
        cfg.load_env(prefix="TEST_")

        assert cfg.get("key") == "value"

    def test_load_env_nested(self):
        """Test loading nested environment variables."""
        os.environ["TEST_MQTT__BROKER"] = "localhost"
        os.environ["TEST_MQTT__PORT"] = "1883"

        cfg = Config()
        cfg.load_env(prefix="TEST_")

        assert cfg.get("mqtt.broker") == "localhost"
        assert cfg.get("mqtt.port") == 1883  # Auto-converted to int

    def test_load_env_boolean(self):
        """Test boolean parsing from env."""
        os.environ["TEST_ENABLED"] = "true"
        os.environ["TEST_DISABLED"] = "false"

        cfg = Config()
        cfg.load_env(prefix="TEST_")

        assert cfg.get("enabled") is True
        assert cfg.get("disabled") is False

    def test_load_env_list(self):
        """Test list parsing from env."""
        os.environ["TEST_HOSTS"] = "host1,host2,host3"

        cfg = Config()
        cfg.load_env(prefix="TEST_")

        assert cfg.get("hosts") == ["host1", "host2", "host3"]


class TestConfigMerge:
    """Tests for configuration merging."""

    def test_defaults_merge(self):
        """Test defaults are merged with config."""
        defaults = {"key1": "default1", "key2": "default2"}
        cfg = Config(defaults=defaults)
        cfg.set("key1", "overridden")

        assert cfg.get("key1") == "overridden"
        assert cfg.get("key2") == "default2"

    def test_env_overrides_file(self):
        """Test environment variables override file config."""
        os.environ["TEST_KEY"] = "from_env"

        cfg = Config(defaults={"key": "from_default"})
        cfg.load_env(prefix="TEST_")

        assert cfg.get("key") == "from_env"

        # Cleanup
        del os.environ["TEST_KEY"]


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_validate_required(self):
        """Test required field validation."""
        cfg = Config()
        cfg.set("present", "value")

        schema = {
            "present": {"required": True},
            "missing": {"required": True},
        }

        errors = cfg.validate(schema)
        assert len(errors) == 1
        assert "missing" in errors[0]

    def test_validate_type(self):
        """Test type validation."""
        cfg = Config()
        cfg.set("port", "not_an_int")

        schema = {
            "port": {"type": int},
        }

        errors = cfg.validate(schema)
        assert len(errors) == 1
        assert "port" in errors[0]

    def test_validate_min_max(self):
        """Test min/max validation."""
        cfg = Config()
        cfg.set("port", 100)

        schema = {
            "port": {"type": int, "min": 1, "max": 65535},
        }

        errors = cfg.validate(schema)
        assert len(errors) == 0

    def test_validate_value_below_min(self):
        """Test value below minimum."""
        cfg = Config()
        cfg.set("port", -1)

        schema = {
            "port": {"type": int, "min": 0},
        }

        errors = cfg.validate(schema)
        assert len(errors) == 1
        assert "below minimum" in errors[0]


class TestConfigToDict:
    """Tests for to_dict method."""

    def test_to_dict(self):
        """Test exporting config to dict."""
        cfg = Config(defaults={"default_key": "default_value"})
        cfg.set("key", "value")

        result = cfg.to_dict()

        assert result["key"] == "value"
        assert result["default_key"] == "default_value"


class TestLoadConfig:
    """Tests for load_config helper function."""

    def setup_method(self):
        """Clear test environment variables."""
        for key in list(os.environ.keys()):
            if key.startswith("TEST_"):
                del os.environ[key]

    def teardown_method(self):
        """Clear test environment variables."""
        for key in list(os.environ.keys()):
            if key.startswith("TEST_"):
                del os.environ[key]

    def test_load_config_with_env(self):
        """Test load_config with environment variables."""
        os.environ["TEST_KEY"] = "value"

        cfg = load_config(env_prefix="TEST_")

        assert cfg.get("key") == "value"

    def test_load_config_with_defaults(self):
        """Test load_config with defaults."""
        defaults = {"key": "default_value"}

        cfg = load_config(defaults=defaults, env_prefix="NONEXISTENT_")

        assert cfg.get("key") == "default_value"


class TestConfigRepr:
    """Tests for Config representation."""

    def test_repr(self):
        """Test Config repr."""
        cfg = Config()
        cfg.set("key1", "value1")
        cfg.set("key2", "value2")

        repr_str = repr(cfg)
        assert "Config" in repr_str
        assert "2" in repr_str
