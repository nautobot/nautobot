from nautobot.extras.secrets import SecretsProvider


class ConstantValueSecretsProvider(SecretsProvider):
    """
    Example of a plugin-provided SecretsProvider - this one just uses a user-specified constant value.

    Obviously this is insecure and not something you'd want to actually use!
    """

    slug = "constant-value"
    name = "constant value"

    @classmethod
    def get_value_for_secret(cls, secret):
        """
        Return the value defined in the Secret.parameters "constant" key.

        A more realistic SecretsProvider would make calls to external APIs, etc. to retrieve a secret from storage.
        """
        return secret.parameters.get("constant")


secrets_providers = [ConstantValueSecretsProvider]
