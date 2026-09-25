from copy import deepcopy
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

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
        LOGGING=deepcopy(settings.LOGGING),
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


class HtmxLoginRedirectMiddlewareTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("circuits:provider_list")
        self.login_url = reverse("login")

    def assertHxRedirect(self, response, next_url):
        self.assertEqual(response.status_code, 204)
        redirect = urlsplit(response.headers["HX-Redirect"])
        self.assertEqual(redirect.path, self.login_url)
        self.assertEqual(parse_qs(redirect.query).get("next"), [next_url])

    def test_htmx_request_from_expired_session_redirects_the_window(self):
        self.client.logout()
        response = self.client.get(self.url, headers={"HX-Request": "true"})
        self.assertHxRedirect(response, self.url)

    def test_htmx_redirect_returns_to_the_page_the_user_was_viewing(self):
        self.client.logout()
        response = self.client.get(
            self.url,
            headers={"HX-Request": "true", "HX-Current-URL": "http://nautobot.example.com/dcim/devices/?status=active"},
        )
        self.assertHxRedirect(response, "/dcim/devices/?status=active")

    def test_htmx_redirect_ignores_an_offsite_current_url(self):
        self.client.logout()
        response = self.client.get(
            self.url,
            headers={"HX-Request": "true", "HX-Current-URL": "https://example.com/phishing/"},
        )
        self.assertHxRedirect(response, self.url)

    def test_htmx_redirect_ignores_a_protocol_relative_current_url(self):
        self.client.logout()
        response = self.client.get(
            self.url,
            headers={"HX-Request": "true", "HX-Current-URL": "http://nautobot.example.com//example.com/phishing/"},
        )
        self.assertHxRedirect(response, self.url)

    def test_htmx_redirect_leaves_other_redirects_alone(self):
        response = self.client.get(reverse("logout"), headers={"HX-Request": "true"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("home"))
        self.assertNotIn("HX-Redirect", response.headers)

    def test_non_htmx_request_from_expired_session_still_redirects(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"{self.login_url}?next={self.url}")
        self.assertNotIn("HX-Redirect", response.headers)

    def test_htmx_request_without_permission_is_still_forbidden(self):
        response = self.client.get(self.url, headers={"HX-Request": "true"})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("HX-Redirect", response.headers)
