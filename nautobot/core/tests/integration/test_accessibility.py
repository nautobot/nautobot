"""
Accessibility regression tests.

These run axe-core against a handful of representative pages rather than trying to cover every view: the templates
exercised here (`base_django.html`, `generic/object_list.html`, `generic/object_retrieve.html`,
`generic/object_edit.html`) back the overwhelming majority of Nautobot's UI, so a regression in shared markup shows up
here regardless of which model it was introduced against.

All four axe-core impact levels are gated on. An earlier version gated only `critical` and `serious`, assuming
lower-impact findings would be too numerous; an audit across these pages found exactly one, and it was a genuine WCAG AA
failure (`meta-viewport`) that the threshold had been hiding on every page. Impact describes how badly a violation
affects a user, not how important the criterion is, so it is a poor thing to filter conformance by.
"""

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.models import Status


class AccessibilityTestCase(SeleniumTestCase):
    """Assert that shared page templates have no critical or serious accessibility violations."""

    def setUp(self):
        super().setUp()
        self.login_as_superuser()

        self.status = Status.objects.get_for_model(Location).first()

        # A parent/child pair, not a single object: the tree expand caret and the "filter to descendants" link only
        # render for rows that have children, and scanning a flat list silently skips that markup entirely. Two real
        # violations in it went unnoticed because the original fixture had no hierarchy.
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
        A form re-rendered with validation errors is where `aria-invalid` and the `aria-describedby` wiring for error
        lists have to hold up, so it needs its own scan.

        Required fields carry the HTML5 `required` attribute, so the browser refuses to submit and the server never gets
        the chance to produce errors; `required` is stripped first to force server-side validation.

        This uses Location Type rather than Location deliberately. Submitting an empty Location form currently raises
        `RelatedObjectDoesNotExist` from `Location.clean()`, which reads `self.location_type.parent` without checking
        that `location_type` was supplied -- a pre-existing bug unrelated to accessibility.
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
        Exercise the `context` and `exclude` plumbing in `assertNoAccessibilityViolations` itself.

        These build an axe context object rather than passing `document`, and axe rejects a malformed one, so a mistake
        here would not fail loudly -- it would quietly scan the wrong part of the page and report nothing. The default
        `exclude` covers django-debug-toolbar, which is absent under the test settings, so nothing in the suite as it
        stands would exercise the argument at all.

        Inject a deliberate contrast failure to check against, rather than relying on a real one: real violations are
        what the rest of this file exists to remove, so any test depending on one is a test that breaks when the code
        gets better.
        """
        self.browser.visit(f"{self.live_server_url}/dcim/locations/")
        self.assertTrue(self.browser.is_element_present_by_tag("main", wait_time=10))
        self.browser.execute_script(
            """
            const offender = document.createElement('div');
            offender.id = 'a11y-self-test';
            /* #777 on #888: 1.2:1, far below the 4.5:1 of 1.4.3 AA, and large enough not to be skipped as decorative. */
            offender.style.cssText = 'background:#888;color:#777;font-size:16px;padding:8px';
            offender.textContent = 'Deliberately low contrast text for the harness self-test';
            document.querySelector('main').append(offender);
            """
        )

        with self.assertRaises(AssertionError) as failure:
            self.assertNoAccessibilityViolations()
        self.assertIn("color-contrast", str(failure.exception))

        # Excluded, the same page passes -- so `exclude` reaches axe and narrows what it reports.
        self.assertNoAccessibilityViolations(exclude=("#a11y-self-test",))

        # And `context` still limits the scan, rather than being ignored now that it is wrapped in a context object.
        self.assertNoAccessibilityViolations(context="header")
        with self.assertRaises(AssertionError):
            self.assertNoAccessibilityViolations(context="main")

        # The default exclusion has to cover a subtree, not just the element named: django-debug-toolbar reports against
        # elements nested inside `#djDebugRoot`, such as the `#djShowToolBarJ` span in its collapsed handle. Stand the
        # shape of it up here, since the toolbar itself is not installed under the test settings.
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
