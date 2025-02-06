"""Test the nautobot.core.utils.paginator module."""

from constance.test import override_config
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings, RequestFactory
from django.urls import reverse

from nautobot.circuits import models as circuits_models
from nautobot.core import testing
from nautobot.core.testing.utils import extract_page_body
from nautobot.core.views import paginator
from nautobot.dcim import models as dcim_models
from nautobot.extras import models as extras_models


class PaginatorTestCase(testing.TestCase):
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
        self.assertEqual(paginator.get_paginate_count(self.request), 100)

    @override_settings(PAGINATE_COUNT=50)
    @override_config(PAGINATE_COUNT=100)
    def test_get_paginate_count_settings(self):
        """Get the default paginate count from Django settings, overriding Constance config."""
        self.assertEqual(paginator.get_paginate_count(self.request), 50)

    @override_settings(PAGINATE_COUNT=50)
    @override_config(PAGINATE_COUNT=100)
    def test_get_paginate_count_user_config(self):
        """Get the user's configured paginate count, overriding global defaults."""
        self.user.set_config("pagination.per_page", 200, commit=True)
        self.assertEqual(paginator.get_paginate_count(self.request), 200)

    @override_settings(PAGINATE_COUNT=50)
    @override_config(PAGINATE_COUNT=100)
    def test_get_paginate_count_request_params(self):
        """Get the paginate count from the request's GET params, overriding user and global default values."""
        self.user.set_config("pagination.per_page", 200, commit=True)
        request = self.request_factory.get("some_paginated_view", {"per_page": 400})
        request.user = self.user
        self.assertEqual(paginator.get_paginate_count(request), 400)

    @override_settings(MAX_PAGE_SIZE=10)
    @override_settings(PAGINATE_COUNT=50)
    def test_enforce_max_page_size(self):
        """Request an object list view and assert that the MAX_PAGE_SIZE setting is enforced"""
        location_type = dcim_models.LocationType.objects.get(name="Campus")
        status = extras_models.Status.objects.get_for_model(dcim_models.Location).first()
        dcim_models.Location.objects.bulk_create(
            [
                dcim_models.Location(name=f"TestLocation{x}", location_type=location_type, status=status)
                for x in range(20)
            ]
        )
        url = reverse("dcim:location_list")
        self.add_permissions("dcim.view_location")
        providers = (circuits_models.Provider(name=f"p-{x}") for x in range(20))
        circuits_models.Provider.objects.bulk_create(providers)
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
            self.assertIn(warning_message, extract_page_body(response.content.decode(response.charset)))
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
            self.assertIn(warning_message, extract_page_body(response.content.decode(response.charset)))

    @override_settings(MAX_PAGE_SIZE=0)
    def test_error_warning_not_shown_when_max_page_size_is_0(self):
        """Assert max page size warning is not shown when max page size is 0"""
        providers = (circuits_models.Provider(name=f"p-{x}") for x in range(20))
        circuits_models.Provider.objects.bulk_create(providers)
        manufacturers = (dcim_models.Manufacturer(name=f"p-{x}") for x in range(20))
        dcim_models.Manufacturer.objects.bulk_create(manufacturers)
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
            self.assertNotIn(warning_message, extract_page_body(response.content.decode(response.charset)))
