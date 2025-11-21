"""PKM Tool - Personal Knowledge Management Tool."""

__version__ = "0.1.0"

from pkm_tool.aggregator import aggregate_data
from pkm_tool.config import Config, load_config
from pkm_tool.formatters import format_as_json, format_as_markdown
from pkm_tool.models import AggregatedData

__all__ = [
    "AggregatedData",
    "Config",
    "aggregate_data",
    "format_as_json",
    "format_as_markdown",
    "load_config",
]
