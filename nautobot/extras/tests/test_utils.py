from unittest import mock
import uuid

from django.core.cache import cache

from nautobot.core.testing import TestCase
from nautobot.dcim.models import Device, LocationType
from nautobot.extras.choices import JobQueueTypeChoices
from nautobot.extras.models import JobQueue
from nautobot.extras.registry import registry
from nautobot.extras.utils import (
    get_base_template,
    get_celery_queues,
    get_worker_count,
    populate_model_features_registry,
)
from nautobot.users.models import Token


class UtilsTestCase(TestCase):
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
