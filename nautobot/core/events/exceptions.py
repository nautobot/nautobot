class EventPublisherError(Exception):
    """Base exception for all event-publisher-related errors."""


class EventPublisherNotFound(EventPublisherError):
    """Raised when a specified event publisher module cannot be found."""


class EventPublisherImproperlyConfigured(EventPublisherError):
    """Raised when a event is not properly configured."""
