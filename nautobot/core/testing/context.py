from django.test.utils import TestContextDecorator

from nautobot.core.events import _EVENT_BROKERS, deregister_event_broker, load_event_brokers


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
