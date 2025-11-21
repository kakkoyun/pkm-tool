"""Configuration management for PKM tool."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class SourceConfig(BaseModel):
    """Configuration for a data source."""

    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class Config(BaseModel):
    """Main configuration for PKM tool."""

    apple_calendar: SourceConfig = Field(default_factory=SourceConfig)
    github: SourceConfig = Field(default_factory=SourceConfig)
    atlassian: SourceConfig = Field(default_factory=SourceConfig)
    things: SourceConfig = Field(default_factory=SourceConfig)
    wakatime: SourceConfig = Field(default_factory=SourceConfig)
    google_docs: SourceConfig = Field(default_factory=SourceConfig)


def load_config(config_path: str | None = None) -> Config:
    """
    Load configuration from file or use defaults.

    Args:
        config_path: Path to configuration YAML file

    Returns:
        Config object
    """
    if config_path is None:
        # Try default locations
        default_paths = [
            Path.home() / ".config" / "pkm-tool" / "config.yaml",
            Path.home() / ".pkm-tool.yaml",
            Path.cwd() / "pkm-tool.yaml",
        ]
        for path in default_paths:
            if path.exists():
                config_path = str(path)
                break

    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            config_data = yaml.safe_load(f) or {}
        return Config(**config_data)

    return Config()
