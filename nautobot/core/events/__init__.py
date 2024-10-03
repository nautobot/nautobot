"""Module providing for the publication of event notifications via mechanisms such as Redis, Kafka, syslog, etc."""

import logging

from .base import EventBroker
from .redis_broker import RedisEventBroker
from .syslog_broker import SyslogEventBroker

_EVENT_BROKERS = []


logger = logging.getLogger(__name__)


def register_event_broker(event_broker):
    """
    Register an `EventBroker` instance for use by Nautobot.

    The `publish_event()` API will publish events to each registered broker.
    The expectation/intent here, at least initially, is that a given deployment will instantiate zero or more
    EventBrokers, then call `register_event_broker()` for each one, as part of Nautobot initial startup.

    Args:
        event_broker (EventBroker): The initialized/configured EventBroker instance to register.
    """
    if event_broker not in _EVENT_BROKERS:
        _EVENT_BROKERS.append(event_broker)
        logger.debug("Registered %s as an event broker", event_broker)
    else:
        logger.warning("Tried to register event broker %s but it was already registered", event_broker)


def deregister_event_broker(event_broker):
    """
    Deregister a previously registered `EventBroker` instance so that it no longer receives published events.
    """
    try:
        _EVENT_BROKERS.remove(event_broker)
        logger.debug("Deregistered event broker %s", event_broker)
    except ValueError:
        logger.warning("Tried to deregister event broker %s but it wasn't previously registered", event_broker)


def publish_event(*, topic, payload):
    """Publish the given event payload to the given topic via all registered `EventBroker` instances.

    Args:
        topic (str): Topic identifier.
            Convention is to use snake_case and use periods to delineate related groups of topics,
            similar to Python logger naming. For example, you might use `nautobot.create.dcim.device`,
            `nautobot.update.dcim.device`, `nautobot.delete.dcim.device`, `nautobot.create.dcim.interface`,
            `nautobot.create.ipam.ipaddress`, etc.
        payload (dict): JSON-serializable structured data to publish.
            While not all EventBrokers may actually use JSON as their data format, it makes for a reasonable
            lowest common denominator for serializability.
    """
    for event_broker in _EVENT_BROKERS:
        event_broker.publish(topic=topic, payload=payload)


__all__ = (
    "deregister_event_broker",
    "EventBroker",
    "publish_event",
    "RedisEventBroker",
    "register_event_broker",
    "SyslogEventBroker",
)
