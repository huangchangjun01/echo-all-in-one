import os
import re
import yaml
from pathlib import Path
from loguru import logger


def _resolve_env_vars(value: str) -> str:
    """Resolve ${VAR_NAME} patterns in a string value using environment variables."""
    pattern = re.compile(r"\$\{([^}]+)\}")
    result = value
    for match in pattern.finditer(value):
        var_name = match.group(1)
        env_value = os.environ.get(var_name, "")
        if not env_value:
            logger.warning(f"Environment variable '{var_name}' is not set, using empty string")
        result = result.replace(match.group(0), env_value)
    return result


def _resolve_config(obj):
    """Recursively resolve environment variables in config values."""
    if isinstance(obj, dict):
        return {k: _resolve_config(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_config(item) for item in obj]
    elif isinstance(obj, str):
        return _resolve_env_vars(obj)
    return obj


class Config:
    """Application configuration loaded from YAML file."""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        self._config_path = Path(config_path)
        self._data = {}
        self._load()

    def _load(self):
        if not self._config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self._config_path}")
        with open(self._config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        self._data = _resolve_config(raw) or {}
        logger.info(f"Config loaded from {self._config_path}")

    @property
    def server(self) -> dict:
        return self._data.get("server", {})

    @property
    def storage(self) -> dict:
        return self._data.get("storage", {})

    @property
    def llm(self) -> dict:
        return self._data.get("llm", {})

    @property
    def vector_store(self) -> dict:
        return self._data.get("vector_store", {})

    @property
    def log(self) -> dict:
        return self._data.get("log", {})

    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default


config = Config()