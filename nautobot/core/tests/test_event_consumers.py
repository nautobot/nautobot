"""Test cases for the event consumer framework (PR 1 + PR 2)."""

from collections import deque
import os
from unittest import mock
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext

from nautobot.core.celery import registry

# ``EventConsumerJob`` is exposed via the lazy ``__getattr__`` in nautobot.core.events.
# pylint: disable=no-name-in-module
from nautobot.core.events import (
    _EVENT_CONSUMERS,
    ConsumedEvent,
    deregister_event_consumer,
    EventConsumer,
    EventConsumerJob,
    is_topic_match,
    load_event_consumers,
    publish_event,
    RedisEventConsumer,
    register_event_consumer,
    register_event_consumer_job,
)

# pylint: enable=no-name-in-module
from nautobot.core.events.exceptions import (
    EventConsumerImproperlyConfigured,
    EventConsumerNotFound,
)
from nautobot.core.testing import TestCase, TransactionTestCase
from nautobot.core.testing.context import (
    load_event_broker_override_settings,
    load_event_consumer_override_settings,
)
from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from nautobot.extras.models import Job, JobQueue, Secret, SecretsGroup, SecretsGroupAssociation


class _BufferingEventConsumer(EventConsumer):
    """In-memory ``EventConsumer`` used by tests."""

    def __init__(self, password=None, **kwargs):
        self.password = password
        self.subscribed_topics = None
        self.acked = []
        self.nacked = []
        self.outbox = deque()
        self.closed = False
        super().__init__(**kwargs)

    def subscribe(self, topics):
        self.subscribed_topics = list(topics)

    def read(self):
        while self.outbox:
            yield self.outbox.popleft()

    def ack(self, event):
        self.acked.append(event)

    def nack(self, event, requeue=True):
        self.nacked.append((event, requeue))

    def close(self):
        self.closed = True


class _NotAnEventConsumer:
    """Class that does NOT inherit from ``EventConsumer`` — used for negative tests."""

    def subscribe(self, topics):
        pass

    def read(self):
        return iter([])

    def ack(self, event):
        pass

    def nack(self, event, requeue=True):
        pass


def _clear_consumer_registry():
    """Drop every entry from ``_EVENT_CONSUMERS`` — for use in test teardown."""
    for entry in list(_EVENT_CONSUMERS):
        deregister_event_consumer(entry["consumer"])


class EventConsumerRegistrationTest(TestCase):
    def tearDown(self):
        super().tearDown()
        _clear_consumer_registry()

    def test_register_and_deregister_consumer(self):
        consumer = _BufferingEventConsumer()
        register_event_consumer(consumer, name="TestConsumer")
        self.assertEqual(len(_EVENT_CONSUMERS), 1)
        self.assertEqual(_EVENT_CONSUMERS[0]["name"], "TestConsumer")
        self.assertIs(_EVENT_CONSUMERS[0]["consumer"], consumer)
        # Defaults for the SecretsGroup access/secret types
        self.assertEqual(_EVENT_CONSUMERS[0]["user_access_type"], "Generic")
        self.assertEqual(_EVENT_CONSUMERS[0]["user_secret_type"], "username")
        # Duplicate registration is a no-op (preserves the first entry)
        register_event_consumer(consumer, name="TestConsumer")
        self.assertEqual(len(_EVENT_CONSUMERS), 1)
        # Deregister removes the entry
        deregister_event_consumer(consumer)
        self.assertEqual(_EVENT_CONSUMERS, [])
        # Duplicate deregistration is a warning, not an error
        deregister_event_consumer(consumer)

    def test_register_consumer_rejects_non_event_consumer(self):
        with self.assertRaises(EventConsumerImproperlyConfigured) as cm:
            register_event_consumer(_NotAnEventConsumer(), name="Bad")
        self.assertIn("is not an EventConsumer instance", str(cm.exception))

    def test_register_event_consumer_job_appends_binding(self):
        consumer = _BufferingEventConsumer()
        register_event_consumer(consumer, name="C1")

        register_event_consumer_job(
            consumer_name="C1",
            topic_pattern="nautobot.create.dcim.device",
            job_class="my_app.jobs.HandleDeviceCreated",
        )
        register_event_consumer_job(
            consumer_name="C1",
            topic_pattern="nautobot.update.*",
            job_class="my_app.jobs.HandleAnyUpdate",
            queue="event-dispatch",
        )

        bindings = _EVENT_CONSUMERS[0]["job_bindings"]
        self.assertEqual(len(bindings), 2)
        self.assertEqual(bindings[0]["topic_pattern"], "nautobot.create.dcim.device")
        self.assertEqual(bindings[0]["job_class_path"], "my_app.jobs.HandleDeviceCreated")
        self.assertIsNone(bindings[0]["queue"])
        self.assertEqual(bindings[1]["queue"], "event-dispatch")
        # is_topic_match should compose cleanly against these patterns
        self.assertTrue(is_topic_match("nautobot.update.dcim.device", [bindings[1]["topic_pattern"]]))
        self.assertFalse(is_topic_match("nautobot.create.dcim.device", [bindings[1]["topic_pattern"]]))

    def test_register_event_consumer_job_unknown_consumer(self):
        with self.assertRaises(EventConsumerImproperlyConfigured) as cm:
            register_event_consumer_job(
                consumer_name="DoesNotExist",
                topic_pattern="nautobot.create.*",
                job_class="my_app.jobs.Foo",
            )
        self.assertIn("No event consumer registered with name 'DoesNotExist'", str(cm.exception))

    def test_register_consumer_normalizes_job_class_objects(self):
        # Build a class whose ``__name__`` truly is "FakeJob" (class-body __name__
        # assignment is ignored — Python reads the slot from the type itself).
        FakeJob = type("FakeJob", (), {"__module__": "fake.module"})

        consumer = _BufferingEventConsumer()
        register_event_consumer(
            consumer,
            name="C2",
            job_bindings=[
                {"topic_pattern": "nautobot.create.*", "job_class": FakeJob},
            ],
        )
        self.assertEqual(_EVENT_CONSUMERS[0]["job_bindings"][0]["job_class_path"], "fake.module.FakeJob")


class LoadEventConsumersTest(TestCase):
    def tearDown(self):
        super().tearDown()
        _clear_consumer_registry()

    def test_load_event_consumers_full_config(self):
        load_event_consumers(
            {
                "RedisConsumer": {
                    "CLASS": "nautobot.core.tests.test_event_consumers._BufferingEventConsumer",
                    "OPTIONS": {},
                    "TOPICS": {
                        "INCLUDE": ["nautobot.create.*"],
                        "EXCLUDE": ["*.no-publish*"],
                    },
                    "SECRETS_GROUP": "event-consumer-creds",
                    "USER_ACCESS_TYPE": "HTTP(S)",
                    "USER_SECRET_TYPE": "username",
                    "JOB_BINDINGS": [
                        {
                            "topic_pattern": "nautobot.create.dcim.device",
                            "job_class": "my_app.jobs.HandleDeviceCreated",
                            "queue": "event-dispatch",
                        },
                    ],
                }
            }
        )
        self.assertEqual(len(_EVENT_CONSUMERS), 1)
        entry = _EVENT_CONSUMERS[0]
        self.assertEqual(entry["name"], "RedisConsumer")
        self.assertIsInstance(entry["consumer"], _BufferingEventConsumer)
        self.assertEqual(entry["consumer"].include_topics, ["nautobot.create.*"])
        self.assertEqual(entry["consumer"].exclude_topics, ["*.no-publish*"])
        self.assertEqual(entry["secrets_group_name"], "event-consumer-creds")
        self.assertEqual(entry["user_access_type"], "HTTP(S)")
        self.assertEqual(entry["user_secret_type"], "username")
        self.assertEqual(entry["job_bindings"][0]["job_class_path"], "my_app.jobs.HandleDeviceCreated")
        self.assertEqual(entry["job_bindings"][0]["queue"], "event-dispatch")

    def test_load_event_consumers_passes_password(self):
        """A top-level ``PASSWORD`` is forwarded to the consumer as a ``password`` kwarg."""
        load_event_consumers(
            {
                "RedisConsumer": {
                    "CLASS": "nautobot.core.tests.test_event_consumers._BufferingEventConsumer",
                    "PASSWORD": "sup3rs3cret",
                    "TOPICS": {"INCLUDE": ["nautobot.create.*"]},
                }
            }
        )
        self.assertEqual(len(_EVENT_CONSUMERS), 1)
        self.assertEqual(_EVENT_CONSUMERS[0]["consumer"].password, "sup3rs3cret")

    def test_load_event_consumers_omits_password_when_absent(self):
        """When no ``PASSWORD`` is configured, the consumer receives no ``password`` kwarg."""
        load_event_consumers(
            {
                "RedisConsumer": {
                    "CLASS": "nautobot.core.tests.test_event_consumers._BufferingEventConsumer",
                    "TOPICS": {"INCLUDE": ["nautobot.create.*"]},
                }
            }
        )
        self.assertEqual(len(_EVENT_CONSUMERS), 1)
        self.assertIsNone(_EVENT_CONSUMERS[0]["consumer"].password)

    def test_load_event_consumers_does_not_query_orm(self):
        """The guardrail: ``load_event_consumers`` runs before ``django.setup()`` in production,
        so it must not perform any ORM access. Future contributors who accidentally add a
        ``SecretsGroup.objects.get(...)`` or similar at this layer will trip this assertion.
        """
        config = {
            "RedisConsumer": {
                "CLASS": "nautobot.core.tests.test_event_consumers._BufferingEventConsumer",
                "TOPICS": {"INCLUDE": ["nautobot.create.*"]},
                "SECRETS_GROUP": "event-consumer-creds",
                "JOB_BINDINGS": [
                    {
                        "topic_pattern": "nautobot.create.dcim.device",
                        "job_class": "my_app.jobs.HandleDeviceCreated",
                    },
                ],
            }
        }
        with CaptureQueriesContext(connection) as ctx:
            load_event_consumers(config)
        self.assertEqual(
            len(ctx.captured_queries),
            0,
            f"load_event_consumers must not query the ORM (ran {len(ctx.captured_queries)} queries: {ctx.captured_queries})",
        )

    def test_load_event_consumers_validates_class_path(self):
        with self.assertRaises(EventConsumerNotFound) as cm:
            load_event_consumers({"BogusConsumer": {"CLASS": "nautobot.core.tests.invalid_path.NoSuchConsumer"}})
        self.assertEqual(str(cm.exception), "Unable to import Event Consumer BogusConsumer.")

    def test_load_event_consumers_rejects_non_event_consumer_class(self):
        with self.assertRaises(EventConsumerImproperlyConfigured) as cm:
            load_event_consumers(
                {
                    "Bad": {
                        "CLASS": "nautobot.core.tests.test_event_consumers._NotAnEventConsumer",
                    }
                }
            )
        self.assertEqual(
            str(cm.exception),
            "Bad Malformed Event Consumer Settings: Consumer provided is not an EventConsumer",
        )

    def test_load_event_consumers_validates_topics_dict(self):
        with self.assertRaises(EventConsumerImproperlyConfigured) as cm:
            load_event_consumers(
                {
                    "Bad": {
                        "CLASS": "nautobot.core.tests.test_event_consumers._BufferingEventConsumer",
                        "TOPICS": [],
                    }
                }
            )
        self.assertEqual(
            str(cm.exception),
            "Bad Malformed Event Consumer Settings: Expected `TOPICS` to be a 'dict', instead a 'list' was provided",
        )

    def test_load_event_consumers_validates_include_list(self):
        with self.assertRaises(EventConsumerImproperlyConfigured) as cm:
            load_event_consumers(
                {
                    "Bad": {
                        "CLASS": "nautobot.core.tests.test_event_consumers._BufferingEventConsumer",
                        "TOPICS": {"INCLUDE": "nautobot.*"},
                    }
                }
            )
        self.assertIn("Expected `INCLUDE` to be a 'list' or 'tuple'", str(cm.exception))

    def test_load_event_consumers_validates_exclude_list(self):
        with self.assertRaises(EventConsumerImproperlyConfigured) as cm:
            load_event_consumers(
                {
                    "Bad": {
                        "CLASS": "nautobot.core.tests.test_event_consumers._BufferingEventConsumer",
                        "TOPICS": {"EXCLUDE": "nautobot.*"},
                    }
                }
            )
        self.assertIn("Expected `EXCLUDE` to be a 'list' or 'tuple'", str(cm.exception))

    def test_load_event_consumers_validates_job_bindings_list(self):
        with self.assertRaises(EventConsumerImproperlyConfigured) as cm:
            load_event_consumers(
                {
                    "Bad": {
                        "CLASS": "nautobot.core.tests.test_event_consumers._BufferingEventConsumer",
                        "JOB_BINDINGS": "not a list",
                    }
                }
            )
        self.assertIn("Expected `JOB_BINDINGS` to be a 'list' or 'tuple'", str(cm.exception))

    def test_load_event_consumers_validates_binding_keys(self):
        with self.assertRaises(EventConsumerImproperlyConfigured) as cm:
            load_event_consumers(
                {
                    "Bad": {
                        "CLASS": "nautobot.core.tests.test_event_consumers._BufferingEventConsumer",
                        "JOB_BINDINGS": [{"topic_pattern": "nautobot.*"}],  # missing job_class
                    }
                }
            )
        self.assertIn("each JOB_BINDINGS entry must be a dict", str(cm.exception))

    @load_event_consumer_override_settings(
        EVENT_CONSUMERS={
            "DecoratorConsumer": {
                "CLASS": "nautobot.core.tests.test_event_consumers._BufferingEventConsumer",
                "TOPICS": {"INCLUDE": ["nautobot.create.*"]},
            }
        }
    )
    def test_load_event_consumer_override_settings_decorator(self):
        """The test decorator registers consumers for the duration of the test, cleans up after."""
        self.assertEqual(len(_EVENT_CONSUMERS), 1)
        self.assertEqual(_EVENT_CONSUMERS[0]["name"], "DecoratorConsumer")
        self.assertEqual(_EVENT_CONSUMERS[0]["consumer"].include_topics, ["nautobot.create.*"])


class EventConsumerJobTest(TestCase):
    """Behavior of the abstract ``EventConsumerJob`` base class itself.

    End-to-end tests that drive a concrete subclass through ``JobResult.enqueue_job`` are
    covered in PR 2 alongside the ``run_event_consumers`` management command.
    """

    def test_event_consumer_job_meta_is_hidden(self):
        self.assertTrue(EventConsumerJob.Meta.hidden)
        self.assertFalse(EventConsumerJob.Meta.has_sensitive_variables)

    def test_event_consumer_job_not_in_jobs_registry(self):
        """The abstract base is never passed to ``register_jobs`` — it must not appear in the registry."""
        class_path = f"{EventConsumerJob.__module__}.{EventConsumerJob.__name__}"
        self.assertNotIn(class_path, registry["jobs"])

    def test_event_consumer_job_run_delegates_to_process_event(self):
        """``run`` should forward the payload kwargs to ``process_event`` and return its result."""

        class _MyJob(EventConsumerJob):
            class Meta:
                hidden = True
                has_sensitive_variables = False

            def process_event(self, *, cleanup_types, max_age=None):
                return {"cleanup_types": cleanup_types, "max_age": max_age}

        result = _MyJob().run(cleanup_types=["extras.ObjectChange"], max_age=None)
        self.assertEqual(result["cleanup_types"], ["extras.ObjectChange"])
        self.assertIsNone(result["max_age"])

    def test_event_consumer_job_run_forwards_arbitrary_payload_kwargs(self):
        """The payload is spread as kwargs, so ``process_event(**kwargs)`` receives it verbatim."""

        class _MyJob(EventConsumerJob):
            class Meta:
                hidden = True
                has_sensitive_variables = False

            def process_event(self, **kwargs):
                return kwargs

        self.assertEqual(_MyJob().run(a=1, b="two"), {"a": 1, "b": "two"})

    def test_event_consumer_job_process_event_must_be_overridden(self):
        """Calling ``run`` on a subclass that forgot to override ``process_event`` raises."""

        class _ForgotToOverride(EventConsumerJob):
            class Meta:
                hidden = True
                has_sensitive_variables = False

        with self.assertRaises(NotImplementedError) as cm:
            _ForgotToOverride().run()
        self.assertIn("_ForgotToOverride must implement process_event", str(cm.exception))


class ConsumedEventDataclassTest(TestCase):
    def test_default_headers_and_broker_ref(self):
        event = ConsumedEvent(topic="t", payload={"a": 1})
        self.assertEqual(event.headers, {})
        self.assertIsNone(event.broker_ref)
        # Each instance gets its own dict (default_factory, not a shared mutable default)
        other = ConsumedEvent(topic="t2", payload={})
        other.headers["x"] = 1
        self.assertEqual(event.headers, {})

    def test_explicit_fields(self):
        ref = mock.sentinel.handle
        event = ConsumedEvent(topic="t", payload={"a": 1}, headers={"h": "v"}, broker_ref=ref)
        self.assertEqual(event.topic, "t")
        self.assertEqual(event.payload, {"a": 1})
        self.assertEqual(event.headers, {"h": "v"})
        self.assertIs(event.broker_ref, ref)


# ---------------------------------------------------------------------------
# PR 2: RedisEventConsumer + run_event_consumers management command
# ---------------------------------------------------------------------------


class RedisEventConsumerTest(TestCase):
    """Round-trip a ``RedisEventConsumer`` against a real Redis (the project's test Redis)."""

    @load_event_broker_override_settings(
        EVENT_BROKERS={
            "RedisEventBroker": {
                "CLASS": "nautobot.core.events.RedisEventBroker",
                "OPTIONS": {"url": settings.CACHES["default"]["LOCATION"]},
            }
        }
    )
    def test_redis_consumer_subscribes_and_reads(self):
        # Use a unique topic per run so concurrent test workers don't collide.
        topic = f"nautobot.test.consumer.{uuid.uuid4().hex}"
        consumer = RedisEventConsumer(url=settings.CACHES["default"]["LOCATION"])
        consumer.subscribe([topic])
        # Drain the initial 'psubscribe' confirmation message before publishing
        # so the first pmessage we see is the real one.
        consumer.pubsub.get_message(timeout=2.0)

        publish_event(topic=topic, payload={"a": 1})

        # Pull a single event directly via the underlying pubsub (avoids the read()
        # generator's shutdown_event coupling, which is exercised separately below).
        msg = consumer.pubsub.get_message(timeout=5.0)
        self.assertIsNotNone(msg, "did not receive any message from Redis within 5s")
        self.assertEqual(msg["type"], "pmessage")
        self.assertEqual(msg["channel"], topic)
        # The broker JSON-encodes the payload; the consumer's read() loop would deserialize it.
        self.assertEqual(msg["data"], '{"a": 1}')
        consumer.close()

    def test_redis_consumer_skips_non_json_payload(self):
        consumer = RedisEventConsumer(url=settings.CACHES["default"]["LOCATION"])
        try:
            # Stub out the pubsub message stream — first a non-JSON payload, then a clean one.
            messages = [
                {"type": "pmessage", "channel": "t", "pattern": "t", "data": "not-json"},
                {"type": "pmessage", "channel": "t", "pattern": "t", "data": '{"ok": true}'},
                None,  # idle tick; loop checks shutdown flag
            ]
            consumer.pubsub = mock.Mock()
            consumer.pubsub.get_message = mock.Mock(side_effect=[*messages, None])

            iterator = consumer.read()
            event = next(iterator)
            # The non-JSON message is skipped with a warning; we receive the second one.
            self.assertEqual(event.payload, {"ok": True})
        finally:
            consumer.close()

    def test_redis_consumer_skips_subscribe_confirmation(self):
        consumer = RedisEventConsumer(url=settings.CACHES["default"]["LOCATION"])
        try:
            consumer.pubsub = mock.Mock()
            consumer.pubsub.get_message = mock.Mock(
                side_effect=[
                    {"type": "psubscribe", "channel": "t", "pattern": None, "data": 1},
                    {"type": "pmessage", "channel": "t", "pattern": "t", "data": '{"x": 1}'},
                ]
            )
            event = next(consumer.read())
            self.assertEqual(event.payload, {"x": 1})
            self.assertEqual(event.topic, "t")
        finally:
            consumer.close()

    def test_redis_consumer_close_terminates_read(self):
        consumer = RedisEventConsumer(url=settings.CACHES["default"]["LOCATION"])
        consumer.pubsub = mock.Mock()
        consumer.pubsub.get_message = mock.Mock(return_value=None)
        # After close() the read() generator should exit immediately.
        consumer.close()
        self.assertEqual(list(consumer.read()), [])


# ---------------------------------------------------------------------------
# run_event_consumers management command
# ---------------------------------------------------------------------------


def _setup_secrets_group(name, env_var, username):
    """Create a SecretsGroup whose TYPE_USERNAME secret reads ``username`` from ``env_var``."""
    os.environ[env_var] = username
    secret = Secret.objects.create(
        name=f"{name}-username",
        provider="environment-variable",
        parameters={"variable": env_var},
    )
    group = SecretsGroup.objects.create(name=name)
    SecretsGroupAssociation.objects.create(
        secrets_group=group,
        secret=secret,
        access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
        secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
    )
    return group


def _create_fake_job(module_name, class_name):
    """Insert a ``Job`` model row pointing at a fake (non-importable) class path.

    The class itself doesn't need to exist for ``JobResult.enqueue_job`` since the
    Celery worker is what actually loads the class — but the management command does
    an ``import_string`` check at startup, so we point at a real existing job class
    in the codebase to satisfy that check, while keeping the Job row name distinct.
    """
    job_queue, _ = JobQueue.objects.get_or_create(name="default")
    return Job.objects.create(
        module_name=module_name,
        job_class_name=class_name,
        grouping="test-event-consumer",
        name=f"{module_name}.{class_name}",
        default_job_queue=job_queue,
    )


class RunEventConsumersCommandTest(TransactionTestCase):
    """End-to-end tests for the ``run_event_consumers`` management command."""

    databases = ("default", "job_logs")

    # We exercise the command's wiring (user resolution, binding resolution, dispatch).
    # The Job's real execution is out of scope; we patch ``JobResult.enqueue_job`` so the
    # test doesn't need an actually-importable Job class or a running Celery worker.

    JOB_MODULE = "nautobot.core.tests.fake_event_consumer_module"
    JOB_CLASS = "FakeEventConsumerJob"

    def setUp(self):
        super().setUp()
        _clear_consumer_registry()
        self.env_var = f"TEST_EVENT_CONSUMER_USERNAME_{uuid.uuid4().hex[:8]}"
        self.username = f"event-runner-{uuid.uuid4().hex[:8]}"
        get_user_model().objects.create(username=self.username, is_active=True)
        self.secrets_group = _setup_secrets_group(
            f"event-consumer-creds-{uuid.uuid4().hex[:8]}",
            self.env_var,
            self.username,
        )
        self.job_model = _create_fake_job(self.JOB_MODULE, self.JOB_CLASS)

    def tearDown(self):
        _clear_consumer_registry()
        os.environ.pop(self.env_var, None)
        super().tearDown()

    def _register_consumer(self, *, name="C1", bindings=None, include_topics=None, exclude_topics=None):
        consumer = _BufferingEventConsumer(
            include_topics=include_topics or ["*"],
            exclude_topics=exclude_topics or [],
        )
        register_event_consumer(
            consumer,
            name=name,
            secrets_group_name=self.secrets_group.name,
            job_bindings=bindings
            or [
                {
                    "topic_pattern": "nautobot.create.*",
                    "job_class": f"{self.JOB_MODULE}.{self.JOB_CLASS}",
                }
            ],
        )
        return consumer

    def test_command_errors_when_no_consumers_registered(self):
        with self.assertRaises(CommandError) as cm:
            call_command("run_event_consumers", "--exit-when-idle")
        self.assertIn("No EventConsumers are registered", str(cm.exception))

    def test_command_errors_when_secrets_group_missing(self):
        # Register a consumer pointing at a SecretsGroup name that doesn't exist.
        consumer = _BufferingEventConsumer()
        register_event_consumer(
            consumer,
            name="C1",
            secrets_group_name="does-not-exist",
            job_bindings=[],
        )
        with self.assertRaises(CommandError) as cm:
            call_command("run_event_consumers", "--exit-when-idle")
        self.assertIn("SecretsGroup 'does-not-exist' does not exist", str(cm.exception))

    def test_command_errors_when_secrets_group_unconfigured(self):
        consumer = _BufferingEventConsumer()
        register_event_consumer(consumer, name="C1", job_bindings=[])  # no secrets_group_name
        with self.assertRaises(CommandError) as cm:
            call_command("run_event_consumers", "--exit-when-idle")
        self.assertIn("no SECRETS_GROUP configured", str(cm.exception))

    def test_command_errors_when_user_missing(self):
        os.environ[self.env_var] = "this-user-doesnt-exist"
        self._register_consumer()
        with self.assertRaises(CommandError) as cm:
            call_command("run_event_consumers", "--exit-when-idle")
        self.assertIn("no active user with username='this-user-doesnt-exist'", str(cm.exception))

    def test_command_errors_when_job_model_missing(self):
        # Reference a job class with no corresponding Job row.
        consumer = _BufferingEventConsumer()
        register_event_consumer(
            consumer,
            name="C1",
            secrets_group_name=self.secrets_group.name,
            job_bindings=[
                {
                    "topic_pattern": "nautobot.create.*",
                    "job_class": "this.module.DoesNotExist",
                }
            ],
        )
        with self.assertRaises(CommandError) as cm:
            call_command("run_event_consumers", "--exit-when-idle")
        # ImportError surfaces before the Job lookup
        self.assertIn("cannot import job_class", str(cm.exception))

    def test_command_errors_when_job_row_missing(self):
        # Use a class path that imports cleanly but has no Job DB row.
        consumer = _BufferingEventConsumer()
        register_event_consumer(
            consumer,
            name="C1",
            secrets_group_name=self.secrets_group.name,
            job_bindings=[
                {
                    "topic_pattern": "nautobot.create.*",
                    "job_class": "nautobot.core.events.EventConsumerJob",  # importable, no Job row
                }
            ],
        )
        with self.assertRaises(CommandError) as cm:
            call_command("run_event_consumers", "--exit-when-idle")
        self.assertIn("no Job database row for", str(cm.exception))

    @mock.patch("nautobot.core.management.commands.run_event_consumers.JobResult.enqueue_job")
    def test_command_dispatches_matching_event(self, mock_enqueue):
        consumer = self._register_consumer()
        consumer.outbox.append(ConsumedEvent(topic="nautobot.create.dcim.device", payload={"name": "rtr"}))

        call_command("run_event_consumers", "--exit-when-idle", "--shutdown-timeout", "2")

        self.assertEqual(mock_enqueue.call_count, 1)
        _args, kwargs = mock_enqueue.call_args
        # The event payload is spread as the Job's own kwargs; no event-envelope keys are passed.
        self.assertEqual(kwargs["name"], "rtr")
        self.assertNotIn("topic", kwargs)
        self.assertNotIn("payload", kwargs)
        self.assertNotIn("source_consumer", kwargs)
        self.assertEqual(len(consumer.acked), 1)
        self.assertEqual(len(consumer.nacked), 0)

    @mock.patch("nautobot.core.management.commands.run_event_consumers.JobResult.enqueue_job")
    def test_command_acks_unmatched_topic_with_warning(self, mock_enqueue):
        consumer = self._register_consumer()
        consumer.outbox.append(ConsumedEvent(topic="something.else", payload={}))

        with self.assertLogs("nautobot.core.management.commands.run_event_consumers", level="WARNING") as cm:
            call_command("run_event_consumers", "--exit-when-idle", "--shutdown-timeout", "2")

        self.assertEqual(mock_enqueue.call_count, 0)
        self.assertEqual(len(consumer.acked), 1)
        self.assertEqual(len(consumer.nacked), 0)
        self.assertTrue(
            any("no Job binding matches topic something.else" in line for line in cm.output),
            cm.output,
        )

    @mock.patch("nautobot.core.management.commands.run_event_consumers.JobResult.enqueue_job")
    def test_command_respects_exclude_topics(self, mock_enqueue):
        consumer = self._register_consumer(exclude_topics=["*.no-publish*"])
        consumer.outbox.append(ConsumedEvent(topic="nautobot.create.no-publish", payload={}))

        call_command("run_event_consumers", "--exit-when-idle", "--shutdown-timeout", "2")

        self.assertEqual(mock_enqueue.call_count, 0)
        self.assertEqual(len(consumer.acked), 1)

    @mock.patch("nautobot.core.management.commands.run_event_consumers.JobResult.enqueue_job")
    def test_command_nacks_on_enqueue_failure(self, mock_enqueue):
        mock_enqueue.side_effect = RuntimeError("simulated DB outage")
        consumer = self._register_consumer()
        consumer.outbox.append(ConsumedEvent(topic="nautobot.create.dcim.device", payload={}))

        with self.assertLogs("nautobot.core.management.commands.run_event_consumers", level="ERROR"):
            call_command("run_event_consumers", "--exit-when-idle", "--shutdown-timeout", "2")

        self.assertEqual(mock_enqueue.call_count, 1)
        self.assertEqual(len(consumer.acked), 0)
        self.assertEqual(len(consumer.nacked), 1)
        _event, requeue = consumer.nacked[0]
        self.assertTrue(requeue)

    @mock.patch("nautobot.core.management.commands.run_event_consumers.JobResult.enqueue_job")
    def test_command_consumer_name_filter(self, mock_enqueue):
        # Register two consumers, only run one.
        self._register_consumer(name="C1")
        consumer2 = self._register_consumer(name="C2")
        consumer2.outbox.append(ConsumedEvent(topic="nautobot.create.dcim.device", payload={}))

        call_command(
            "run_event_consumers",
            "--exit-when-idle",
            "--consumer-name",
            "C2",
            "--shutdown-timeout",
            "2",
        )
        # Only C2 ran (and the only event was on its outbox); it should have acked the event.
        self.assertEqual(mock_enqueue.call_count, 1)
        self.assertEqual(len(consumer2.acked), 1)

    def test_command_consumer_name_filter_no_match(self):
        self._register_consumer(name="C1")
        with self.assertRaises(CommandError) as cm:
            call_command("run_event_consumers", "--exit-when-idle", "--consumer-name", "NoSuchConsumer")
        self.assertIn("matching --consumer-name='NoSuchConsumer'", str(cm.exception))
