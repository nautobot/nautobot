"""Test cases for the event notification APIs."""

from collections import defaultdict
import json

from django.conf import settings
import redis

from nautobot.core.events import (
    deregister_event_broker,
    EventBroker,
    load_event_brokers,
    publish_event,
    register_event_broker,
)
from nautobot.core.events.exceptions import EventPublisherImproperlyConfigured, EventPublisherNotFound
from nautobot.core.testing import TestCase
from nautobot.core.testing.context import load_event_broker_override_settings


class TestEventBroker(EventBroker):
    def __init__(self, **kwargs):
        self.events = defaultdict(list)
        super().__init__(**kwargs)

    def publish(self, *, topic, payload):
        self.events[topic].append(payload)


class EventNotificationTest(TestCase):
    def test_publish_events_to_broker(self):
        event_broker = TestEventBroker()
        event_broker_2 = TestEventBroker()

        # An event broker doesn't receive events if it isn't registered
        publish_event(topic="nautobot.test.some_event", payload={"x": 0})
        self.assertNotIn("nautobot.test.some_event", event_broker.events)
        self.assertNotIn("nautobot.test.some_event", event_broker_2.events)

        register_event_broker(event_broker)
        # Events are not retroactively published by Nautobot
        self.assertNotIn("nautobot.test.some_event", event_broker.events)
        self.assertNotIn("nautobot.test.some_event", event_broker_2.events)

        # Duplicate registration is a no-op
        register_event_broker(event_broker)

        # New events are published to the registered broker only
        try:
            publish_event(topic="nautobot.test.event", payload={"a": 1})
            self.assertIn("nautobot.test.event", event_broker.events)
            self.assertEqual(len(event_broker.events["nautobot.test.event"]), 1)
            self.assertEqual(event_broker.events["nautobot.test.event"][0], {"a": 1})
            self.assertNotIn("nautobot.test.event", event_broker_2.events)

            # New events can be published to multiple brokers
            register_event_broker(event_broker_2)
            try:
                publish_event(topic="nautobot.test.event", payload={"a": 2})
                self.assertIn("nautobot.test.event", event_broker.events)
                self.assertEqual(len(event_broker.events["nautobot.test.event"]), 2)
                self.assertEqual(event_broker.events["nautobot.test.event"][1], {"a": 2})
                self.assertIn("nautobot.test.event", event_broker_2.events)
                self.assertEqual(len(event_broker_2.events["nautobot.test.event"]), 1)
                self.assertEqual(event_broker_2.events["nautobot.test.event"][0], {"a": 2})
            finally:
                deregister_event_broker(event_broker_2)

            # After deregistering one broker, it stops receiving events but the other remains registered and active
            publish_event(topic="nautobot.test.another_event", payload={"b": 1})
            self.assertIn("nautobot.test.another_event", event_broker.events)
            self.assertEqual(len(event_broker.events["nautobot.test.another_event"]), 1)
            self.assertEqual(event_broker.events["nautobot.test.another_event"][0], {"b": 1})
            self.assertNotIn("nautobot.test.another_event", event_broker_2.events)

        finally:
            deregister_event_broker(event_broker)

        # After deregistering both brokers, we can still publish events, but no one is listening
        publish_event(topic="nautobot.test.yet_another_event", payload={"b": 2})
        self.assertNotIn("nautobot.test.yet_another_event", event_broker.events)
        self.assertNotIn("nautobot.test.yet_another_event", event_broker_2.events)

        # Duplicate deregistration is a no-op
        deregister_event_broker(event_broker)
        deregister_event_broker(event_broker_2)

    @load_event_broker_override_settings(
        NAUTOBOT_EVENT_BROKERS={
            "SyslogEventBroker": {
                "CLASS": "nautobot.core.events.SyslogEventBroker",
                "TOPICS": {
                    "INCLUDE": ["nautobot.test.*"],
                    "EXCLUDE": ["*.no-publish*"],
                },
            }
        }
    )
    def test_publish_events_to_syslog(self):
        with self.assertLogs("nautobot.events.nautobot.test.event") as cm:
            publish_event(topic="nautobot.test.event", payload={"a": 1})
            publish_event(topic="nautobot.test.no-publish.event", payload={"a": 1})
        # This test assets that only `nautobot.test.event` topic was published
        self.assertEqual(cm.output, ["INFO:nautobot.events.nautobot.test.event:" + json.dumps({"a": 1}, indent=4)])

    @load_event_broker_override_settings(
        NAUTOBOT_EVENT_BROKERS={
            "RedisEventBroker": {
                "CLASS": "nautobot.core.events.RedisEventBroker",
                "OPTIONS": {"url": settings.CACHES["default"]["LOCATION"]},
            }
        }
    )
    def test_publish_events_to_redis(self):
        url = settings.CACHES["default"]["LOCATION"]
        connection = redis.StrictRedis.from_url(url, decode_responses=True)
        sub = connection.pubsub()
        sub.psubscribe("nautobot.*")
        self.assertEqual(
            sub.get_message(timeout=5.0),
            {"type": "psubscribe", "pattern": None, "channel": "nautobot.*", "data": 1},
        )
        publish_event(topic="nautobot.test.event", payload={"b": 2})
        self.assertEqual(
            sub.get_message(timeout=5.0),
            {"type": "pmessage", "pattern": "nautobot.*", "channel": "nautobot.test.event", "data": '{"b": 2}'},
        )

    def test_invalid_event_broker_config(self):
        with self.assertRaises(EventPublisherNotFound) as err:
            broker_config = {
                "TestEventBroker": {
                    "CLASS": "nautobot.core.tests.invalid_path.TestEventBroker",
                }
            }
            load_event_brokers(broker_config)
        self.assertEqual(
            str(err.exception),
            "Unable to import event publisher TestEventBroker: Module nautobot.core.tests.invalid_path not found",
        )

        with self.assertRaises(EventPublisherNotFound) as err:
            broker_config = {
                "TestEventBroker": {
                    "CLASS": "nautobot.core.tests.test_events.InvalidBroker",
                }
            }
            load_event_brokers(broker_config)
        self.assertEqual(
            str(err.exception),
            "Unable to import event publisher TestEventBroker: TestEventBroker not found in module nautobot.core.tests.test_events",
        )

        with self.assertRaises(EventPublisherImproperlyConfigured) as err:
            broker_config = {
                "TestEventBroker": {"CLASS": "nautobot.core.tests.test_events.TestEventBroker", "TOPICS": []}
            }
            load_event_brokers(broker_config)
        self.assertEqual(
            str(err.exception),
            "Malformed Event Publisher Settings: Expected `TOPICS` to be a 'dict', instead a 'list' was provided",
        )

        with self.assertRaises(EventPublisherImproperlyConfigured) as err:
            broker_config = {
                "TestEventBroker": {
                    "CLASS": "nautobot.core.tests.test_events.TestEventBroker",
                    "TOPICS": {
                        "INCLUDE": "nautobot.test.*",
                    },
                }
            }
            load_event_brokers(broker_config)
        self.assertEqual(
            str(err.exception),
            "Malformed Event Publisher Settings: Expected `INCLUDE` to be a 'list', instead a 'str' was provided",
        )

        with self.assertRaises(EventPublisherImproperlyConfigured) as err:
            broker_config = {
                "TestEventBroker": {
                    "CLASS": "nautobot.core.tests.test_events.TestEventBroker",
                    "TOPICS": {
                        "EXCLUDE": "nautobot.test.*",
                    },
                }
            }
            load_event_brokers(broker_config)
        self.assertEqual(
            str(err.exception),
            "Malformed Event Publisher Settings: Expected `EXCLUDE` to be a 'list', instead a 'str' was provided",
        )
