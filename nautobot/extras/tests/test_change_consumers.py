"""Tests for `nautobot.extras.change_consumers`."""

from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from django.test import tag

from nautobot.core.events import deregister_event_broker, EventBroker, register_event_broker
from nautobot.core.testing import TestCase
from nautobot.dcim.models import Location
from nautobot.extras.change_consumers import (
    change_has_consumers,
    get_change_event_topic,
    invalidate_change_consumers_cache,
)
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.models import Job, JobHook, Webhook
from nautobot.extras.registry import registry


class CollectingEventBroker(EventBroker):
    """Broker that records what it is asked to publish."""

    def __init__(self, **kwargs):
        self.events = defaultdict(list)
        super().__init__(**kwargs)

    def publish(self, *, topic, payload):
        self.events[topic].append(payload)


@tag("unit")
class GetChangeEventTopicTest(TestCase):
    def test_topic_is_built_from_action_and_content_type(self):
        content_type = ContentType.objects.get_for_model(Location)
        self.assertEqual(
            get_change_event_topic(content_type, ObjectChangeActionChoices.ACTION_UPDATE),
            "nautobot.update.dcim.location",
        )

    def test_topic_matches_what_web_request_context_publishes(self):
        """The topic here must stay identical to the one `web_request_context()` publishes to."""
        content_type = ContentType.objects.get_for_model(Location)
        for action in (
            ObjectChangeActionChoices.ACTION_CREATE,
            ObjectChangeActionChoices.ACTION_UPDATE,
            ObjectChangeActionChoices.ACTION_DELETE,
        ):
            with self.subTest(action=action):
                self.assertEqual(
                    get_change_event_topic(content_type, action),
                    f"nautobot.{action}.{content_type.app_label}.{content_type.model}",
                )


class ChangeConsumersTestMixin:
    """Shared fixtures: a content type that supports hooks, and one that supports neither kind."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.location_ct = ContentType.objects.get_for_model(Location)
        # ContentType itself is neither webhook-enabled nor change-logged, so it exercises both guards.
        cls.unsupported_ct = ContentType.objects.get_for_model(ContentType)

    def setUp(self):
        super().setUp()
        # Other tests in the same process may have populated the cache for these content types.
        invalidate_change_consumers_cache()

    def assertHasConsumers(self, content_type=None, action=ObjectChangeActionChoices.ACTION_UPDATE):
        self.assertTrue(change_has_consumers(content_type or self.location_ct, action))

    def assertHasNoConsumers(self, content_type=None, action=ObjectChangeActionChoices.ACTION_UPDATE):
        self.assertFalse(change_has_consumers(content_type or self.location_ct, action))

    def create_webhook(self, content_type=None, **kwargs):
        kwargs.setdefault("name", f"Webhook {Webhook.objects.count()}")
        kwargs.setdefault("payload_url", "http://localhost/")
        kwargs.setdefault("type_update", True)
        webhook = Webhook.objects.create(**kwargs)
        webhook.content_types.set([content_type or self.location_ct])
        return webhook

    def create_job_hook(self, content_type=None, **kwargs):
        kwargs.setdefault("name", f"JobHook {JobHook.objects.count()}")
        kwargs.setdefault("job", Job.objects.get(job_class_name="TestJobHookReceiverLog"))
        kwargs.setdefault("type_update", True)
        job_hook = JobHook.objects.create(**kwargs)
        job_hook.content_types.set([content_type or self.location_ct])
        return job_hook


@tag("unit")
class ChangeHasConsumersTest(ChangeConsumersTestMixin, TestCase):
    def test_no_consumers_configured(self):
        self.assertHasNoConsumers()

    #
    # Webhooks
    #

    def test_enabled_webhook_is_a_consumer(self):
        self.create_webhook()
        self.assertHasConsumers()

    def test_disabled_webhook_is_not_a_consumer(self):
        self.create_webhook(enabled=False)
        self.assertHasNoConsumers()

    def test_webhook_for_another_action_is_not_a_consumer(self):
        self.create_webhook(type_update=False, type_delete=True)
        self.assertHasNoConsumers(action=ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertHasConsumers(action=ObjectChangeActionChoices.ACTION_DELETE)

    def test_webhook_for_another_content_type_is_not_a_consumer(self):
        self.create_webhook(content_type=ContentType.objects.get_for_model(Job))
        self.assertHasNoConsumers()

    def test_webhook_on_model_that_does_not_support_webhooks_is_ignored(self):
        """Mirrors the `@extras_features("webhooks")` guard in `enqueue_webhooks()`."""
        self.assertNotIn(
            self.unsupported_ct.model,
            registry["model_features"]["webhooks"].get(self.unsupported_ct.app_label, []),
        )
        self.create_webhook(content_type=self.unsupported_ct)
        self.assertHasNoConsumers(content_type=self.unsupported_ct)

    #
    # Job hooks
    #

    def test_enabled_job_hook_is_a_consumer(self):
        self.create_job_hook()
        self.assertHasConsumers()

    def test_disabled_job_hook_is_not_a_consumer(self):
        self.create_job_hook(enabled=False)
        self.assertHasNoConsumers()

    def test_job_hook_for_another_action_is_not_a_consumer(self):
        self.create_job_hook(type_update=False, type_create=True)
        self.assertHasNoConsumers(action=ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertHasConsumers(action=ObjectChangeActionChoices.ACTION_CREATE)

    def test_job_hook_on_non_change_logged_model_is_ignored(self):
        """Mirrors the change-logged guard in `enqueue_job_hooks()`."""
        self.create_job_hook(content_type=self.unsupported_ct)
        self.assertHasNoConsumers(content_type=self.unsupported_ct)

    #
    # Event brokers
    #

    def test_broker_subscribed_to_the_topic_is_a_consumer(self):
        broker = CollectingEventBroker(include_topics=["nautobot.update.dcim.*"])
        register_event_broker(broker)
        try:
            self.assertHasConsumers(action=ObjectChangeActionChoices.ACTION_UPDATE)
            self.assertHasNoConsumers(action=ObjectChangeActionChoices.ACTION_CREATE)
        finally:
            deregister_event_broker(broker)

    def test_broker_excluding_the_topic_is_not_a_consumer(self):
        broker = CollectingEventBroker(include_topics=["*"], exclude_topics=["nautobot.*.dcim.location"])
        register_event_broker(broker)
        try:
            self.assertHasNoConsumers()
        finally:
            deregister_event_broker(broker)

    def test_broker_is_checked_without_touching_the_database(self):
        broker = CollectingEventBroker(include_topics=["*"])
        register_event_broker(broker)
        try:
            with self.assertNumQueries(0):
                self.assertHasConsumers()
        finally:
            deregister_event_broker(broker)

    #
    # Caching
    #

    def test_answer_is_cached(self):
        self.create_webhook()
        self.assertHasConsumers()
        with self.assertNumQueries(0):
            self.assertHasConsumers()

    def test_cache_is_keyed_by_content_type_and_action(self):
        self.create_webhook(content_type=self.location_ct, type_update=True)
        self.assertHasConsumers(action=ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertHasNoConsumers(action=ObjectChangeActionChoices.ACTION_CREATE)
        self.assertHasNoConsumers(content_type=self.unsupported_ct)


@tag("unit")
class ChangeConsumersCacheInvalidationTest(ChangeConsumersTestMixin, TestCase):
    """The cached answer must not survive a change to the Webhook/JobHook data it was computed from."""

    def test_creating_a_webhook_invalidates_the_cache(self):
        self.assertHasNoConsumers()
        self.create_webhook()
        self.assertHasConsumers()

    def test_deleting_a_webhook_invalidates_the_cache(self):
        webhook = self.create_webhook()
        self.assertHasConsumers()
        webhook.delete()
        self.assertHasNoConsumers()

    def test_disabling_a_webhook_invalidates_the_cache(self):
        webhook = self.create_webhook()
        self.assertHasConsumers()
        webhook.enabled = False
        webhook.save()
        self.assertHasNoConsumers()

    def test_changing_webhook_content_types_invalidates_the_cache(self):
        webhook = self.create_webhook(content_type=ContentType.objects.get_for_model(Job))
        self.assertHasNoConsumers()
        webhook.content_types.set([self.location_ct])
        self.assertHasConsumers()

    def test_clearing_webhook_content_types_invalidates_the_cache(self):
        webhook = self.create_webhook()
        self.assertHasConsumers()
        webhook.content_types.clear()
        self.assertHasNoConsumers()

    def test_creating_a_job_hook_invalidates_the_cache(self):
        self.assertHasNoConsumers()
        self.create_job_hook()
        self.assertHasConsumers()

    def test_deleting_a_job_hook_invalidates_the_cache(self):
        job_hook = self.create_job_hook()
        self.assertHasConsumers()
        job_hook.delete()
        self.assertHasNoConsumers()

    def test_changing_job_hook_content_types_invalidates_the_cache(self):
        job_hook = self.create_job_hook(content_type=ContentType.objects.get_for_model(Job))
        self.assertHasNoConsumers()
        job_hook.content_types.set([self.location_ct])
        self.assertHasConsumers()
