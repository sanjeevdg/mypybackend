
from pathlib import Path
import yaml

CONFIG_DIR = Path(__file__).parent / "config"

CONFIG_FILE = CONFIG_DIR / "customer_master_detail.yaml"
SHARED_CONFIG_FILE = CONFIG_DIR / "shared.yaml"


def load_yaml():
    """Load the existing customer master-detail page configuration."""
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_shared_yaml():
    """Load reusable application configuration."""
    if not SHARED_CONFIG_FILE.exists():
        return {}

    with SHARED_CONFIG_FILE.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def deep_merge(base, override):
    """Merge page configuration over shared defaults."""
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override

    result = base.copy()

    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result
