"""
Accessibility regression tests: axe-core against representative pages rather than every view.

`base_django.html`, `generic/object_list.html`, `generic/object_retrieve.html` and `generic/object_create_base.html`
back most of the UI, so a regression in shared markup surfaces here whichever model introduced it. That holds for page
furniture only -- overridden blocks, self-rendering columns and per-app `extra_styles` are invisible to a single-model
scan, which is what `test_list_views_across_apps` covers.
"""

from nautobot.core.testing.integration import SeleniumTestCase
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

    def test_list_views_across_apps(self):
        """Cover markup each view adds to the shared template. Not a substitute for an App scanning its own views."""
        for path in (
            "/circuits/circuits/",
            "/cloud/cloud-accounts/",
            "/dcim/devices/",
            "/dcim/interfaces/",
            "/extras/jobs/",
            "/extras/job-results/",
            "/extras/object-changes/",
            "/ipam/ip-addresses/",
            "/ipam/prefixes/",
            "/ipam/vlans/",
            "/tenancy/tenants/",
            "/virtualization/virtual-machines/",
            "/vpn/tunnels/",
            "/wireless/wireless-networks/",
        ):
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

        `required` is stripped so the browser will submit and the server can reject. Location Type rather than Location
        because an empty Location form raises `RelatedObjectDoesNotExist` from `Location.clean()`, which reads
        `self.location_type.parent` unguarded -- a pre-existing bug unrelated to accessibility.
        """
        self.browser.visit(f"{self.live_server_url}/dcim/location-types/add/")
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

    def test_accessibility_assertion_context_is_honoured(self):
        """
        Self-test the `context`/`exclude` plumbing. A malformed axe context makes axe reject and fails loudly, but a
        well-formed selector aimed at the wrong subtree scans the wrong thing and reports nothing. Every call in this
        file passes the default `exclude`, but django-debug-toolbar is absent under the test settings, so nothing else
        checks that it suppresses anything.

        The violation is injected rather than borrowed from the page, so this does not break as the UI improves.
        """
        self.browser.visit(f"{self.live_server_url}/dcim/locations/")
        self.assertTrue(self.browser.is_element_present_by_tag("main", wait_time=10))
        self.browser.execute_script(
            """
            const offender = document.createElement('div');
            offender.id = 'a11y-self-test';
            /* 16px normal weight, so 1.4.3 AA wants 4.5:1; #777 on #888 is about 1.3:1. */
            offender.style.cssText = 'background:#888;color:#777;font-size:16px;padding:8px';
            offender.textContent = 'Deliberately low contrast text for the harness self-test';
            document.querySelector('main').append(offender);
            """
        )

        with self.assertRaises(AssertionError) as failure:
            self.assertNoAccessibilityViolations()
        self.assertIn("color-contrast", str(failure.exception))

        self.assertNoAccessibilityViolations(exclude=("#a11y-self-test",))

        self.assertNoAccessibilityViolations(context="header")
        with self.assertRaises(AssertionError):
            self.assertNoAccessibilityViolations(context="main")

        # `AXE_EXCLUDE_SELECTORS` has to exclude the whole subtree, since django-debug-toolbar reports against elements
        # nested inside `#djDebugRoot`. Rebuild that shape here, as the toolbar itself is absent under test settings.
        self.browser.execute_script(
            """
            const offender = document.getElementById('a11y-self-test');
            const toolbar = document.createElement('div');
            toolbar.id = 'djDebugRoot';
            document.querySelector('main').append(toolbar);
            toolbar.append(offender);
            """
        )
        self.assertNoAccessibilityViolations()
