"""Secret storage providers built into Nautobot.

Plugins may define and register additional providers in addition to these.
"""
import logging
import os

from django import forms

from nautobot.extras.secrets import SecretsProvider
from nautobot.utilities.forms import BootstrapMixin


logger = logging.getLogger(__name__)


class EnvironmentVariableSecretsProvider(SecretsProvider):
    """Simple secret provider - retrieve a value stored in an environment variable."""

    slug = "environment-variable"
    name = "environment variable"

    class ParametersForm(BootstrapMixin, forms.Form):
        variable = forms.CharField(required=True, help_text="Environment variable name")

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

    class ParametersForm(BootstrapMixin, forms.Form):
        path = forms.CharField(required=True, help_text="Absolute filesystem path to the file")

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
