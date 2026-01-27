from pathlib import Path
import yaml


class ConfigError(Exception):
    pass


def load_config(config_dir: Path) -> dict:
    """
    taitan.yaml 로드
    """
    config_path = config_dir / "taitan.yaml"

    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        raise ConfigError(f"Failed to load config: {e}")

    validate_config(config)
    return config


def validate_config(config: dict):
    """
    최소한의 필수 키 검증
    """
    required_sections = ["app", "scheduler", "trading", "log"]

    for key in required_sections:
        if key not in config:
            raise ConfigError(f"Missing config section: {key}")
