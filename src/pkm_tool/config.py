"""Configuration management for PKM tool."""

from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


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
    whoop: SourceConfig = Field(default_factory=SourceConfig)


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
        logger.debug("searching_for_config_file", paths=[str(p) for p in default_paths])
        for path in default_paths:
            logger.debug("checking_config_path", path=str(path), exists=path.exists())
            if path.exists():
                config_path = str(path)
                logger.info("config_file_found", path=config_path)
                break
        else:
            logger.info("no_config_file_found", message="Using default configuration")

    if config_path and Path(config_path).exists():
        logger.info("loading_config_file", path=config_path)
        try:
            with open(config_path) as f:
                config_data = yaml.safe_load(f) or {}
            logger.debug("config_file_loaded", path=config_path, keys=list(config_data.keys()))
            return Config(**config_data)
        except Exception as e:
            logger.error("config_file_load_failed", path=config_path, error=str(e), exc_info=True)
            logger.warning("using_default_config", reason="Failed to load config file")
            return Config()

    logger.info("using_default_config", reason="No config file specified or found")
    return Config()
