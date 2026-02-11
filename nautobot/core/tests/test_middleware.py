from copy import deepcopy
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings

from nautobot.core.settings_funcs import setup_structlog_logging
from nautobot.core.testing import TestCase

override_middleware = deepcopy(settings.MIDDLEWARE)
django_structlog_middleware = "django_structlog.middlewares.RequestMiddleware"
try:
    index_of_prometheus_after_middleware = override_middleware.index(
        "django_prometheus.middleware.PrometheusAfterMiddleware"
    )
    override_middleware.insert(index_of_prometheus_after_middleware, django_structlog_middleware)
except ValueError:
    override_middleware.append(django_structlog_middleware)


class MiddlewareTestCase(TestCase):
    @override_settings(
        _TESTING_STRUCTLOG=True,
        DEBUG=False,
        MIDDLEWARE=override_middleware,
        # LOGGING=deepcopy(settings.LOGGING),
        INSTALLED_APPS=deepcopy(settings.INSTALLED_APPS),
    )
    def test_exception_handling_middleware(self):
        """Test that stack traces are also included for API view 500s.

        Note that a better test would probably be to assert the actual log output to be there, but this poses problems:
        - Colored output would need to be disabled or the ANSI codes stripped
        - The log message did not seem to output when I tried to reproduce this, I assume something about the way
          the structlog middleware is implemented is interfering
        """
        setup_structlog_logging(
            settings.LOGGING,
            settings.INSTALLED_APPS,
            settings.MIDDLEWARE,
        )
        with patch("nautobot.core.middleware.bind_extra_request_failed_metadata") as signal:
            result = self.client.get("/api/plugins/example-app/error/")
        # This assertion makes sure we actually got a HTTP 500 return code. This should be guaranteed, as the view
        # in question is incapable of doing anything else.
        self.assertEqual(result.status_code, 500)
        # This is the assertion that is actually testing our behaviour
        signal.send.assert_called()
