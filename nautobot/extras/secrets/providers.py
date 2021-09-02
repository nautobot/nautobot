"""Secret storage providers built into Nautobot.

Plugins may define and register additional providers in addition to these.
"""
from abc import ABC, abstractmethod, abstractproperty
import logging
import os


logger = logging.getLogger(__name__)


class SecretsProvider(ABC):
    """Abstract base class for concrete providers of secret retrieval features."""

    @abstractproperty
    def slug(self):
        """String uniquely identifying this class; will be used as a key to look up the class owning a given Secret."""

    @property
    def name(self):
        """Human-friendly name for this class, falling back to the slug if not overridden."""
        return self.slug

    @classmethod
    @abstractmethod
    def get_value_for_secret(cls, secret):
        """Retrieve the stored value described by the given Secret record."""


class EnvironmentVariableSecretsProvider(SecretsProvider):
    """Simple secret provider - retrieve a value stored in an environment variable."""

    slug = "environment-variable"
    name = "environment variable"

    @classmethod
    def get_value_for_secret(cls, secret):
        """Retrieve the appropriate environment variable's value."""
        if "variable" not in secret.parameters:
            logger.error('Secret "%s" is lacking a "variable" parameter!', secret)
        else:
            return os.getenv(secret.parameters["variable"])
        return None


class TextFileSecretsProvider(SecretsProvider):
    """Simple secret provider - retrieve a value stored in a text file on the filesystem."""

    slug = "text-file"
    name = "text file"

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
