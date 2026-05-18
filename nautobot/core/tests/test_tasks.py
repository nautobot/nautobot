"""Tests for the TaskBackend abstraction in nautobot.core.tasks.

These tests cover the backend-agnostic interface introduced to enable
Procrastinate as an alternative to Celery. They do not require a running
broker or database; they validate the dataclasses, the ABC contract, the
factory's settings-driven dispatch, and the CeleryBackend legacy kwargs
shape.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass
from unittest import mock
from uuid import UUID, uuid4

from django.test import SimpleTestCase, override_settings

from nautobot.core.tasks import (
    DispatchResult,
    EnqueueOptions,
    PeriodicRunner,
    TaskBackend,
    get_task_backend,
)
from nautobot.core.tasks.celery_backend import (
    CeleryBackend,
    _build_celery_kwargs_dict,
)


class DispatchResultTests(SimpleTestCase):
    def test_is_dataclass(self):
        self.assertTrue(is_dataclass(DispatchResult))

    def test_is_frozen(self):
        result = DispatchResult(task_id=uuid4(), backend="celery")
        with self.assertRaises(FrozenInstanceError):
            result.backend = "procrastinate"  # type: ignore[misc]

    def test_fields(self):
        tid = uuid4()
        result = DispatchResult(task_id=tid, backend="celery")
        self.assertEqual(result.task_id, tid)
        self.assertEqual(result.backend, "celery")


class EnqueueOptionsTests(SimpleTestCase):
    def test_defaults(self):
        opts = EnqueueOptions()
        self.assertIsNone(opts.queue)
        self.assertIsNone(opts.soft_time_limit)
        self.assertIsNone(opts.time_limit)
        self.assertFalse(opts.profile)
        self.assertFalse(opts.console_log)
        self.assertFalse(opts.ignore_singleton_lock)
        self.assertIsNone(opts.user_id)
        self.assertIsNone(opts.job_model_id)
        self.assertIsNone(opts.schedule_id)
        self.assertIsNone(opts.branch_name)
        self.assertEqual(opts.extra, {})

    def test_extra_field_is_independent_per_instance(self):
        # Guards against the classic dataclass-mutable-default footgun.
        a = EnqueueOptions()
        b = EnqueueOptions()
        a.extra["only_in_a"] = True
        self.assertNotIn("only_in_a", b.extra)


class TaskBackendABCTests(SimpleTestCase):
    def test_cannot_instantiate_abstract_class(self):
        with self.assertRaises(TypeError):
            TaskBackend()  # type: ignore[abstract]

    def test_concrete_subclass_must_implement_all_abstract_methods(self):
        # Subclass missing enqueue_sync should still be unconstructable.
        class Incomplete(TaskBackend):
            name = "incomplete"

            def enqueue(self, **kwargs):
                pass

            def get_active_workers(self):
                return 0

        with self.assertRaises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_complete_subclass_works(self):
        class Complete(TaskBackend):
            name = "complete"

            def enqueue(self, **kwargs):
                return DispatchResult(task_id=uuid4(), backend=self.name)

            def enqueue_sync(self, **kwargs):
                return DispatchResult(task_id=uuid4(), backend=self.name)

            def get_active_workers(self):
                return 1

        backend = Complete()
        self.assertEqual(backend.name, "complete")
        self.assertIsNone(backend.get_periodic_runner())  # default impl

    def test_periodic_runner_is_abstract(self):
        with self.assertRaises(TypeError):
            PeriodicRunner()  # type: ignore[abstract]


class GetTaskBackendFactoryTests(SimpleTestCase):
    def setUp(self):
        # Each test should start with a fresh cache.
        get_task_backend.cache_clear()

    def tearDown(self):
        get_task_backend.cache_clear()

    @override_settings(TASK_BACKEND="celery")
    def test_celery_is_default(self):
        backend = get_task_backend()
        self.assertIsInstance(backend, CeleryBackend)
        self.assertEqual(backend.name, "celery")

    def test_result_is_cached(self):
        get_task_backend.cache_clear()
        first = get_task_backend()
        second = get_task_backend()
        self.assertIs(first, second)

    def test_custom_dotted_path_resolves(self):
        # Use a stub backend defined in this test module via a real dotted path.
        with override_settings(TASK_BACKEND="nautobot.core.tasks.celery_backend.CeleryBackend"):
            get_task_backend.cache_clear()
            backend = get_task_backend()
            self.assertIsInstance(backend, CeleryBackend)


class CeleryBackendLegacyKwargsTests(SimpleTestCase):
    """The legacy ``nautobot_job_*`` keys must match the exact shape produced by
    the old ``JobResult._build_celery_kwargs`` method, because NautobotTask /
    NautobotDatabaseScheduler / JobResult.celery_kwargs all consume them.
    """

    def test_minimal_options(self):
        user_id = uuid4()
        job_model_id = uuid4()
        options = EnqueueOptions(
            queue="default",
            user_id=user_id,
            job_model_id=job_model_id,
        )
        result = _build_celery_kwargs_dict(options)
        self.assertEqual(result["nautobot_job_user_id"], str(user_id))
        self.assertEqual(result["nautobot_job_job_model_id"], str(job_model_id))
        self.assertEqual(result["queue"], "default")
        self.assertFalse(result["nautobot_job_profile"])
        self.assertFalse(result["nautobot_job_console_log"])
        self.assertFalse(result["nautobot_job_ignore_singleton_lock"])
        self.assertNotIn("nautobot_job_schedule_id", result)
        self.assertNotIn("soft_time_limit", result)
        self.assertNotIn("time_limit", result)

    def test_time_limits_omitted_when_none(self):
        options = EnqueueOptions(soft_time_limit=None, time_limit=None)
        result = _build_celery_kwargs_dict(options)
        self.assertNotIn("soft_time_limit", result)
        self.assertNotIn("time_limit", result)

    def test_time_limits_included_when_set(self):
        options = EnqueueOptions(soft_time_limit=10.0, time_limit=20.0)
        result = _build_celery_kwargs_dict(options)
        self.assertEqual(result["soft_time_limit"], 10.0)
        self.assertEqual(result["time_limit"], 20.0)

    def test_schedule_id_is_passed_as_raw_uuid(self):
        # Matches the original behavior; NautobotDatabaseScheduler also sets
        # this key as a raw UUID, not a string.
        schedule_id = uuid4()
        options = EnqueueOptions(schedule_id=schedule_id)
        result = _build_celery_kwargs_dict(options)
        self.assertEqual(result["nautobot_job_schedule_id"], schedule_id)
        self.assertIsInstance(result["nautobot_job_schedule_id"], UUID)

    def test_extra_overrides_defaults(self):
        # The original code allowed caller-supplied celery_kwargs to override
        # keys like 'queue'. Preserve that behavior via EnqueueOptions.extra.
        options = EnqueueOptions(queue="default", extra={"queue": "override"})
        result = _build_celery_kwargs_dict(options)
        self.assertEqual(result["queue"], "override")

    def test_extra_can_add_unknown_keys(self):
        options = EnqueueOptions(extra={"custom_celery_arg": "foo"})
        result = _build_celery_kwargs_dict(options)
        self.assertEqual(result["custom_celery_arg"], "foo")


class CeleryBackendDispatchTests(SimpleTestCase):
    """Verify the backend calls into Celery's apply_async with the right shape.

    Heavier end-to-end tests live in nautobot.extras.tests.test_jobs.
    """

    def test_enqueue_calls_run_job_apply_async(self):
        backend = CeleryBackend()
        job_result_id = uuid4()
        options = EnqueueOptions(queue="default", user_id=uuid4(), job_model_id=uuid4())

        with mock.patch("nautobot.extras.jobs.run_job") as mock_run_job:
            result = backend.enqueue(
                job_result_id=job_result_id,
                job_class_path="dummy.module.DummyJob",
                args=[],
                kwargs={"foo": "bar"},
                options=options,
            )

        mock_run_job.apply_async.assert_called_once()
        call_kwargs = mock_run_job.apply_async.call_args.kwargs
        self.assertEqual(call_kwargs["task_id"], str(job_result_id))
        self.assertEqual(call_kwargs["kwargs"], {"foo": "bar"})
        self.assertEqual(call_kwargs["args"], ["dummy.module.DummyJob"])
        self.assertEqual(call_kwargs["queue"], "default")
        self.assertEqual(result.task_id, job_result_id)
        self.assertEqual(result.backend, "celery")

    def test_enqueue_console_log_routes_to_console_log_task(self):
        backend = CeleryBackend()
        options = EnqueueOptions(console_log=True, user_id=uuid4(), job_model_id=uuid4())

        with mock.patch(
            "nautobot.extras.jobs.run_console_log_job_and_return_job_result"
        ) as mock_console_task, mock.patch("nautobot.extras.jobs.run_job") as mock_run_job:
            backend.enqueue(
                job_result_id=uuid4(),
                job_class_path="dummy.module.DummyJob",
                args=[],
                kwargs={},
                options=options,
            )

        mock_console_task.apply_async.assert_called_once()
        mock_run_job.apply_async.assert_not_called()
