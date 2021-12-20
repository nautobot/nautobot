from django import forms

from nautobot.utilities.forms import BootstrapMixin
from nautobot.extras.secrets import SecretsProvider


class ConstantValueSecretsProvider(SecretsProvider):
    """
    Example of a plugin-provided SecretsProvider - this one just uses a user-specified constant value.

    Obviously this is insecure and not something you'd want to actually use!
    """

    slug = "constant-value"
    name = "Constant Value"

    class ParametersForm(BootstrapMixin, forms.Form):
        """
        User-friendly form for specifying the required parameters of this provider.
        """

        constant = forms.CharField(
            required=True,
            help_text="Constant secret value. <strong>Example Only - DO NOT USE FOR REAL SENSITIVE DATA</strong>",
        )

    @classmethod
    def get_value_for_secret(cls, secret, obj=None, **kwargs):
        """
        Return the value defined in the Secret.parameters "constant" key.

        A more realistic SecretsProvider would make calls to external APIs, etc. to retrieve a secret from storage.

        Args:
            secret (nautobot.extras.models.Secret): The secret whose value should be retrieved.
            obj (object): The object (Django model or similar) providing context for the secret's parameters.
        """
        return secret.rendered_parameters(obj=obj).get("constant")


secrets_providers = [ConstantValueSecretsProvider]
