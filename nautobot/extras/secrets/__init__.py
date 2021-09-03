from abc import ABC, abstractmethod, abstractproperty

from nautobot.extras.registry import registry


class SecretsProvider(ABC):
    """Abstract base class for concrete providers of secret retrieval features."""

    @abstractproperty
    def slug(self):
        """String uniquely identifying this class; will be used as a key to look up the class owning a given Secret."""

    @property
    def name(self):
        """Human-friendly name for this class, falling back to the slug if not overridden."""
        return self.slug

    @abstractproperty
    def ParametersForm(self):
        """Django Form class with inputs for describing the parameter(s) required for a Secret to use this Provider."""

    @classmethod
    @abstractmethod
    def get_value_for_secret(cls, secret):
        """Retrieve the stored value described by the given Secret record."""


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


__all__ = (
    "SecretsProvider",
    "register_secrets_provider",
)
