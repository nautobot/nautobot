from abc import ABC, abstractmethod

from jinja2.sandbox import unsafe

from nautobot.extras.registry import registry

from .exceptions import SecretError, SecretParametersError, SecretProviderError, SecretValueNotFoundError


class SecretsProvider(ABC):
    """Abstract base class for concrete providers of secret retrieval features."""

    def __repr__(self):
        return f"<{self.name}>"

    @property
    @abstractmethod
    def slug(self):
        """String uniquely identifying this class; will be used as a key to look up the class owning a given Secret."""

    @property
    def name(self):
        """Human-friendly name for this class, falling back to the slug if not overridden."""
        return self.slug

    @property
    @abstractmethod
    def ParametersForm(self):
        """Django Form class with inputs for describing the parameter(s) required for a Secret to use this Provider.

        The clean() method may be implemented to provide additional input validation.
        """

    @classmethod
    @abstractmethod
    @unsafe
    def get_value_for_secret(cls, secret, obj=None, **kwargs):
        """Retrieve the stored value described by the given Secret record.

        May raise a SecretError or one of its subclasses if an error occurs.

        Args:
            secret (nautobot.extras.models.Secret): DB entry describing the secret or family of secrets in question.
            obj (object): Django model instance or similar providing additional context for retrieving the secret.
        """

    get_value_for_secret.__func__.do_not_call_in_templates = True

    def __init_subclass__(cls, **kwargs):
        # Automatically apply protection against Django and Jinja2 template execution to child classes.
        if not getattr(cls.get_value_for_secret, "do_not_call_in_templates", False):  # Django
            cls.get_value_for_secret.__func__.do_not_call_in_templates = True
        if not getattr(cls.get_value_for_secret, "unsafe_callable", False):  # Jinja @unsafe decorator
            cls.get_value_for_secret.__func__.unsafe_callable = True

        super().__init_subclass__(**kwargs)


def register_secrets_provider(provider):
    """
    Register a SecretsProvider class for use by Nautobot.
    """
    if not issubclass(provider, SecretsProvider):
        raise TypeError(f"{provider} must be a subclass of extras.secrets.SecretsProvider")
    if provider.slug in registry["secrets_providers"]:
        raise KeyError(
            f'Cannot register {provider} as slug "{provider.slug}" is already registered '
            f"by {registry['secrets_providers'][provider.slug]}"
        )
    registry["secrets_providers"][provider.slug] = provider


__all__ = (
    "SecretError",
    "SecretParametersError",
    "SecretProviderError",
    "SecretValueNotFoundError",
    "SecretsProvider",
    "register_secrets_provider",
)
