"""Module providing for the publication of event notifications via mechanisms such as Redis, Kafka, syslog, etc."""

import fnmatch
import json
import logging

from django.utils.module_loading import import_string

from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.core.events.exceptions import EventBrokerImproperlyConfigured, EventBrokerNotFound

from .base import EventBroker
from .redis_broker import RedisEventBroker
from .syslog_broker import SyslogEventBroker

_EVENT_BROKERS = []


logger = logging.getLogger(__name__)


def load_event_brokers(event_broker_configs):
    """Process plugins and log errors if they can't be loaded."""
    for broker_name, broker in event_broker_configs.items():
        options = broker.get("OPTIONS", {})
        topics = broker.get("TOPICS", {})
        if not isinstance(topics, dict):
            raise EventBrokerImproperlyConfigured(
                f"{broker_name} Malformed Event Broker Settings: Expected `TOPICS` to be a 'dict', instead a '{type(topics).__name__}' was provided"
            )
        include_topics = topics.get("INCLUDE")
        if include_topics and not isinstance(include_topics, (list, tuple)):
            raise EventBrokerImproperlyConfigured(
                f"{broker_name} Malformed Event Broker Settings: Expected `INCLUDE` to be a 'list' or 'tuple', instead a '{type(include_topics).__name__}' was provided"
            )
        exclude_topics = topics.get("EXCLUDE", [])
        if exclude_topics and not isinstance(exclude_topics, (list, tuple)):
            raise EventBrokerImproperlyConfigured(
                f"{broker_name} Malformed Event Broker Settings: Expected `EXCLUDE` to be a 'list' or 'tuple', instead a '{type(exclude_topics).__name__}' was provided"
            )
        options.update({"include_topics": include_topics, "exclude_topics": exclude_topics})

        try:
            event_broker_class = import_string(broker["CLASS"])
            if not issubclass(event_broker_class, EventBroker):
                raise EventBrokerImproperlyConfigured(
                    f"{broker_name} Malformed Event Broker Settings: Broker provided is not an EventBroker"
                )
            event_broker = event_broker_class(**options)
            register_event_broker(event_broker)
        except ImportError as err:
            raise EventBrokerNotFound(f"Unable to import Event Broker {broker_name}.") from err


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


def is_topic_match(topic, patterns):
    return any(fnmatch.fnmatch(topic, pattern) for pattern in patterns)


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
        exclude_topics = event_broker.exclude_topics
        include_topics = event_broker.include_topics
        if is_topic_match(topic, include_topics) and not is_topic_match(topic, exclude_topics):
            serialized_payload = json.dumps(payload, cls=NautobotKombuJSONEncoder)
            event_broker.publish(topic=topic, payload=serialized_payload)


__all__ = (
    "EventBroker",
    "RedisEventBroker",
    "SyslogEventBroker",
    "deregister_event_broker",
    "publish_event",
    "register_event_broker",
)
