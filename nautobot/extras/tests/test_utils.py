from unittest import mock
import uuid

from django.core.cache import cache
from django.test import override_settings

from nautobot.core.testing import TestCase
from nautobot.dcim.models import Device, LocationType
from nautobot.extras.choices import JobQueueTypeChoices
from nautobot.extras.models import JobQueue, JobResult
from nautobot.extras.registry import registry
from nautobot.extras.utils import (
    get_base_template,
    get_celery_queues,
    get_worker_count,
    populate_model_features_registry,
    run_kubernetes_job_and_return_job_result,
)
from nautobot.users.models import Token


class UtilsTestCase(TestCase):
    databases = ("default", "job_logs")

    def test_get_base_template(self):
        with self.subTest("explicitly specified base_template always wins"):
            self.assertEqual(get_base_template("dcim/device/base.html", Device), "dcim/device/base.html")

        with self.subTest("<model>.html wins over <model>_retrieve.html"):
            # TODO: why do we even have both locationtype.html and locationtype_retrieve.html?
            self.assertEqual(get_base_template(None, LocationType), "dcim/locationtype.html")

        with self.subTest("<model>_retrieve.html is used if present"):
            self.assertEqual(get_base_template(None, JobQueue), "extras/jobqueue_retrieve.html")

        with self.subTest("generic/object_retrieve.html is used as a fallback"):
            self.assertEqual(get_base_template(None, Token), "generic/object_retrieve.html")

    @mock.patch("celery.app.control.Inspect.active_queues")
    def test_get_celery_queues(self, mock_active_queues):
        with self.subTest("No queues"):
            mock_active_queues.return_value = None
            self.assertDictEqual(get_celery_queues(), {})

        with self.subTest("1 worker 1 queue"):
            mock_active_queues.return_value = {"celery@worker": [{"name": "queue1"}]}
            self.assertDictEqual(get_celery_queues(), {"queue1": 1})

        with self.subTest("2 workers 2 shared queues"):
            cache.clear()
            mock_active_queues.return_value = {
                "celery@worker1": [{"name": "queue1"}, {"name": "queue2"}],
                "celery@worker2": [{"name": "queue1"}, {"name": "queue2"}],
            }
            self.assertDictEqual(get_celery_queues(), {"queue1": 2, "queue2": 2})

        with self.subTest("2 workers 2 individual queues"):
            cache.clear()
            mock_active_queues.return_value = {
                "celery@worker1": [{"name": "queue1"}],
                "celery@worker2": [{"name": "queue2"}],
            }
            self.assertDictEqual(get_celery_queues(), {"queue1": 1, "queue2": 1})

        with self.subTest("2 workers 3 queues"):
            cache.clear()
            mock_active_queues.return_value = {
                "celery@worker1": [{"name": "queue1"}, {"name": "queue3"}],
                "celery@worker2": [{"name": "queue2"}],
            }
            self.assertDictEqual(get_celery_queues(), {"queue1": 1, "queue2": 1, "queue3": 1})

    @mock.patch("nautobot.extras.utils.get_celery_queues")
    def test_get_worker_count(self, mock_get_celery_queues):
        mock_get_celery_queues.return_value = {"default": 12, "priority": 2, "bulk": 4, "nobody": 0}
        JobQueue.objects.get_or_create(name="default", defaults={"queue_type": JobQueueTypeChoices.TYPE_CELERY})
        priority_job_queue, _ = JobQueue.objects.get_or_create(
            name="priority", defaults={"queue_type": JobQueueTypeChoices.TYPE_CELERY}
        )
        bulk_job_queue, _ = JobQueue.objects.get_or_create(
            name="bulk", defaults={"queue_type": JobQueueTypeChoices.TYPE_CELERY}
        )
        empty_job_queue, _ = JobQueue.objects.get_or_create(
            name="nobody", defaults={"queue_type": JobQueueTypeChoices.TYPE_CELERY}
        )
        with self.subTest("Nonexistent queue"):
            self.assertEqual(get_worker_count(queue="invalid"), 0)
        with self.subTest("Default queue"):
            self.assertEqual(get_worker_count(), 12)
        with self.subTest("Priority queue"):
            self.assertEqual(get_worker_count(queue=priority_job_queue.name), 2)
        with self.subTest("Bulk queue"):
            self.assertEqual(get_worker_count(queue=bulk_job_queue.name), 4)
        with self.subTest("Empty queue"):
            self.assertEqual(get_worker_count(queue=empty_job_queue.name), 0)
        with self.subTest("Passing a job queue instance"):
            self.assertEqual(get_worker_count(queue=bulk_job_queue), 4)
        with self.subTest("Passing a job queue pk"):
            self.assertEqual(get_worker_count(queue=str(bulk_job_queue.pk)), 4)
        with self.subTest("Passing a random uuid"):
            self.assertEqual(get_worker_count(queue=str(uuid.uuid4())), 0)

    def test_populate_model_features_registry(self):
        original_custom_fields_registry = registry["model_features"]["custom_fields"].copy()

        self.assertIn(
            "circuit", registry["model_features"]["custom_fields"]["circuits"], "Registry should already be populated"
        )

        populate_model_features_registry()
        self.assertDictEqual(
            registry["model_features"]["custom_fields"],
            original_custom_fields_registry,
            "Registry should not be modified if refresh flag not set",
        )

        registry["model_features"]["custom_fields"].pop("circuits")
        self.assertNotEqual(
            registry["model_features"]["custom_fields"],
            original_custom_fields_registry,
            "Registry should be successfully modified",
        )

        # Make sure we return to the original state
        populate_model_features_registry(refresh=True)
        self.assertDictEqual(
            registry["model_features"]["custom_fields"],
            original_custom_fields_registry,
            "Registry should be restored to original state",
        )

    @override_settings(
        KUBERNETES_JOB_POD_NAME="test-pod",
        KUBERNETES_JOB_POD_NAMESPACE="test-namespace",
        KUBERNETES_JOB_MANIFEST={
            "metadata": {"name": "test-job"},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "command": [],
                            }
                        ]
                    }
                }
            },
        },
        KUBERNETES_SSL_CA_CERT_PATH="/path/to/ca.crt",
        KUBERNETES_TOKEN_PATH="/path/to/token",  # noqa: S106
        KUBERNETES_DEFAULT_SERVICE_ADDRESS="https://kubernetes.default.svc",
    )
    @mock.patch("nautobot.extras.utils.transaction.on_commit")
    @mock.patch("builtins.open", new_callable=mock.mock_open, read_data="test-token\n")
    @mock.patch("nautobot.extras.utils.kubernetes.client.BatchV1Api")
    @mock.patch("nautobot.extras.utils.kubernetes.client.ApiClient")
    @mock.patch("nautobot.extras.utils.kubernetes.client.Configuration")
    def test_run_kubernetes_job_and_return_job_result(
        self,
        mock_configuration,
        mock_api_client,
        mock_batch_api,
        mock_open,
        mock_on_commit,
    ):
        """Test run_kubernetes_job_and_return_job_result function."""
        # Setup test data
        job_result = JobResult.objects.create(
            name="Test Job",
            user=self.user,
        )
        # Mock the log method to avoid database writes during test
        job_result.log = mock.Mock()
        job_kwargs = '{"key": "value"}'

        # Setup kubernetes client mocks
        mock_config_instance = mock.MagicMock()
        mock_config_instance.api_key_prefix = {}
        mock_config_instance.api_key = {}
        mock_configuration.return_value = mock_config_instance

        mock_api_client_instance = mock.Mock()
        mock_api_client.return_value.__enter__.return_value = mock_api_client_instance
        mock_api_client.return_value.__exit__.return_value = None

        mock_api_instance = mock.Mock()
        mock_batch_api.return_value = mock_api_instance

        # Capture the callback passed to transaction.on_commit
        commit_callback = None

        def capture_callback(callback):
            nonlocal commit_callback
            commit_callback = callback
            # Execute immediately for testing
            callback()

        mock_on_commit.side_effect = capture_callback

        # Execute the function
        result = run_kubernetes_job_and_return_job_result(job_result, job_kwargs)

        # Verify job_result was updated and saved
        job_result.refresh_from_db()
        self.assertEqual(job_result.task_kwargs, job_kwargs)
        self.assertEqual(result, job_result)

        # Verify transaction.on_commit was called
        mock_on_commit.assert_called_once()
        self.assertIsNotNone(commit_callback)

        # Verify kubernetes configuration was set up correctly
        mock_configuration.assert_called_once()
        self.assertEqual(mock_config_instance.host, "https://kubernetes.default.svc")
        self.assertEqual(mock_config_instance.ssl_ca_cert, "/path/to/ca.crt")
        self.assertEqual(mock_config_instance.api_key_prefix["authorization"], "Bearer")
        self.assertEqual(mock_config_instance.api_key["authorization"], "test-token")

        # Verify ApiClient was used as context manager
        mock_api_client.assert_called_once_with(mock_config_instance)

        # Verify BatchV1Api was created with the api_client_instance
        mock_batch_api.assert_called_once_with(mock_api_client_instance)

        # Verify the pod manifest was modified correctly
        mock_api_instance.create_namespaced_job.assert_called_once()
        create_call = mock_api_instance.create_namespaced_job.call_args
        body = create_call[1]["body"]
        self.assertEqual(body["metadata"]["name"], f"nautobot-job-{job_result.pk}")
        self.assertEqual(
            body["spec"]["template"]["spec"]["containers"][0]["command"],
            ["nautobot-server", "runjob_with_job_result", str(job_result.pk)],
        )
        self.assertEqual(create_call[1]["namespace"], "test-namespace")

        # Verify token file was opened
        mock_open.assert_called_once_with("/path/to/token", "r", encoding="utf-8")

        # Verify job_result.log was called (checking for log messages)
        self.assertEqual(job_result.log.call_count, 1)
        self.assertIn("Creating job pod", str(job_result.log.call_args_list[0]))
