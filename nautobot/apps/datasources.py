"""Utilities for an app to register datasource contents (for Git, etc.)."""

from nautobot.extras.datasources import get_repo_access_url
from nautobot.extras.registry import DatasourceContent

__all__ = ("DatasourceContent", "get_repo_access_url")
