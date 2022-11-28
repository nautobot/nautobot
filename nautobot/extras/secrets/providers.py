"""Secret storage providers built into Nautobot.

Plugins may define and register additional providers in addition to these.
"""
import os

from django import forms
from django.core.exceptions import ValidationError

from nautobot.extras.secrets import SecretsProvider
from nautobot.extras.secrets.exceptions import SecretParametersError, SecretValueNotFoundError
from nautobot.utilities.forms import BootstrapMixin


class EnvironmentVariableSecretsProvider(SecretsProvider):
    """Simple secret provider - retrieve a value stored in an environment variable."""

    slug = "environment-variable"
    name = "Environment Variable"

    class ParametersForm(BootstrapMixin, forms.Form):
        variable = forms.CharField(required=True, help_text="Environment variable name")

    @classmethod
    def get_value_for_secret(cls, secret, obj=None, **kwargs):
        """Retrieve the appropriate environment variable's value."""
        rendered_parameters = secret.rendered_parameters(obj=obj)
        if "variable" not in rendered_parameters:
            raise SecretParametersError(secret, cls, 'The "variable" parameter is mandatory!')
        value = os.getenv(rendered_parameters["variable"], default=None)
        if value is None:
            raise SecretValueNotFoundError(
                secret, cls, f'Undefined environment variable "{rendered_parameters["variable"]}"!'
            )
        return value


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
    def get_value_for_secret(cls, secret, obj=None, **kwargs):
        """
        Retrieve the appropriate text file's contents.

        The value will be stripped of leading and trailing whitespace and newlines.
        """
        rendered_parameters = secret.rendered_parameters(obj=obj)
        if "path" not in rendered_parameters:
            raise SecretParametersError(secret, cls, 'The "path" parameter is mandatory!')
        if not os.path.isfile(rendered_parameters["path"]):
            raise SecretValueNotFoundError(secret, cls, f'File "{rendered_parameters["path"]}" not found!')
        with open(rendered_parameters["path"], "rt", encoding="utf8") as file_handle:
            return file_handle.read().strip()
