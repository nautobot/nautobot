"""
Accessibility regression tests.

These run axe-core against a handful of representative pages rather than trying to cover every view: the templates
exercised here (`base_django.html`, `generic/object_list.html`, `generic/object_retrieve.html`,
`generic/object_edit.html`) back the overwhelming majority of Nautobot's UI, so a regression in shared markup shows up
here regardless of which model it was introduced against.

All four axe-core impact levels are gated on. Impact describes how badly a violation affects a user, not how important
the criterion is, so it is a poor thing to filter conformance by: a `moderate` finding such as `meta-viewport` is a
genuine WCAG AA failure. The volume at the lower levels is low enough across these pages that there is nothing to gain
from a narrower threshold.
"""

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.models import Status


class AccessibilityTestCase(SeleniumTestCase):
    """Assert that shared page templates have no accessibility violations."""

    def setUp(self):
        super().setUp()
        self.login_as_superuser()

        self.status = Status.objects.get_for_model(Location).first()

        # A parent/child pair, not a single object: the tree expand caret and the "filter to descendants" link only
        # render for rows that have children, so a flat list silently skips that markup entirely.
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
        """
        Scan a list view from each app, not just the one that backs the shared template.

        The premise of the rest of this file -- that shared templates mean one list view stands in for all of them -- is
        true of the page furniture and false of everything a view contributes itself. Templates that override blocks,
        columns that render their own markup, and per-app inline `extra_styles` are all invisible to a single-model scan;
        `/extras/jobs/`, for instance, styles its own rows and can fail 1.4.3 on every link in the table while every
        other page passes.

        These are still list views of the same template, so this is cheap. It is not a substitute for an App scanning its
        own views.
        """
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
        A form re-rendered with validation errors is where `aria-invalid` and the `aria-describedby` wiring for error
        lists have to hold up, so it needs its own scan.

        Required fields carry the HTML5 `required` attribute, so the browser refuses to submit and the server never gets
        the chance to produce errors; `required` is stripped first to force server-side validation.

        Location Type is used rather than Location because an empty submission puts errors on plain scalar fields, which
        is the wiring under test, rather than on the related-object widgets a Location form leads with.
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

    def test_header_search_stays_the_size_of_the_field(self):
        """
        The header search must keep the size and shape of a single-line control, whatever the query length.

        This is a geometry assertion rather than an axe-core one because axe cannot see the problem for what it is: a
        label painting outside its field reports as an *incomplete* `color-contrast` check ("partially obscured by
        another element"), since contrast is indeterminate for whatever part of an element falls outside the ancestor
        painting its background. Nor can markup assertions catch it, since it is only visible as boxes on a screen. So
        assert the boxes -- in both axes.

        Both axes, specifically, because the two failure modes trade off against each other and checking one hides the
        other. The trigger's label sets its own minimum size, so dropping `.text-nowrap` stops it overflowing sideways
        only by letting it wrap, which grows the field downwards instead: an 85-character query takes it from 36px to
        133px over six lines, dragging the header row with it. `.text-truncate` is what resolves both, since the
        `overflow: hidden` it carries also drops a flex item's automatic minimum size to zero. Measuring width alone
        would pass against markup with no truncation at all.
        """
        long_query = "a-very-long-search-query-that-should-not-be-allowed-to-overflow-the-header-search-box"
        measure = """
            const container = document.querySelector('#header_search');
            const trigger = document.querySelector('#header_search_trigger');
            const root = document.documentElement;
            const containerRect = container.getBoundingClientRect();
            const triggerRect = trigger.getBoundingClientRect();
            return {
                escaping_children: [...container.children]
                    .filter((child) => {
                        const rect = child.getBoundingClientRect();
                        return (
                            rect.right > containerRect.right + 1 || rect.left < containerRect.left - 1 ||
                            rect.bottom > containerRect.bottom + 1 || rect.top < containerRect.top - 1
                        );
                    })
                    .map((child) => child.id || child.className),
                container_height: Math.round(containerRect.height),
                container_scroll_width: container.scrollWidth,
                container_client_width: container.clientWidth,
                document_scroll_width: root.scrollWidth,
                document_client_width: root.clientWidth,
                trigger_line_count: Math.round(triggerRect.height / parseFloat(getComputedStyle(trigger).lineHeight)),
            };
        """

        heights = {}
        for label, url in (
            ("no query", f"{self.live_server_url}/dcim/locations/"),
            ("long query", f"{self.live_server_url}/dcim/locations/?q={long_query}"),
        ):
            with self.subTest(query=label):
                self.browser.visit(url)
                self.assertTrue(self.browser.is_element_present_by_css("#header_search_trigger", wait_time=10))
                metrics = self.browser.driver.execute_script(measure)
                heights[label] = metrics["container_height"]

                self.assertEqual(
                    metrics["escaping_children"],
                    [],
                    f"header search children painted outside the field with {label}: {metrics}",
                )
                # `scrollWidth` over `clientWidth` means content the field cannot show without scrolling, and it has no
                # scrollbar -- so anything over is content spilling out of, or clipped by, the visible box.
                self.assertLessEqual(
                    metrics["container_scroll_width"],
                    metrics["container_client_width"],
                    f"header search content overflows the field with {label}: {metrics}",
                )
                # Overflow here widened the whole document, which scrolls the page sideways at any window size.
                self.assertLessEqual(
                    metrics["document_scroll_width"],
                    metrics["document_client_width"],
                    f"page scrolls horizontally with {label}: {metrics}",
                )
                self.assertEqual(
                    metrics["trigger_line_count"],
                    1,
                    f"header search label wrapped onto more than one line with {label}: {metrics}",
                )

        self.assertEqual(
            heights["long query"],
            heights["no query"],
            f"the query being searched for changed the height of the header search: {heights}",
        )

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

    def test_header_search_does_not_open_dialog_on_focus(self):
        """
        Moving focus to the search trigger must not open the search dialog (WCAG 3.2.1 On Focus, Level A).

        No automated checker can find this one -- it needs something to actually take focus and then look at what
        happened. An `<input>` that opens the dialog on `focus` fails the criterion: a keyboard user tabbing through the
        header lands in a modal they had not asked for. Activation, by click or key, is what should open it.
        """
        self.browser.visit(f"{self.live_server_url}/dcim/locations/")
        self.assertTrue(self.browser.is_element_present_by_css("#header_search_trigger", wait_time=10))

        # `search.js` builds `#search_popup` on demand and removes it again on close, so presence is the open state. Check
        # that it also renders, so that a popup left in the DOM but hidden cannot pass for a closed one.
        visible_dialog_probe = """
            const popup = document.getElementById('search_popup');
            return {
                dialog_visible: !!(
                    popup && popup.offsetParent !== null && getComputedStyle(popup).visibility !== 'hidden'
                ),
                focused: document.activeElement ? document.activeElement.id : null,
            };
        """
        after_focus = self.browser.driver.execute_script(
            "document.querySelector('#header_search_trigger').focus();" + visible_dialog_probe
        )
        self.assertFalse(after_focus["dialog_visible"], "focusing the search trigger opened the search dialog")
        self.assertEqual(after_focus["focused"], "header_search_trigger", "focus left the search trigger unbidden")

        self.browser.find_by_css("#header_search_trigger").first.click()
        self.assertTrue(self.browser.is_element_present_by_css("#search_popup", wait_time=10))
        after_click = self.browser.driver.execute_script(visible_dialog_probe)
        self.assertTrue(after_click["dialog_visible"], "activating the search trigger did not open the search dialog")
