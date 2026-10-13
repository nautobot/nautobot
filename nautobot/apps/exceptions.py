"""Exceptions for Nautobot apps."""

from nautobot.core.api.exceptions import SerializerNotFound, ServiceUnavailable
from nautobot.core.exceptions import (
    AbortTransaction,
    CeleryWorkerNotRunningException,
    FilterSetFieldNotFound,
    SensitiveFieldError,
)
from nautobot.core.utils.regex import InvalidRegexError, RegexTimeoutError
from nautobot.extras.secrets.exceptions import (
    SecretError,
    SecretParametersError,
    SecretProviderError,
    SecretValueNotFoundError,
)


class ConfigurationError(Exception):
    """Deprecated - no longer used in Nautobot core."""


__all__ = (
    "AbortTransaction",
    "CeleryWorkerNotRunningException",
    "ConfigurationError",
    "FilterSetFieldNotFound",
    "InvalidRegexError",
    "RegexTimeoutError",
    "SecretError",
    "SecretParametersError",
    "SecretProviderError",
    "SecretValueNotFoundError",
    "SensitiveFieldError",
    "SerializerNotFound",
    "ServiceUnavailable",
)
