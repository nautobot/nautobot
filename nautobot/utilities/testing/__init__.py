import time

from celery.contrib.testing.worker import start_worker
from django.test import tag, TransactionTestCase as _TransactionTestCase

from nautobot.core.celery import app

from .api import *
from .utils import *
from .views import *


@tag("unit")
class TransactionTestCase(_TransactionTestCase):
    """
    Base test case class using the TransactionTestCase for unit testing
    """


class CeleryTestCase(TransactionTestCase):
    """
    Test class that provides a running Celery worker for the duration of the test case
    """

    @classmethod
    def setUpClass(cls):
        """Start a celery worker"""
        super().setUpClass()
        # Special namespace loading of methods needed by start_worker, per the celery docs
        app.loader.import_module("celery.contrib.testing.tasks")
        cls.clear_worker()
        cls.celery_worker = start_worker(app, concurrency=1)
        cls.celery_worker.__enter__()

    @classmethod
    def tearDownClass(cls):
        """Stop the celery worker"""
        super().tearDownClass()
        cls.celery_worker.__exit__(None, None, None)

    @staticmethod
    def clear_worker():
        """Purge any running or queued tasks"""
        app.control.purge()

    @classmethod
    def wait_on_active_tasks(cls):
        """Wait on all active tasks to finish before returning"""
        # TODO(john): admittedly, this is not great, but it seems the standard
        # celery APIs for inspecting the worker, looping through all active tasks,
        # and calling `.get()` on them is not working when the worker is in solo mode.
        # Needs more investigation and until then, these tasks run very quickly, so
        # simply delaying the test execution provides enough time for them to complete.
        time.sleep(1)
