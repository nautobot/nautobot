"""Secret storage providers built into Nautobot.

Plugins may define and register additional providers in addition to these.
"""
from abc import ABC, abstractmethod
import logging
import os

import pkg_resources


logger = logging.getLogger(__name__)


class SecretProvider(ABC):
    """Abstract base class for concrete providers of secret retrieval features."""

    @classmethod
    @abstractmethod
    def get_value_for_secret(cls, secret):
        """Retrieve the stored value described by the given Secret record."""

    @staticmethod
    def available_provider_names():
        """Get the listing of registered provider names currently available."""
        return sorted(
            set(entry_point.name for entry_point in pkg_resources.iter_entry_points("nautobot.secrets.providers"))
        )

    @staticmethod
    def get_providers(name):
        """Get the provider class(es) registered under the given name."""
        # Should only be one matching entry point but in theory multiple plugins could register the same name...
        for entry_point in pkg_resources.iter_entry_points("nautobot.secrets.providers", name=name):
            yield entry_point.load()

    @staticmethod
    def name_to_display(name):
        """Convert a provider entrypoint name to a more user-friendly display name.

        provider_name_to_display("constant-value") -> "Constant Value"
        provider_name_to_display("AWS-secrets-manager") -> "AWS Secrets Manager"
        """
        # For display value, replace "-" with " " in the provider names, and convert to title-case where appropriate.
        # See also nautobot.utilities.templatetags.helpers.bettertitle()
        return " ".join(w[0].upper() + w[1:] for w in name.split("-"))


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
