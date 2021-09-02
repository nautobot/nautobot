from nautobot.extras.registry import registry

from .providers import SecretsProvider


def register_secrets_provider(provider):
    """
    Register a SecretsProvider class for use by Nautobot.
    """
    if not issubclass(provider, SecretsProvider):
        raise TypeError(f"{provider} must be a subclass of extras.secrets.SecretsProvider")
    if provider.slug in registry["secrets_providers"]:
        raise KeyError(
            f'Cannot register {provider} as slug "{provider.slug}" is already registered '
            f'by {registry["secrets_providers"][provider.slug]}'
        )
    registry["secrets_providers"][provider.slug] = provider
