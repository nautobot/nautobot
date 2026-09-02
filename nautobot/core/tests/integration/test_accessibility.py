"""
Accessibility regression tests: axe-core against representative pages rather than every view.

`base_django.html`, `generic/object_list.html`, `generic/object_retrieve.html` and `generic/object_create_base.html`
back most of the UI, so a regression in shared markup surfaces here whichever model introduced it. That holds for page
furniture only -- overridden blocks, self-rendering columns and per-template `extra_styles` are invisible to a
single-model scan, which is what `test_core_list_views` covers.
"""

from django.apps import apps
from django.urls import NoReverseMatch, reverse

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.core.utils.lookup import get_route_for_model
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.models import Status


class AccessibilityTestCase(SeleniumTestCase):
    """Assert that Nautobot's shared pages have no axe-core violations."""

    def setUp(self):
        super().setUp()
        self.login_as_superuser()

        self.status = Status.objects.get_for_model(Location).first()

        # A parent/child pair, not a single object: the tree caret and "filter to descendants" link render only for rows
        # with children (`{% if children_exists %}` in `dcim/tables/template_code.py`), so a flat list skips them.
        self.location_type = LocationType.objects.create(name="A11y Test Site")
        self.child_location_type = LocationType.objects.create(name="A11y Test Building", parent=self.location_type)
        self.location = Location.objects.create(
            name="A11y Test Location",
            location_type=self.location_type,
            status=self.status,
        )
        self.child_location = Location.objects.create(
            name="A11y Test Child Location",
            location_type=self.child_location_type,
            parent=self.location,
            status=self.status,
        )

    def test_home_page(self):
        self.browser.visit(self.live_server_url)
        self.assertTrue(self.browser.is_element_present_by_css("#draggable-homepage-panels", wait_time=10))
        self.assertNoAccessibilityViolations()

    def test_core_list_views(self):
        """Cover markup each view adds to the shared template. Not a substitute for an App scanning its own views."""
        paths = set()
        for model in apps.get_models():
            route = get_route_for_model(model, "list")
            # App routes are named `plugins:...`; skip them, this test covers core views only.
            if route.startswith("plugins:"):
                continue
            try:
                paths.add(reverse(route))
            except NoReverseMatch:
                continue

        # If the lookup above breaks, it would leave this test passing over an empty set of paths.
        self.assertGreater(len(paths), 100)

        for path in sorted(paths):
            with self.subTest(path=path):
                self.browser.visit(f"{self.live_server_url}{path}")
                self.assertTrue(self.browser.is_element_present_by_tag("main", wait_time=10))
                self.assertNoAccessibilityViolations()

    def test_object_list_view(self):
        self.browser.visit(f"{self.live_server_url}/dcim/locations/")
        self.assertTrue(self.browser.is_element_present_by_css("#object_list_form", wait_time=10))
        self.assertNoAccessibilityViolations()

    def test_object_detail_view(self):
        self.browser.visit(f"{self.live_server_url}{self.location.get_absolute_url()}")
        self.assertTrue(self.browser.is_element_present_by_tag("main", wait_time=10))
        self.assertNoAccessibilityViolations()

    def test_object_edit_view(self):
        self.browser.visit(f"{self.live_server_url}/dcim/locations/add/")
        self.assertTrue(self.browser.is_element_present_by_css("form", wait_time=10))
        self.assertNoAccessibilityViolations()

    def test_object_edit_view_with_validation_errors(self):
        """
        Scan the error state, where `aria-invalid` and the `aria-describedby` wiring for error lists have to hold up.

        `required` is stripped so the browser will submit and the server can reject.
        """
        self.browser.visit(f"{self.live_server_url}/dcim/locations/add/")
        self.assertTrue(self.browser.is_element_present_by_css("form", wait_time=10))
        self.browser.execute_script(
            "document.querySelectorAll('[required]').forEach((element) => element.removeAttribute('required'));"
        )
        self.browser.find_by_xpath("//button[@name='_create']").first.click()
        self.assertTrue(self.browser.is_element_present_by_css("[aria-invalid='true']", wait_time=10))
        self.assertNoAccessibilityViolations()

    def test_search_page(self):
        self.browser.visit(f"{self.live_server_url}/search/?q=A11y")
        self.assertTrue(self.browser.is_element_present_by_tag("main", wait_time=10))
        self.assertNoAccessibilityViolations()

    def test_login_page(self):
        self.logout()
        self.browser.visit(f"{self.live_server_url}/login/")
        self.assertTrue(self.browser.is_element_present_by_name("username", wait_time=10))
        self.assertNoAccessibilityViolations()
