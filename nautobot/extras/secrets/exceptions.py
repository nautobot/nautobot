"""Exception classes specific to secrets."""


class SecretError(Exception):
    """General purpose exception class for failures raised when secret value access fails."""

    def __init__(self, secret, provider_class, message, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self.secret = secret
        self.provider_class = provider_class
        self.message = message

    def __str__(self):
        return (
            f"{self.__class__.__name__}: "
            f'Secret "{self.secret}" (provider "{self.provider_class.__name__}"): {self.message}'
        )


class SecretParametersError(SecretError):
    """Exception raised when a Secret record's parameters are incorrectly specified.

    Normally this should be caught during input validation of the Secret record, but in the case of direct
    ORM access bypassing the usual clean() functionality, it's possible to create a mis-defined Secret which
    would trigger this exception upon access.
    """


class SecretValueNotFoundError(SecretError, KeyError):
    """Exception raised when a secrets provider is operating normally but a specific requested secret is not found."""


class SecretProviderError(SecretError):
    """General purpose exception class for failures that indicate that a secrets provider is not working correctly."""
