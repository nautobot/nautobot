"""Exceptions for Nautobot apps."""

from nautobot.core.api.exceptions import SerializerNotFound, ServiceUnavailable
from nautobot.core.exceptions import (
    AbortTransaction,
    CeleryWorkerNotRunningException,
    FilterSetFieldNotFound,
)
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
    "SecretError",
    "SecretParametersError",
    "SecretProviderError",
    "SecretValueNotFoundError",
    "SerializerNotFound",
    "ServiceUnavailable",
)
