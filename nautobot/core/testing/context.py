from django.test.utils import TestContextDecorator

from nautobot.core.events import (
    _EVENT_BROKERS,
    _EVENT_CONSUMERS,
    deregister_event_broker,
    deregister_event_consumer,
    load_event_brokers,
    load_event_consumers,
)


class load_event_broker_override_settings(TestContextDecorator):
    def __init__(self, **kwargs) -> None:
        self.options = kwargs
        super().__init__()

    def enable(self):
        """Registered event brokers"""
        load_event_brokers(self.options["EVENT_BROKERS"])

    def disable(self):
        """Clear all registered event brokers"""
        for event_broker in _EVENT_BROKERS:
            deregister_event_broker(event_broker)


class load_event_consumer_override_settings(TestContextDecorator):
    """Test decorator that loads ``EVENT_CONSUMERS`` from kwargs and tears them down after.

    Parallel to ``load_event_broker_override_settings``. Use to register event consumers
    for the duration of a single test method or class.
    """

    def __init__(self, **kwargs) -> None:
        self.options = kwargs
        super().__init__()

    def enable(self):
        """Register the event consumers described by ``EVENT_CONSUMERS``."""
        load_event_consumers(self.options["EVENT_CONSUMERS"])

    def disable(self):
        """Clear all registered event consumers."""
        for entry in list(_EVENT_CONSUMERS):
            deregister_event_consumer(entry["consumer"])
