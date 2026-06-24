"""APIs for Nautobot event-notification subsystem."""

# ``EventConsumerJob`` is exposed via a module-level ``__getattr__`` in
# ``nautobot.core.events`` (PEP 562 lazy import to avoid a circular import with
# ``nautobot.extras.jobs``). Pylint can't see through ``__getattr__`` statically.
# pylint: disable=no-name-in-module
from nautobot.core.events import (
    ConsumedEvent,
    deregister_event_broker,
    deregister_event_consumer,
    EventBroker,
    EventConsumer,
    EventConsumerJob,
    load_event_consumers,
    publish_event,
    RedisEventBroker,
    RedisEventConsumer,
    register_event_broker,
    register_event_consumer,
    register_event_consumer_job,
    SyslogEventBroker,
)

# pylint: enable=no-name-in-module

__all__ = (
    "ConsumedEvent",
    "EventBroker",
    "EventConsumer",
    "EventConsumerJob",
    "RedisEventBroker",
    "RedisEventConsumer",
    "SyslogEventBroker",
    "deregister_event_broker",
    "deregister_event_consumer",
    "load_event_consumers",
    "publish_event",
    "register_event_broker",
    "register_event_consumer",
    "register_event_consumer_job",
)
