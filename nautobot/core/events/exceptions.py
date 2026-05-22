class EventBrokerError(Exception):
    """Base exception for all event-broker-related errors."""


class EventBrokerNotFound(EventBrokerError):
    """Raised when a specified event broker module cannot be found."""


class EventBrokerImproperlyConfigured(EventBrokerError):
    """Raised when a event is not properly configured."""


class EventConsumerError(Exception):
    """Base exception for all event-consumer-related errors."""


class EventConsumerNotFound(EventConsumerError):
    """Raised when a specified event consumer module cannot be found."""


class EventConsumerImproperlyConfigured(EventConsumerError):
    """Raised when an event consumer is not properly configured."""
