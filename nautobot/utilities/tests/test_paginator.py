"""Test the nautobot.utilities.paginator module."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory, override_settings
from django.urls import reverse

from constance.test import override_config

from nautobot.circuits.models import Provider
from nautobot.dcim.models import Manufacturer, Site
from nautobot.utilities.paginator import get_paginate_count
from nautobot.utilities.testing import TestCase


class PaginatorTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create(username="User 1", is_active=True)
        self.request_factory = RequestFactory()
        self.request = self.request_factory.get("some_paginated_view")
        self.request.user = self.user

    @override_config(PAGINATE_COUNT=100)
    def test_get_paginate_count_config(self):
        """Get the default paginate count from Constance config."""
        del settings.PAGINATE_COUNT
        self.assertEqual(get_paginate_count(self.request), 100)

    @override_settings(PAGINATE_COUNT=50)
    @override_config(PAGINATE_COUNT=100)
    def test_get_paginate_count_settings(self):
        """Get the default paginate count from Django settings, overriding Constance config."""
        self.assertEqual(get_paginate_count(self.request), 50)

    @override_settings(PAGINATE_COUNT=50)
    @override_config(PAGINATE_COUNT=100)
    def test_get_paginate_count_user_config(self):
        """Get the user's configured paginate count, overriding global defaults."""
        self.user.set_config("pagination.per_page", 200, commit=True)
        self.assertEqual(get_paginate_count(self.request), 200)

    @override_settings(PAGINATE_COUNT=50)
    @override_config(PAGINATE_COUNT=100)
    def test_get_paginate_count_request_params(self):
        """Get the paginate count from the request's GET params, overriding user and global default values."""
        self.user.set_config("pagination.per_page", 200, commit=True)
        request = self.request_factory.get("some_paginated_view", {"per_page": 400})
        request.user = self.user
        self.assertEqual(get_paginate_count(request), 400)

    @override_settings(MAX_PAGE_SIZE=10)
    @override_settings(PAGINATE_COUNT=50)
    def test_enforce_max_page_size(self):
        """Request an object list view and assert that the MAX_PAGE_SIZE setting is enforced"""
        Site.objects.bulk_create([Site(name=f"TestSite{x}") for x in range(20)])
        providers = (Provider(name=f"p-{x}", slug=f"p-{x}") for x in range(20))
        Provider.objects.bulk_create(providers)
        url = reverse("dcim:site_list")
        self.add_permissions("dcim.view_site")
        self.add_permissions("circuits.view_provider")
        self.client.force_login(self.user)
        with self.subTest("query parameter per_page=20 returns 10 rows"):
            response = self.client.get(url, {"per_page": 20})
            self.assertHttpStatus(response, 200)
            self.assertEqual(response.context["paginator"].per_page, 10)
            self.assertEqual(len(response.context["table"].page), 10)
            warning_message = (
                "Requested &quot;per_page&quot; is too large. No more than 10 items may be displayed at a time."
            )
            self.assertIn(warning_message, response.content.decode(response.charset))
        with self.subTest("query parameter per_page=5 returns 5 rows"):
            response = self.client.get(url, {"per_page": 5})
            self.assertHttpStatus(response, 200)
            self.assertEqual(response.context["paginator"].per_page, 5)
            self.assertEqual(len(response.context["table"].page), 5)
        with self.subTest("user config per_page=200 returns 10 rows"):
            self.user.set_config("pagination.per_page", 200, commit=True)
            response = self.client.get(url)
            self.assertHttpStatus(response, 200)
            self.assertEqual(response.context["paginator"].per_page, 10)
            self.assertEqual(len(response.context["table"].page), 10)
        with self.subTest("global config PAGINATE_COUNT=50 returns 10 rows"):
            self.user.clear_config("pagination.per_page", commit=True)
            # Asserting `max_page` restriction on `NautobotUIViewSet`.
            response = self.client.get(reverse("circuits:provider_list"))
            self.assertHttpStatus(response, 200)
            self.assertEqual(response.context["paginator"].per_page, 10)
            self.assertEqual(len(response.context["table"].page), 10)
            warning_message = (
                "Requested &quot;per_page&quot; is too large. No more than 10 items may be displayed at a time."
            )
            self.assertIn(warning_message, response.content.decode(response.charset).replace("\n", ""))

    @override_settings(MAX_PAGE_SIZE=0)
    def test_error_warning_not_shown_when_max_page_size_is_0(self):
        """Assert max page size warning is not shown when max page size is 0"""
        providers = (Provider(name=f"p-{x}", slug=f"p-{x}") for x in range(20))
        Provider.objects.bulk_create(providers)
        manufacturers = (Manufacturer(name=f"p-{x}", slug=f"p-{x}") for x in range(20))
        Manufacturer.objects.bulk_create(manufacturers)
        self.add_permissions("circuits.view_provider")
        self.add_permissions("dcim.view_manufacturer")
        self.client.force_login(self.user)

        # Test on both default views and NautobotUIViewset views
        urls = [reverse("dcim:manufacturer_list"), reverse("circuits:provider_list")]
        for url in urls:
            response = self.client.get(url, {"per_page": 20})
            self.assertHttpStatus(response, 200)
            self.assertEqual(response.context["paginator"].per_page, 20)
            self.assertEqual(len(response.context["table"].page), 20)
            warning_message = "Requested &quot;per_page&quot; is too large."
            self.assertNotIn(warning_message, response.content.decode(response.charset))
