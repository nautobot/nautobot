"""Test cases for the event notification APIs."""


from collections import defaultdict

from nautobot.core.events import deregister_event_broker, EventBroker, publish_event, register_event_broker
from nautobot.core.testing import TestCase


class TestEventBroker(EventBroker):
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
