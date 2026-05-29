"""Module providing for the publication of event notifications via mechanisms such as Redis, Kafka, syslog, etc."""

import fnmatch
import json
import logging

from django.utils.module_loading import import_string

from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.core.events.exceptions import (
    EventBrokerImproperlyConfigured,
    EventBrokerNotFound,
    EventConsumerImproperlyConfigured,
    EventConsumerNotFound,
)

from .base import EventBroker
from .consumer_base import ConsumedEvent, EventConsumer
from .redis_broker import RedisEventBroker
from .redis_consumer import RedisEventConsumer
from .syslog_broker import SyslogEventBroker

_EVENT_BROKERS = []

# Registry of configured EventConsumer instances and their deferred-lookup metadata.
# Each entry is a dict with the following keys (all values are JSON-friendly primitives
# except ``consumer``, which is the live ``EventConsumer`` instance):
#
#     {
#         "name": str,                    # operator-supplied name for the consumer
#         "consumer": EventConsumer,      # the instantiated EventConsumer
#         "secrets_group_name": str|None, # name of a SecretsGroup; resolved at runtime
#         "user_access_type": str,        # SecretsGroupAccessTypeChoices value
#         "user_secret_type": str,        # SecretsGroupSecretTypeChoices value
#         "job_bindings": [
#             {
#                 "topic_pattern": str,
#                 "job_class_path": str,  # dotted path; resolved at runtime
#                 "queue": str|None,
#             },
#             ...
#         ],
#     }
#
# IMPORTANT: This registry is populated at settings-preprocess time (before
# ``django.setup()``) so it MUST NOT contain references to Django model instances.
# All model lookups (``SecretsGroup``, ``User``, ``Job``) are deferred to the
# ``run_event_consumers`` management command, which runs after Django initialization.
_EVENT_CONSUMERS = []


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


def _normalize_job_class_path(job_class):
    """Normalize a Job reference to a dotted-path string.

    Accepts either a dotted-path string or a class object. Storing strings keeps the
    registry free of class references and avoids any ORM/import side effects at
    settings-preprocess time. The actual ``Job`` model row is resolved later by the
    ``run_event_consumers`` management command.
    """
    if isinstance(job_class, str):
        return job_class
    module = getattr(job_class, "__module__", None)
    name = getattr(job_class, "__name__", None)
    if not module or not name:
        raise EventConsumerImproperlyConfigured(
            f"Cannot derive dotted path for job_class {job_class!r}; pass a class or a 'module.ClassName' string"
        )
    return f"{module}.{name}"


def _find_consumer_entry(consumer_name):
    for entry in _EVENT_CONSUMERS:
        if entry["name"] == consumer_name:
            return entry
    return None


def register_event_consumer(
    consumer,
    *,
    name,
    secrets_group_name=None,
    user_access_type=None,
    user_secret_type=None,
    job_bindings=None,
):
    """Register an ``EventConsumer`` instance for use by Nautobot.

    Args:
        consumer (EventConsumer): The initialized/configured ``EventConsumer`` instance.
        name (str): Operator-supplied identifier for the consumer. Must be unique among
            registered consumers; used by ``register_event_consumer_job(consumer_name=...)``
            and by the management command for logging.
        secrets_group_name (str, optional): Name of a ``SecretsGroup`` from which to
            resolve the Job-executing user at command-runtime. Looked up via
            ``SecretsGroup.objects.get(name=...)`` later (NOT at registration time).
        user_access_type (str, optional): ``SecretsGroupAccessTypeChoices`` value used
            to retrieve the username from the SecretsGroup. Defaults to ``"Generic"``.
        user_secret_type (str, optional): ``SecretsGroupSecretTypeChoices`` value used
            to retrieve the username from the SecretsGroup. Defaults to ``"username"``.
        job_bindings (list, optional): Iterable of binding dicts. Each dict must have
            ``topic_pattern`` (str), ``job_class`` (str or class), and optional ``queue``.

    Stores only strings and Python primitives (plus the ``EventConsumer`` instance
    itself). Performs no ORM access — safe to call during settings preprocessing.
    """
    if not isinstance(consumer, EventConsumer):
        raise EventConsumerImproperlyConfigured(f"{name}: object {consumer!r} is not an EventConsumer instance")
    if _find_consumer_entry(name) is not None:
        logger.warning("Tried to register event consumer %s but the name was already registered", name)
        return

    normalized_bindings = []
    for binding in job_bindings or []:
        normalized_bindings.append(
            {
                "topic_pattern": binding["topic_pattern"],
                "job_class_path": _normalize_job_class_path(binding["job_class"]),
                "queue": binding.get("queue"),
            }
        )

    entry = {
        "name": name,
        "consumer": consumer,
        "secrets_group_name": secrets_group_name,
        "user_access_type": user_access_type or "Generic",
        "user_secret_type": user_secret_type or "username",
        "job_bindings": normalized_bindings,
    }
    _EVENT_CONSUMERS.append(entry)
    logger.debug("Registered %s as an event consumer (name=%s)", consumer, name)


def deregister_event_consumer(consumer):
    """Deregister a previously registered ``EventConsumer`` instance."""
    for index, entry in enumerate(_EVENT_CONSUMERS):
        if entry["consumer"] is consumer:
            del _EVENT_CONSUMERS[index]
            logger.debug("Deregistered event consumer %s", consumer)
            return
    logger.warning("Tried to deregister event consumer %s but it wasn't previously registered", consumer)


def register_event_consumer_job(*, consumer_name, topic_pattern, job_class, queue=None):
    """Append a topic-to-Job binding to an already-registered consumer.

    Args:
        consumer_name (str): The ``name`` passed to ``register_event_consumer``.
        topic_pattern (str): Glob-style topic pattern (e.g., ``"nautobot.create.dcim.*"``).
        job_class (str or type): Dotted path or class object of an ``EventConsumerJob``
            subclass. The class itself is not resolved here — only its dotted path is
            stored. Resolution happens at management-command runtime.
        queue (str, optional): Celery queue name override for this binding.

    Raises:
        EventConsumerImproperlyConfigured: If ``consumer_name`` is not registered, or if
            ``job_class`` cannot be normalized to a dotted-path string.
    """
    entry = _find_consumer_entry(consumer_name)
    if entry is None:
        raise EventConsumerImproperlyConfigured(f"No event consumer registered with name {consumer_name!r}")
    entry["job_bindings"].append(
        {
            "topic_pattern": topic_pattern,
            "job_class_path": _normalize_job_class_path(job_class),
            "queue": queue,
        }
    )


def load_event_consumers(event_consumer_configs):
    """Instantiate and register event consumers from a settings-style configuration dict.

    Mirrors ``load_event_brokers``. Expected to be called from
    ``nautobot.core.cli._preprocess_settings`` *before* ``django.setup()``. This function
    is **forbidden** from performing any ORM query — the Django app registry is not yet
    ready and any model access would raise ``AppRegistryNotReady`` or behave unsafely.

    Args:
        event_consumer_configs (dict): Mapping of consumer-name to consumer config dict.
            Each value must contain ``CLASS`` (dotted path to an ``EventConsumer``
            subclass) and may contain ``OPTIONS`` (kwargs), ``TOPICS`` (``INCLUDE`` /
            ``EXCLUDE`` lists), ``PASSWORD`` (str, passed to the consumer as a
            ``password`` kwarg for authenticating the broker connection),
            ``SECRETS_GROUP`` (str), ``USER_ACCESS_TYPE`` (str),
            ``USER_SECRET_TYPE`` (str), and ``JOB_BINDINGS`` (list of binding dicts).
    """
    for consumer_name, consumer_cfg in event_consumer_configs.items():
        options = dict(consumer_cfg.get("OPTIONS", {}) or {})
        topics = consumer_cfg.get("TOPICS", {})
        if not isinstance(topics, dict):
            raise EventConsumerImproperlyConfigured(
                f"{consumer_name} Malformed Event Consumer Settings: "
                f"Expected `TOPICS` to be a 'dict', instead a '{type(topics).__name__}' was provided"
            )
        include_topics = topics.get("INCLUDE")
        if include_topics and not isinstance(include_topics, (list, tuple)):
            raise EventConsumerImproperlyConfigured(
                f"{consumer_name} Malformed Event Consumer Settings: "
                f"Expected `INCLUDE` to be a 'list' or 'tuple', "
                f"instead a '{type(include_topics).__name__}' was provided"
            )
        exclude_topics = topics.get("EXCLUDE", [])
        if exclude_topics and not isinstance(exclude_topics, (list, tuple)):
            raise EventConsumerImproperlyConfigured(
                f"{consumer_name} Malformed Event Consumer Settings: "
                f"Expected `EXCLUDE` to be a 'list' or 'tuple', "
                f"instead a '{type(exclude_topics).__name__}' was provided"
            )
        options.update({"include_topics": include_topics, "exclude_topics": exclude_topics})

        password = consumer_cfg.get("PASSWORD")
        if password is not None:
            options.setdefault("password", password)

        job_bindings_cfg = consumer_cfg.get("JOB_BINDINGS", [])
        if not isinstance(job_bindings_cfg, (list, tuple)):
            raise EventConsumerImproperlyConfigured(
                f"{consumer_name} Malformed Event Consumer Settings: "
                f"Expected `JOB_BINDINGS` to be a 'list' or 'tuple', "
                f"instead a '{type(job_bindings_cfg).__name__}' was provided"
            )
        for binding in job_bindings_cfg:
            if not isinstance(binding, dict) or "topic_pattern" not in binding or "job_class" not in binding:
                raise EventConsumerImproperlyConfigured(
                    f"{consumer_name} Malformed Event Consumer Settings: "
                    f"each JOB_BINDINGS entry must be a dict with 'topic_pattern' and 'job_class' keys; got {binding!r}"
                )

        try:
            consumer_class = import_string(consumer_cfg["CLASS"])
        except ImportError as err:
            raise EventConsumerNotFound(f"Unable to import Event Consumer {consumer_name}.") from err

        if not issubclass(consumer_class, EventConsumer):
            raise EventConsumerImproperlyConfigured(
                f"{consumer_name} Malformed Event Consumer Settings: Consumer provided is not an EventConsumer"
            )
        consumer = consumer_class(**options)

        register_event_consumer(
            consumer,
            name=consumer_name,
            secrets_group_name=consumer_cfg.get("SECRETS_GROUP"),
            user_access_type=consumer_cfg.get("USER_ACCESS_TYPE"),
            user_secret_type=consumer_cfg.get("USER_SECRET_TYPE"),
            job_bindings=job_bindings_cfg,
        )


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


def __getattr__(name):
    """Lazy access to ``EventConsumerJob``.

    ``nautobot.extras.jobs`` imports ``publish_event`` from this module, so eagerly
    importing ``EventConsumerJob`` (which subclasses ``Job``) here would create a
    circular dependency. Deferring the import via ``__getattr__`` lets callers write
    ``from nautobot.core.events import EventConsumerJob`` while the Job framework is
    only loaded the first time someone actually references it.
    """
    if name == "EventConsumerJob":
        # Intentional lazy import — see docstring above for why this can't live at module top.
        from .consumer_job import EventConsumerJob

        return EventConsumerJob
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# pylint: disable=undefined-all-variable
# ``EventConsumerJob`` is provided via the module-level ``__getattr__`` above (PEP 562)
# to avoid a circular import with ``nautobot.extras.jobs``. Pylint can't see through
# ``__getattr__`` statically, hence the disable.
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
