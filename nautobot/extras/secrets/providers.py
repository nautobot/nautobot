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


class EnvironmentVariableSecretProvider(SecretProvider):
    """Simple secret provider - retrieve a value stored in an environment variable."""

    @classmethod
    def get_value_for_secret(cls, secret):
        """Retrieve the appropriate environment variable's value."""
        if "variable" not in secret.parameters:
            logger.error('Secret "%s" is lacking a "variable" parameter!', secret)
        else:
            return os.getenv(secret.parameters["variable"])
        return None


class TextFileSecretProvider(SecretProvider):
    """Simple secret provider - retrieve a value stored in a text file on the filesystem."""

    @classmethod
    def get_value_for_secret(cls, secret):
        """Retrieve the appropriate text file's contents."""
        if "path" not in secret.parameters:
            logger.error('Secret "%s" is lacking a "path" parameter!', secret)
        elif not os.path.isfile(secret.parameters["path"]):
            logger.error('Secret "%s" points to nonexistent file "%s"!', secret, secret.parameters["path"])
        else:
            with open(secret.parameters["path"], "rt", encoding="utf8") as file_handle:
                return file_handle.read()
        return None
