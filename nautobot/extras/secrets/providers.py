"""Secret storage providers built into Nautobot.

Plugins may define and register additional providers in addition to these.
"""
from abc import ABC, abstractmethod
import logging
import os


logger = logging.getLogger(__name__)


class SecretProvider(ABC):
    """Abstract base class for concrete providers of secret retrieval features."""

    @classmethod
    @abstractmethod
    def get_value_for_secret(cls, secret):
        """Retrieve the stored value described by the given Secret record."""


class EnvironmentVariable(SecretProvider):
    """Simple secret provider - retrieve a value stored in an environment variable."""

    @classmethod
    def get_value_for_secret(cls, secret):
        """Retrieve the appropriate environment variable's value."""
        if "variable" in secret.parameters:
            return os.getenv(secret.parameters["variable"])
        logger.error('Secret "%s" is lacking a "variable" parameter!', secret)
        return None
