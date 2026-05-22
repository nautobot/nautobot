"""``RedisEventConsumer`` — Redis Pub/Sub consume-side counterpart to ``RedisEventBroker``.

Redis Pub/Sub is **fire-and-forget**: subscribers must be running to receive messages, and
there is no replay or persistence. Operators needing durable delivery should use Redis
Streams (out of scope here) or a non-Redis broker shipped by an app.

A typical pair on the publisher side looks like this::

    EVENT_BROKERS = {
        "RedisBroker": {
            "CLASS": "nautobot.core.events.RedisEventBroker",
            "OPTIONS": {"url": "redis://localhost:6379/0"},
        },
    }

and the consumer side ::

    EVENT_CONSUMERS = {
        "RedisConsumer": {
            "CLASS": "nautobot.core.events.RedisEventConsumer",
            "OPTIONS": {"url": "redis://localhost:6379/0"},
            "TOPICS": {"INCLUDE": ["nautobot.create.dcim.device"]},
            "SECRETS_GROUP": "event-consumer-creds",
            "JOB_BINDINGS": [
                {
                    "topic_pattern": "nautobot.create.dcim.device",
                    "job_class": "my_app.jobs.LogDeviceCreated",
                },
            ],
        },
    }
"""

import json
import logging
import threading

import redis

from .consumer_base import ConsumedEvent, EventConsumer

logger = logging.getLogger(__name__)

# Polling interval (seconds) for ``pubsub.get_message``. Bounded so ``close()`` is
# responsive while still avoiding a tight loop when no messages are flowing.
_READ_POLL_TIMEOUT = 1.0


class RedisEventConsumer(EventConsumer):
    """``EventConsumer`` that subscribes to Redis Pub/Sub channels.

    Uses ``PSUBSCRIBE``, which natively supports glob patterns — the framework's
    fnmatch-style ``include_topics`` and ``exclude_topics`` map cleanly onto Redis
    channel patterns.
    """

    def __init__(self, *args, url, **kwargs):
        """Initialize the consumer.

        Args:
            url (str): The Redis URL to connect to (e.g., ``redis://host:6379/0``).
        """
        self.url = url
        self.connection = redis.StrictRedis.from_url(self.url, decode_responses=True)
        self.pubsub = self.connection.pubsub()
        self._shutdown = threading.Event()
        super().__init__(*args, **kwargs)

    def subscribe(self, topics):
        """Subscribe to the given list of Redis channel patterns via ``PSUBSCRIBE``."""
        if not topics:
            return
        self.pubsub.psubscribe(*topics)
        logger.debug("RedisEventConsumer subscribed to %s", topics)

    def read(self):
        """Yield each Redis ``pmessage`` as a ``ConsumedEvent`` until ``close()`` is called."""
        while not self._shutdown.is_set():
            msg = self.pubsub.get_message(timeout=_READ_POLL_TIMEOUT)
            if msg is None:
                continue
            if msg.get("type") != "pmessage":
                # Skip 'subscribe' / 'psubscribe' confirmation messages
                continue
            try:
                payload = json.loads(msg["data"])
            except (TypeError, ValueError):
                logger.warning(
                    "RedisEventConsumer received a non-JSON message on channel %s; skipping",
                    msg.get("channel"),
                )
                continue
            yield ConsumedEvent(
                topic=msg["channel"],
                payload=payload if isinstance(payload, dict) else {"_raw": payload},
                broker_ref=msg,
            )

    def ack(self, event):
        """No-op. Redis Pub/Sub is fire-and-forget and has no ack concept."""

    def nack(self, event, requeue=True):
        """No-op. Redis Pub/Sub cannot redeliver; ``requeue`` is ignored."""

    def close(self):
        """Stop the read loop and tear down the pubsub/connection."""
        self._shutdown.set()
        try:
            self.pubsub.close()
        except Exception:  # pylint: disable=broad-except
            logger.exception("RedisEventConsumer error closing pubsub")
        try:
            self.connection.close()
        except Exception:  # pylint: disable=broad-except
            logger.exception("RedisEventConsumer error closing connection")
