from .providers import SecretsProvider, EnvironmentVariableSecretsProvider, TextFileSecretsProvider
from .registry import register_secrets_provider


__all__ = (
    "SecretsProvider",
    "register_secrets_provider",
)

register_secrets_provider(EnvironmentVariableSecretsProvider)
register_secrets_provider(TextFileSecretsProvider)
