from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import tag
from django.utils import timezone
from selenium.webdriver.common.keys import Keys

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.models import Manufacturer
from nautobot.extras.models import ObjectLock
from nautobot.users.models import ObjectPermission

User = get_user_model()


@tag("integration")
class ObjectLockAffordanceTestCase(SeleniumTestCase):
    def setUp(self):
        super().setUp()
        self.ct = ContentType.objects.get_for_model(Manufacturer)
        self.manufacturer = Manufacturer.objects.create(name="AffordanceMfr")
        # Grant the test user permission to view manufacturers, view locks, and release own locks.
        # The lock blocks both update and delete; grant change + delete on the manufacturer so both
        # blocked affordances render (each control is gated on the matching object permission).
        for action, ct_kwargs in [
            ("view", {"app_label": "dcim", "model": "manufacturer"}),
            ("change", {"app_label": "dcim", "model": "manufacturer"}),
            ("delete", {"app_label": "dcim", "model": "manufacturer"}),
            ("view", {"app_label": "extras", "model": "objectlock"}),
            ("delete", {"app_label": "extras", "model": "objectlock"}),
        ]:
            perm = ObjectPermission.objects.create(name=f"{action}-{ct_kwargs['model']}", actions=[action])
            perm.object_types.set([ContentType.objects.get(**ct_kwargs)])
            perm.users.add(self.user)
        # A single own-lock that blocks BOTH update and delete: the detail template renders both the
        # Edit and Delete affordances whenever any active lock exists, so one claim with both flags
        # exercises both blocked controls while keeping the panel at exactly one releasable row (the
        # release-to-zero assertions below depend on the counter starting at 1).
        ObjectLock.objects.create(
            content_type=self.ct,
            object_id=self.manufacturer.pk,
            prevent_delete=True,
            prevent_update=True,
            reason="integration",
            source_key=f"user:{self.user.pk}",
            created_by=self.user,
            expires=timezone.now() + timedelta(days=1),
        )

    def _detail_url(self):
        return f"{self.live_server_url}{self.manufacturer.get_absolute_url()}"

    def _open_detail(self):
        """Load the locked object's detail page (assumes already logged in); return its URL."""
        url = self._detail_url()
        self.browser.visit(url)
        return url

    def _visit_detail(self):
        """Log in once and load the locked object's detail page; return its URL."""
        self.login(self.user.username, self.password)
        return self._open_detail()

    def test_delete_control_is_aria_disabled_with_explanation(self):
        self._visit_detail()
        delete_btn = self.browser.find_by_css("[data-nb-object-lock-blocked='delete']", wait_time=5)
        self.assertEqual(1, len(delete_btn))
        self.assertEqual("true", delete_btn.first["aria-disabled"])
        described_by = delete_btn.first["aria-describedby"]
        self.assertTrue(described_by)
        explanation = self.browser.find_by_id(described_by)
        self.assertIn("protected against accidental deletion", explanation.first["innerHTML"])

    def test_edit_control_is_aria_disabled_with_explanation(self):
        # The Edit affordance must carry the same accessible blocked semantics as Delete: focusable,
        # aria-disabled, and pointing (via aria-describedby) at an explanation element that exists.
        self._visit_detail()
        edit_btn = self.browser.find_by_css("[data-nb-object-lock-blocked='edit']", wait_time=5)
        self.assertEqual(1, len(edit_btn))
        self.assertEqual("true", edit_btn.first["aria-disabled"])
        described_by = edit_btn.first["aria-describedby"]
        self.assertTrue(described_by)
        explanation = self.browser.find_by_id(described_by)
        # The aria-describedby target must resolve to a real element with edit-specific copy.
        self.assertEqual(1, len(explanation))
        self.assertIn("edit it", explanation.first["innerHTML"])

    def test_blocked_control_click_suppresses_navigation_and_moves_focus(self):
        # Activating a blocked control must NOT navigate (proves event.preventDefault on the <a href="#">)
        # and must move focus to its explanation element (the core screen-reader affordance).
        self.login(self.user.username, self.password)
        for blocked in ("edit", "delete"):
            with self.subTest(control=blocked):
                url = self._open_detail()  # reload between subtests so each starts from a clean page
                control = self.browser.find_by_css(f"[data-nb-object-lock-blocked='{blocked}']", wait_time=5)
                described_by = control.first["aria-describedby"]
                control.first.click()
                # Navigation suppression: the URL is still the detail page (no "#" appended, no nav).
                self.assertEqual(url, self.browser.url)
                # Focus moves to the explanation element identified by aria-describedby.
                self.assertEqual(described_by, self.browser.evaluate_script("document.activeElement.id"))

    def test_blocked_control_keyboard_activation_suppresses_navigation_and_moves_focus(self):
        # Keyboard parity: focusing a blocked control and pressing Enter (and Space) yields the same
        # navigation-suppression + focus-to-explanation result as a click. We drive the real key press
        # through the underlying Selenium WebElement rather than simulating an event, so this exercises
        # the keydown handler end to end.
        self.login(self.user.username, self.password)
        for key in (Keys.ENTER, Keys.SPACE):
            with self.subTest(key="ENTER" if key == Keys.ENTER else "SPACE"):
                url = self._open_detail()  # reload between subtests so each starts from a clean page
                control = self.browser.find_by_css("[data-nb-object-lock-blocked='edit']", wait_time=5)
                described_by = control.first["aria-describedby"]
                element = control.first._element  # underlying Selenium WebElement
                # Focus the control as a keyboard user would (tab onto it) before sending the key, so the
                # keydown lands on the blocked control and not on whatever the page focused by default.
                self.browser.driver.execute_script("arguments[0].focus();", element)
                element.send_keys(key)
                self.assertEqual(url, self.browser.url)
                self.assertEqual(described_by, self.browser.evaluate_script("document.activeElement.id"))

    def test_remaining_counter_region_is_live(self):
        # The "N remaining" region must be a status live region so screen readers announce the count
        # change after a release without the user moving focus. role="status" implies aria-live="polite"
        # (the explicit attribute is intentionally not set, to avoid the redundancy).
        self._visit_detail()
        counter = self.browser.find_by_css(".object-lock-remaining", wait_time=5)
        self.assertEqual(1, len(counter))
        self.assertEqual("status", counter.first["role"])

    def test_releasing_own_lock_decrements_counter_to_zero(self):
        self._visit_detail()
        counter = self.browser.find_by_css(".object-lock-remaining", wait_time=5)
        self.assertEqual("1", counter.first["data-nb-remaining"])
        self.browser.find_by_css(".object-lock-release-btn", wait_time=5).first.click()
        # Releasing the only lock drops the live counter to 0. Per js/object_lock.js that briefly
        # announces "0 lock(s) remaining" in the aria-live region, then reloads the page so the server
        # re-renders the now-unblocked controls with their real action URLs (the client can't synthesize
        # them). The blocked-delete affordance is therefore gone after the reload, not flipped in place.
        self.assertTrue(self.browser.is_text_present("0 lock(s) remaining", wait_time=10))
        self.assertTrue(
            self.browser.is_element_not_present_by_css("[data-nb-object-lock-blocked='delete']", wait_time=10)
        )


@tag("integration")
class ObjectLockMixedOwnershipTestCase(SeleniumTestCase):
    def setUp(self):
        super().setUp()
        self.ct = ContentType.objects.get_for_model(Manufacturer)
        self.manufacturer = Manufacturer.objects.create(name="MixedMfr")
        self.other = User.objects.create_user(username="other-owner")
        # The lock is delete-only; grant delete on the manufacturer so the blocked Delete control
        # renders (the Delete control is gated on the user's delete permission for the object).
        for action, ct_kwargs in [
            ("view", {"app_label": "dcim", "model": "manufacturer"}),
            ("delete", {"app_label": "dcim", "model": "manufacturer"}),
            ("view", {"app_label": "extras", "model": "objectlock"}),
            ("delete", {"app_label": "extras", "model": "objectlock"}),
        ]:
            perm = ObjectPermission.objects.create(name=f"{action}-{ct_kwargs['model']}", actions=[action])
            perm.object_types.set([ContentType.objects.get(**ct_kwargs)])
            perm.users.add(self.user)
        # One own lock + one lock held by someone else (no force_release perm granted).
        ObjectLock.objects.create(
            content_type=self.ct,
            object_id=self.manufacturer.pk,
            prevent_delete=True,
            reason="mine",
            source_key=f"user:{self.user.pk}",
            created_by=self.user,
            expires=timezone.now() + timedelta(days=1),
        )
        ObjectLock.objects.create(
            content_type=self.ct,
            object_id=self.manufacturer.pk,
            prevent_delete=True,
            reason="theirs",
            source_key=f"user:{self.other.pk}",
            created_by=self.other,
            expires=timezone.now() + timedelta(days=1),
        )

    def test_terminal_state_hands_off_to_administrator(self):
        self.login(self.user.username, self.password)
        self.browser.visit(f"{self.live_server_url}{self.manufacturer.get_absolute_url()}")
        # Only the OWN lock has a release button.
        self.assertEqual(1, len(self.browser.find_by_css(".object-lock-release-btn")))
        self.browser.find_by_css(".object-lock-release-btn").first.click()
        self.assertTrue(self.browser.is_text_present("Contact an administrator to release them", wait_time=10))
        # The blocked delete control stays aria-disabled (cannot reach zero).
        self.assertTrue(
            self.browser.is_element_present_by_css(
                "[data-nb-object-lock-blocked='delete'][aria-disabled='true']", wait_time=5
            )
        )


@tag("integration")
class ObjectLockListAndDetailTestCase(SeleniumTestCase):
    def setUp(self):
        super().setUp()
        self.ct = ContentType.objects.get_for_model(Manufacturer)
        self.locked = Manufacturer.objects.create(name="ListLockedMfr")
        self.unlocked = Manufacturer.objects.create(name="ListUnlockedMfr")
        for action in ["view", "add", "change", "delete"]:
            perm = ObjectPermission.objects.create(name=f"mfr-{action}", actions=[action])
            perm.object_types.set([self.ct])
            perm.users.add(self.user)
        view_lock = ObjectPermission.objects.create(name="view-lock", actions=["view"])
        view_lock.object_types.set([ContentType.objects.get(app_label="extras", model="objectlock")])
        view_lock.users.add(self.user)
        add_lock = ObjectPermission.objects.create(name="add-lock", actions=["add"])
        add_lock.object_types.set([ContentType.objects.get(app_label="extras", model="objectlock")])
        add_lock.users.add(self.user)
        ObjectLock.objects.create(
            content_type=self.ct,
            object_id=self.locked.pk,
            prevent_delete=True,
            reason="list",
            source_key="s",
            expires=timezone.now() + timedelta(days=1),
        )

    def test_list_view_shows_glyph_next_to_locked_object(self):
        self.login(self.user.username, self.password)
        self.browser.visit(f"{self.live_server_url}/dcim/manufacturers/")
        self.assertTrue(self.browser.is_text_present("ListLockedMfr", wait_time=5))
        # A lock glyph appears somewhere in the locked row.
        glyphs = self.browser.find_by_css("td .mdi-lock")
        self.assertGreaterEqual(len(glyphs), 1)

    def test_quick_filter_shows_locked_only(self):
        self.login(self.user.username, self.password)
        self.browser.visit(f"{self.live_server_url}/dcim/manufacturers/?is_locked=true")
        self.assertTrue(self.browser.is_text_present("ListLockedMfr", wait_time=5))
        self.assertFalse(self.browser.is_text_present("ListUnlockedMfr"))

    def test_detail_view_shows_banner_and_panel(self):
        self.login(self.user.username, self.password)
        self.browser.visit(f"{self.live_server_url}{self.locked.get_absolute_url()}")
        self.assertTrue(self.browser.is_text_present("Delete-locked", wait_time=5))  # banner
        self.assertTrue(
            self.browser.is_text_present("LOCKS", wait_time=5) or self.browser.is_text_present("Locks", wait_time=5)
        )  # panel label

    def test_bulk_lock_confirmation_lists_locked_member(self):
        self.login(self.user.username, self.password)
        self.browser.visit(f"{self.live_server_url}/dcim/manufacturers/")
        # Select all rows and click "Lock Selected".
        self.browser.find_by_css("input[type=checkbox][name=pk]", wait_time=5)
        for cb in self.browser.find_by_css("input[type=checkbox][name=pk]"):
            cb.check()
        # With both change+delete granted, the bulk-action bar renders "Edit Selected" as the primary
        # split-button and stows the rest (Delete/Lock/Release) inside a collapsed Bootstrap dropdown
        # (see consolidated_bulk_action_buttons.html). Open that menu first so "Lock Selected" is
        # interactable, exactly as a user must.
        self.browser.find_by_css(".btn-group.dropup .dropdown-toggle", wait_time=5).first.click()
        lock_btn = self.browser.find_by_xpath("//button[@name='_lock']", wait_time=5).first
        self.assertTrue(lock_btn.visible)
        lock_btn.click()
        self.assertTrue(self.browser.is_text_present("already locked", wait_time=10))
