"""Configuration management for PKM tool."""

from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import BaseModel, Field, field_validator

logger = structlog.get_logger(__name__)


# Default section titles with emojis (keyed by source name in config)
DEFAULT_SOURCE_TITLES: dict[str, str] = {
    "apple_calendar": "📅 Calendar Events",
    "github": "🐙 GitHub Activities",
    "atlassian": "🏢 Atlassian (Jira/Confluence)",
    "things": "✅ Things - Completed Tasks",
    "wakatime": "⏱️ Wakatime - Coding Activity",
    "google_docs": "📝 Google Docs",
    "whoop": "💪 Whoop Health Data",
}

# Errors title (always last, in folded format)
ERRORS_TITLE: str = "⚠️ Errors"

# OAuth configuration defaults for sources requiring OAuth2 authentication.
# These are used as fallbacks when not explicitly configured in config.yaml.
#
# Example Whoop OAuth configuration in config.yaml:
# whoop:
#   enabled: true
#   config:
#     client_id: "your-client-id"
#     client_secret: "your-client-secret"
#     callback_port: 8642  # Optional, default 8642
#     scopes:  # Optional, defaults shown below
#       - read:recovery
#       - read:sleep
#       - read:workout
#       - offline
#
# Example Google Docs OAuth configuration in config.yaml:
# google_docs:
#   enabled: true
#   config:
#     client_id: "your-client-id"
#     client_secret: "your-client-secret"
#     scopes:  # Optional, default shown below
#       - https://www.googleapis.com/auth/drive.readonly

WHOOP_DEFAULT_CONFIG: dict[str, Any] = {
    "callback_port": 8642,
    "scopes": ["read:recovery", "read:sleep", "read:workout", "offline"],
}

GOOGLE_DOCS_DEFAULT_CONFIG: dict[str, Any] = {
    "scopes": ["https://www.googleapis.com/auth/drive.readonly"],
}


class SourceConfig(BaseModel):
    """Configuration for a data source."""

    enabled: bool = True
    exclude_weekends: bool = False
    title: str | None = None  # Custom section title, uses default if None
    order: int | None = None  # Custom order, uses config definition order if None
    preferred_browser: str | None = None  # Browser for OAuth flows, falls back to global if None
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("config", mode="before")
    @classmethod
    def config_none_to_empty_dict(cls, v: Any) -> dict[str, Any]:
        """Convert None to empty dict for YAML compatibility.

        YAML parses `config:` followed by only comments as None, not {}.
        This validator ensures those cases don't cause validation errors.
        """
        if v is None:
            return {}
        return v


class CacheConfig(BaseModel):
    """Configuration for HTTP response cache."""

    enabled: bool = True
    directory: str = ".pkm-cache"  # Local directory, easy to clean
    ttl_hours: int = 24  # Cache expiration time in hours


class RetryConfig(BaseModel):
    """Configuration for HTTP request retries."""

    enabled: bool = True
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds


class Config(BaseModel):
    """Main configuration for PKM tool."""

    # Browser settings
    preferred_browser: str | None = None  # None = system default

    # Output settings
    output_filename_template: str = "{date} ({day_abbr}).{format}"
    output_directory: str = "."

    # Cache settings
    cache: CacheConfig = Field(default_factory=CacheConfig)

    # Retry settings
    retry: RetryConfig = Field(default_factory=RetryConfig)

    # Source configurations (order here defines default display order)
    apple_calendar: SourceConfig = Field(default_factory=SourceConfig)
    github: SourceConfig = Field(default_factory=SourceConfig)
    atlassian: SourceConfig = Field(default_factory=SourceConfig)
    things: SourceConfig = Field(default_factory=SourceConfig)
    wakatime: SourceConfig = Field(default_factory=SourceConfig)
    google_docs: SourceConfig = Field(default_factory=SourceConfig)
    whoop: SourceConfig = Field(default_factory=SourceConfig)

    def get_source_title(self, source_name: str) -> str:
        """Get title for a source, using custom title if set or default."""
        source_config = getattr(self, source_name, None)
        if source_config and source_config.title:
            return source_config.title
        return DEFAULT_SOURCE_TITLES.get(source_name, source_name.replace("_", " ").title())

    def get_ordered_sources(self) -> list[str]:
        """Get list of source names ordered by their order field or config definition order."""
        # All source names in config definition order
        sources = [
            "apple_calendar",
            "github",
            "atlassian",
            "things",
            "wakatime",
            "google_docs",
            "whoop",
        ]

        def get_order_key(source_name: str) -> tuple[int, int]:
            """Return (has_order, order_value) for sorting."""
            source_config = getattr(self, source_name, None)
            if source_config and source_config.order is not None:
                # Has explicit order - sort by it first
                return (0, source_config.order)
            # No explicit order - maintain config definition order
            return (1, sources.index(source_name))

        return sorted(sources, key=get_order_key)


def load_config(config_path: str | None = None) -> Config:
    """
    Load configuration from file or use defaults.

    Args:
        config_path: Path to configuration YAML file

    Returns:
        Config object
    """
    if config_path is None:
        # Try default locations (in order of preference)
        # 1. Current directory (project-specific config)
        # 2. Home directory (user config)
        # 3. XDG config directory (system standard)
        default_paths = [
            # Project-level config (current directory)
            Path.cwd() / ".pkm.yaml",
            Path.cwd() / ".pkm.yml",
            Path.cwd() / "pkm-tool.yaml",
            # User-level config (home directory)
            Path.home() / ".pkm.yaml",
            Path.home() / ".pkm.yml",
            Path.home() / ".pkm-tool.yaml",
            # XDG config directory
            Path.home() / ".config" / "pkm-tool" / "config.yaml",
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
