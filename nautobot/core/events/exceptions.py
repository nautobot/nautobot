class EventBrokerError(Exception):
    """Base exception for all event-broker-related errors."""


class EventBrokerNotFound(EventBrokerError):
    """Raised when a specified event broker module cannot be found."""


class EventBrokerImproperlyConfigured(EventBrokerError):
    """Raised when a event is not properly configured."""
