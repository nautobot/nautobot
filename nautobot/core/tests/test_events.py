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
from nautobot.core.events.exceptions import EventBrokerImproperlyConfigured, EventBrokerNotFound
from nautobot.core.testing import TestCase
from nautobot.core.testing.context import load_event_broker_override_settings
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.context_managers import web_request_context
from nautobot.extras.models import ObjectChange, Status


class TestEventBroker(EventBroker):
    def __init__(self, **kwargs):
        self.events = defaultdict(list)
        super().__init__(**kwargs)

    def publish(self, *, topic, payload):
        self.events[topic].append(payload)


class InvalidTestEventBroker:
    """Broker that do not inherit from EventBroker"""

    def __init__(self):
        self.events = defaultdict(list)

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
            self.assertEqual(event_broker.events["nautobot.test.event"][0], json.dumps({"a": 1}))
            self.assertNotIn("nautobot.test.event", event_broker_2.events)

            # New events can be published to multiple brokers
            register_event_broker(event_broker_2)
            try:
                publish_event(topic="nautobot.test.event", payload={"a": 2})
                self.assertIn("nautobot.test.event", event_broker.events)
                self.assertEqual(len(event_broker.events["nautobot.test.event"]), 2)
                self.assertEqual(event_broker.events["nautobot.test.event"][1], json.dumps({"a": 2}))
                self.assertIn("nautobot.test.event", event_broker_2.events)
                self.assertEqual(len(event_broker_2.events["nautobot.test.event"]), 1)
                self.assertEqual(event_broker_2.events["nautobot.test.event"][0], json.dumps({"a": 2}))
            finally:
                deregister_event_broker(event_broker_2)

            # After deregistering one broker, it stops receiving events but the other remains registered and active
            publish_event(topic="nautobot.test.another_event", payload={"b": 1})
            self.assertIn("nautobot.test.another_event", event_broker.events)
            self.assertEqual(len(event_broker.events["nautobot.test.another_event"]), 1)
            self.assertEqual(event_broker.events["nautobot.test.another_event"][0], json.dumps({"b": 1}))
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
        EVENT_BROKERS={
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
            publish_event(topic="nautobot.test.event.no-publish", payload={"a": 1})
        # This test assets that only `nautobot.test.event` topic was published and `nautobot.test.event.no-publish` was not published
        self.assertEqual(cm.output, ["INFO:nautobot.events.nautobot.test.event:" + json.dumps({"a": 1}, indent=4)])

    @load_event_broker_override_settings(
        EVENT_BROKERS={
            "SyslogEventBroker": {
                "CLASS": "nautobot.core.events.SyslogEventBroker",
                "TOPICS": {
                    "INCLUDE": ["nautobot.update.*"],
                },
            }
        }
    )
    def test_publish_update_object_event_without_existing_changelog(self):
        """
        Test that an update event creates a event notification with a complete event payload even without existing changelogs.
        https://github.com/nautobot/nautobot/issues/7102
        """
        ObjectChange.objects.all().delete()
        location = Location.objects.first()
        old_status = location.status
        new_status = Status.objects.get_for_model(Location).exclude(pk=old_status.pk).first()
        with self.assertLogs("nautobot.events.nautobot.update.dcim.location") as cm:
            with web_request_context(self.user):
                location.status = new_status
                location.save()

        # Assert that the event notification contains a non-null prechange/postchange values
        # Assert the old status id and new status id are present in the event payload
        self.assertNotIn('"prechange": null', cm.output[0])
        self.assertNotIn('"postchange": null', cm.output[0])
        self.assertIn(f"{old_status.pk}", cm.output[0])
        self.assertIn(f"{new_status.pk}", cm.output[0])

    @load_event_broker_override_settings(
        EVENT_BROKERS={
            "SyslogEventBroker": {
                "CLASS": "nautobot.core.events.SyslogEventBroker",
                "TOPICS": {
                    "INCLUDE": ["nautobot.delete.*"],
                },
            }
        }
    )
    def test_publish_delete_object_event_without_existing_changelog(self):
        """
        Test that a delete event creates a event notification with a complete event payload even without existing changelogs.
        https://github.com/nautobot/nautobot/issues/7102
        """
        ObjectChange.objects.all().delete()
        lt = LocationType.objects.first()
        location = Location.objects.create(
            name="New Test Location", location_type=lt, status=Status.objects.get_for_model(Location).first()
        )
        deleted_pk = location.pk
        with self.assertLogs("nautobot.events.nautobot.delete.dcim.location") as cm:
            with web_request_context(self.user):
                location.delete()

        # Assert that the event notification contains the deleted object PK, non-null prechange values and null postchange value
        self.assertIn(f"{deleted_pk}", cm.output[0])
        self.assertNotIn('"prechange": null', cm.output[0])
        self.assertIn('"postchange": null', cm.output[0])

    @load_event_broker_override_settings(
        EVENT_BROKERS={
            "RedisEventBroker": {
                "CLASS": "nautobot.core.events.RedisEventBroker",
                "OPTIONS": {"url": settings.CACHES["default"]["LOCATION"]},
                "TOPICS": {"EXCLUDE": ["*.test.event.no-publish"]},
            }
        }
    )
    def test_publish_events_to_redis(self):
        url = settings.CACHES["default"]["LOCATION"]
        connection = redis.StrictRedis.from_url(url, decode_responses=True)

        sub = None
        try:
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

            # Assert exclude topics are not published
            publish_event(topic="nautobot.test.event.no-publish", payload={"c": 3})
            self.assertIsNone(sub.get_message(timeout=5.0))
        finally:
            if sub is not None:
                sub.close()

    def test_invalid_event_broker_config(self):
        with self.assertRaises(EventBrokerNotFound) as err:
            broker_config = {
                "TestEventBroker": {
                    "CLASS": "nautobot.core.tests.invalid_path.TestEventBroker",
                }
            }
            load_event_brokers(broker_config)
        self.assertEqual(
            str(err.exception),
            "Unable to import Event Broker TestEventBroker.",
        )

        with self.assertRaises(EventBrokerImproperlyConfigured) as err:
            broker_config = {
                "TestEventBroker": {
                    "CLASS": "nautobot.core.tests.test_events.InvalidTestEventBroker",
                }
            }
            load_event_brokers(broker_config)
        self.assertEqual(
            str(err.exception),
            "TestEventBroker Malformed Event Broker Settings: Broker provided is not an EventBroker",
        )

        with self.assertRaises(EventBrokerImproperlyConfigured) as err:
            broker_config = {
                "TestEventBroker": {"CLASS": "nautobot.core.tests.test_events.TestEventBroker", "TOPICS": []}
            }
            load_event_brokers(broker_config)
        self.assertEqual(
            str(err.exception),
            "TestEventBroker Malformed Event Broker Settings: Expected `TOPICS` to be a 'dict', instead a 'list' was provided",
        )

        with self.assertRaises(EventBrokerImproperlyConfigured) as err:
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
            "TestEventBroker Malformed Event Broker Settings: Expected `INCLUDE` to be a 'list' or 'tuple', instead a 'str' was provided",
        )

        with self.assertRaises(EventBrokerImproperlyConfigured) as err:
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
            "TestEventBroker Malformed Event Broker Settings: Expected `EXCLUDE` to be a 'list' or 'tuple', instead a 'str' was provided",
        )
