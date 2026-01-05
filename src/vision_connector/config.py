"""
Configuration management for vision-connector.

Provides enterprise-grade configuration with:
- YAML file support
- Environment variable overrides
- Type validation
- Default values
- Configuration merging
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from vision_connector.logging import get_logger

_logger = get_logger(__name__)

# Track if PyYAML is available
_yaml_available = False

try:
    import yaml
    _yaml_available = True
except ImportError:
    pass


T = TypeVar("T")


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass


class Config:
    """
    Configuration manager for vision-connector.

    Supports loading from YAML files and environment variables.
    Environment variables override file-based config.

    Example:
        >>> config = Config()
        >>> config.load_file("config.yaml")
        >>> # Or load from environment
        >>> config.load_env(prefix="VISION_")
        >>>
        >>> # Access configuration
        >>> broker = config.get("mqtt.broker", default="localhost")
        >>> port = config.get("mqtt.port", default=1883, cast=int)

    Environment Variable Naming:
        Nested keys use double underscore: VISION_MQTT__BROKER=localhost
    """

    def __init__(self, defaults: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration.

        Args:
            defaults: Optional default values.
        """
        self._config: Dict[str, Any] = {}
        self._defaults: Dict[str, Any] = defaults or {}
        self._env_prefix: Optional[str] = None

        _logger.debug("Config initialized", has_defaults=bool(defaults))

    def load_file(self, path: Union[str, Path]) -> "Config":
        """
        Load configuration from a YAML file.

        Args:
            path: Path to YAML configuration file.

        Returns:
            Self for chaining.

        Raises:
            ConfigurationError: If file cannot be loaded or parsed.
            FileNotFoundError: If file doesn't exist.
        """
        if not _yaml_available:
            raise ConfigurationError(
                "PyYAML is required for YAML configuration. "
                "Install with: pip install pyyaml"
            )

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        _logger.debug("Loading config file", path=str(path))

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}

            if not isinstance(data, dict):
                raise ConfigurationError(
                    f"Configuration file must contain a dictionary, got {type(data).__name__}"
                )

            self._config = self._merge_dicts(self._config, data)
            _logger.info("Config loaded from file", path=str(path), keys=len(data))

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {path}: {e}") from e

        return self

    def load_env(
        self,
        prefix: str = "VISION_",
        separator: str = "__",
    ) -> "Config":
        """
        Load configuration from environment variables.

        Environment variables with the given prefix are loaded.
        Nested keys use the separator (default: double underscore).

        Example:
            VISION_MQTT__BROKER=localhost -> {"mqtt": {"broker": "localhost"}}
            VISION_LOG_LEVEL=DEBUG -> {"log_level": "DEBUG"}

        Args:
            prefix: Prefix for environment variables.
            separator: Separator for nested keys.

        Returns:
            Self for chaining.
        """
        self._env_prefix = prefix
        env_config: Dict[str, Any] = {}

        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue

            # Remove prefix and convert to config key
            config_key = key[len(prefix):].lower()

            # Handle nested keys (double underscore)
            if separator in config_key:
                parts = config_key.split(separator)
                current = env_config
                for part in parts[:-1]:
                    current = current.setdefault(part, {})
                current[parts[-1]] = self._parse_env_value(value)
            else:
                env_config[config_key] = self._parse_env_value(value)

        if env_config:
            self._config = self._merge_dicts(self._config, env_config)
            _logger.info(
                "Config loaded from environment",
                prefix=prefix,
                vars_loaded=len(env_config),
            )

        return self

    def _parse_env_value(self, value: str) -> Any:
        """
        Parse environment variable value to appropriate type.

        Handles booleans, integers, floats, and lists.
        """
        # Boolean
        if value.lower() in ("true", "yes", "1", "on"):
            return True
        if value.lower() in ("false", "no", "0", "off"):
            return False

        # Integer
        try:
            return int(value)
        except ValueError:
            pass

        # Float
        try:
            return float(value)
        except ValueError:
            pass

        # List (comma-separated)
        if "," in value:
            return [v.strip() for v in value.split(",")]

        # String
        return value

    def _merge_dicts(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_dicts(result[key], value)
            else:
                result[key] = value

        return result

    def get(
        self,
        key: str,
        default: Optional[T] = None,
        cast: Optional[Type[T]] = None,
        required: bool = False,
    ) -> Optional[T]:
        """
        Get a configuration value.

        Supports nested keys with dot notation: "mqtt.broker"

        Args:
            key: Configuration key (dot-separated for nested).
            default: Default value if key not found.
            cast: Optional type to cast the value to.
            required: If True, raise error if key not found.

        Returns:
            Configuration value.

        Raises:
            ConfigurationError: If required key is missing or cast fails.
        """
        value = self._get_nested(key, self._config)

        if value is None:
            value = self._get_nested(key, self._defaults)

        if value is None:
            if required:
                raise ConfigurationError(f"Required configuration key not found: {key}")
            return default

        if cast is not None:
            try:
                value = cast(value)
            except (ValueError, TypeError) as e:
                raise ConfigurationError(
                    f"Cannot cast config value '{key}' to {cast.__name__}: {e}"
                ) from e

        return value

    def _get_nested(self, key: str, data: Dict) -> Any:
        """Get nested value using dot notation."""
        parts = key.split(".")
        current = data

        for part in parts:
            if not isinstance(current, dict):
                return None
            current = current.get(part)
            if current is None:
                return None

        return current

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key (dot-separated for nested).
            value: Value to set.
        """
        parts = key.split(".")
        current = self._config

        for part in parts[:-1]:
            current = current.setdefault(part, {})

        current[parts[-1]] = value
        _logger.debug("Config value set", key=key)

    def to_dict(self) -> Dict[str, Any]:
        """
        Export configuration as dictionary.

        Returns:
            Configuration dictionary.
        """
        return self._merge_dicts(self._defaults, self._config)

    def validate(self, schema: Dict[str, Any]) -> List[str]:
        """
        Validate configuration against a schema.

        Schema format:
            {
                "mqtt.broker": {"type": str, "required": True},
                "mqtt.port": {"type": int, "default": 1883},
            }

        Args:
            schema: Validation schema.

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        for key, rules in schema.items():
            value = self.get(key)

            # Check required
            if rules.get("required", False) and value is None:
                errors.append(f"Required key missing: {key}")
                continue

            # Check type
            if value is not None and "type" in rules:
                expected_type = rules["type"]
                if not isinstance(value, expected_type):
                    errors.append(
                        f"Invalid type for {key}: expected {expected_type.__name__}, "
                        f"got {type(value).__name__}"
                    )

            # Check min/max for numbers
            if value is not None and isinstance(value, (int, float)):
                if "min" in rules and value < rules["min"]:
                    errors.append(f"Value for {key} below minimum: {value} < {rules['min']}")
                if "max" in rules and value > rules["max"]:
                    errors.append(f"Value for {key} above maximum: {value} > {rules['max']}")

        if errors:
            _logger.warning("Configuration validation failed", errors=errors)
        else:
            _logger.debug("Configuration validation passed")

        return errors

    def __repr__(self) -> str:
        return f"Config({len(self._config)} keys)"


# Global configuration instance
config = Config()


def load_config(
    file_path: Optional[Union[str, Path]] = None,
    env_prefix: str = "VISION_",
    defaults: Optional[Dict[str, Any]] = None,
) -> Config:
    """
    Load configuration from file and environment.

    Environment variables take precedence over file config.

    Args:
        file_path: Optional path to YAML config file.
        env_prefix: Prefix for environment variables.
        defaults: Optional default values.

    Returns:
        Configured Config instance.

    Example:
        >>> config = load_config(
        ...     file_path="config.yaml",
        ...     env_prefix="VISION_",
        ...     defaults={"mqtt": {"port": 1883}}
        ... )
    """
    cfg = Config(defaults=defaults)

    if file_path:
        cfg.load_file(file_path)

    cfg.load_env(prefix=env_prefix)

    return cfg
