"""
Configuration management for Leto BLRM.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import json


@dataclass
class LetoBLRMConfig:
    """Configuration for Leto BLRM job runs."""

    name: str = "leto_blrm_v0_1"
    input_path: str = "data/leto_blrm_input/sample.csv"
    output_dir: str = "data/leto_blrm_runs"
    n_scenarios: int = 5
    max_runtime_sec: int = 300
    seed: int = 42

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LetoBLRMConfig":
        """Create config from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def load_config(path: Optional[str] = None) -> LetoBLRMConfig:
    """
    Load configuration from file or return defaults.

    Args:
        path: Path to config file (JSON or YAML). If None, returns defaults.

    Returns:
        LetoBLRMConfig instance
    """
    if path is None:
        return LetoBLRMConfig()

    config_path = Path(path)

    if not config_path.exists():
        print(f"Config file not found: {path}, using defaults")
        return LetoBLRMConfig()

    # Load based on extension
    if config_path.suffix == ".json":
        with open(config_path, "r") as f:
            data = json.load(f)
        return LetoBLRMConfig.from_dict(data)

    elif config_path.suffix in [".yaml", ".yml"]:
        try:
            import yaml
            with open(config_path, "r") as f:
                data = yaml.safe_load(f)
            return LetoBLRMConfig.from_dict(data)
        except ImportError:
            print("PyYAML not installed, falling back to defaults")
            return LetoBLRMConfig()

    else:
        print(f"Unsupported config format: {config_path.suffix}, using defaults")
        return LetoBLRMConfig()
