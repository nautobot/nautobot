"""Secret storage providers built into Nautobot.

Plugins may define and register additional providers in addition to these.
"""
import logging
import os

from django import forms
from django.core.exceptions import ValidationError

from nautobot.extras.secrets import SecretsProvider
from nautobot.utilities.forms import BootstrapMixin


logger = logging.getLogger(__name__)


class EnvironmentVariableSecretsProvider(SecretsProvider):
    """Simple secret provider - retrieve a value stored in an environment variable."""

    slug = "environment-variable"
    name = "Environment Variable"

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
    name = "Text File"

    class ParametersForm(BootstrapMixin, forms.Form):
        path = forms.CharField(required=True, help_text="Absolute filesystem path to the file")

        def clean(self):
            """Prevent some path-related trickery."""
            super().clean()

            path = self.cleaned_data.get("path", "")
            if not path.startswith("/"):
                raise ValidationError("Path must be an absolute path, not a relative one")
            if ".." in path:
                raise ValidationError("Illegal character sequence in path")

            return self.cleaned_data

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
