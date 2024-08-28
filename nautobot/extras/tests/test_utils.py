from unittest import mock

from nautobot.core.testing import TestCase
from nautobot.extras.registry import registry
from nautobot.extras.utils import get_celery_queues, get_worker_count, populate_model_features_registry


class UtilsTestCase(TestCase):
    @mock.patch("celery.app.control.Inspect.active_queues")
    def test_get_celery_queues(self, mock_active_queues):
        with self.subTest("No queues"):
            mock_active_queues.return_value = None
            self.assertDictEqual(get_celery_queues(), {})

        with self.subTest("1 worker 1 queue"):
            mock_active_queues.return_value = {"celery@worker": [{"name": "queue1"}]}
            self.assertDictEqual(get_celery_queues(), {"queue1": 1})

        with self.subTest("2 workers 2 shared queues"):
            mock_active_queues.return_value = {
                "celery@worker1": [{"name": "queue1"}, {"name": "queue2"}],
                "celery@worker2": [{"name": "queue1"}, {"name": "queue2"}],
            }
            self.assertDictEqual(get_celery_queues(), {"queue1": 2, "queue2": 2})

        with self.subTest("2 workers 2 individual queues"):
            mock_active_queues.return_value = {
                "celery@worker1": [{"name": "queue1"}],
                "celery@worker2": [{"name": "queue2"}],
            }
            self.assertDictEqual(get_celery_queues(), {"queue1": 1, "queue2": 1})

        with self.subTest("2 workers 3 queues"):
            mock_active_queues.return_value = {
                "celery@worker1": [{"name": "queue1"}, {"name": "queue3"}],
                "celery@worker2": [{"name": "queue2"}],
            }
            self.assertDictEqual(get_celery_queues(), {"queue1": 1, "queue2": 1, "queue3": 1})

    @mock.patch("nautobot.extras.utils.get_celery_queues")
    def test_get_worker_count(self, mock_get_celery_queues):
        mock_get_celery_queues.return_value = {"default": 12, "priority": 2, "bulk": 4, "nobody": 0}
        with self.subTest("Nonexistent queue"):
            self.assertEqual(get_worker_count(queue="invalid"), 0)
        with self.subTest("Default queue"):
            self.assertEqual(get_worker_count(), 12)
        with self.subTest("Bulk queue"):
            self.assertEqual(get_worker_count(queue="bulk"), 4)
        with self.subTest("Empty queue"):
            self.assertEqual(get_worker_count(queue="nobody"), 0)

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
