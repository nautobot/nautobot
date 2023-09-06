# Implementing Secrets Providers

+++ 1.2.0

An app can define and register additional providers (sources) for [Secrets](../../../../user-guide/platform-functionality/secret.md), allowing Nautobot to retrieve secret values from additional systems or data sources. By default, Nautobot looks for an iterable named `secrets_providers` within a `secrets.py` file. (This can be overridden by setting `secrets_providers` to a custom value on the app's `NautobotAppConfig`.)

To define a new `SecretsProvider` subclass, we must specify the following:

* A unique `slug` string identifying this provider
* A human-readable `name` string (optional; the `slug` will be used if this is not specified)
* A Django form for entering the parameters required by this provider, as an inner class named `ParametersForm`
* An implementation of the `get_value_for_secret()` API to actually retrieve the value of a given secret

For a simple (insecure!) example, we could define a "constant-value" provider that simply stores a constant value in Nautobot itself and returns this value on demand.

!!! warning
    This is an intentionally simplistic example and should not be used in practice! Sensitive secret data should never be stored directly in Nautobot's database itself.

```python
# secrets.py
from django import forms
from nautobot.apps.secrets import SecretsProvider
from nautobot.utilities.forms import BootstrapMixin


class ConstantValueSecretsProvider(SecretsProvider):
    """
    Example SecretsProvider - this one just returns a user-specified constant value.

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
            help_text="Constant secret value. <strong>DO NOT USE FOR REAL DATA</strong>"
        )

    @classmethod
    def get_value_for_secret(cls, secret, obj=None, **kwargs):
        """
        Return the value defined in the Secret.parameters "constant" key.

        A more realistic SecretsProvider would make calls to external APIs, etc.,
        to retrieve a secret from another system as desired.

        Args:
            secret (nautobot.extras.models.Secret): The secret whose value should be retrieved.
            obj (object): The object (Django model or similar) providing context for the secret's
                parameters.
        """
        return secret.rendered_parameters(obj=obj).get("constant")


secrets_providers = [ConstantValueSecretsProvider]
```

After installing and enabling your app, you should now be able to navigate to `Secrets > Secrets` and create a new Secret, at which point `"constant-value"` should now be available as a new secrets provider to use.
