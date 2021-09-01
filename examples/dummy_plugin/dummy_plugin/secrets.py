from nautobot.extras.secrets import SecretProvider


class ConstantSecretProvider(SecretProvider):
    """
    Example of a plugin-provided SecretProvider - this one just uses a user-specified constant value.

    Obviously this is insecure and not something you'd want to actually use!
    """

    @classmethod
    def get_value_for_secret(cls, secret):
        """
        Return the value defined in the Secret.parameters "constant" key.

        A more realistic SecretProvider would make calls to external APIs, etc. to retrieve a secret from storage.
        """
        return secret.parameters.get("constant")
