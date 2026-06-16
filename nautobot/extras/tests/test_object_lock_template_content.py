"""Tests for the Object Lock detail-view banner (template_content.py)."""

from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.template import Context
from django.test import override_settings, RequestFactory, TestCase
from django.utils import timezone

from nautobot.dcim.models import Manufacturer
from nautobot.extras.models import ObjectLock
from nautobot.extras.plugins import TemplateExtension
from nautobot.extras.registry import registry
from nautobot.extras.template_content import (
    _claim_can_release,
    object_lock_banner,
    ObjectLockPanel,
    register_object_lock_ui,
)
from nautobot.users.models import ObjectPermission

User = get_user_model()


class ObjectLockBannerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ct = ContentType.objects.get_for_model(Manufacturer)
        cls.user = User.objects.create_superuser(username="su")
        cls.locked = Manufacturer.objects.create(name="Banner Locked")
        cls.unlocked = Manufacturer.objects.create(name="Banner Unlocked")
        expiry = timezone.now() + timedelta(days=1)
        ObjectLock.objects.create(
            content_type=cls.ct,
            object_id=cls.locked.pk,
            prevent_delete=True,
            prevent_update=False,
            reason="d",
            source_key="a",
            expires=expiry,
        )
        ObjectLock.objects.create(
            content_type=cls.ct,
            object_id=cls.locked.pk,
            prevent_delete=False,
            prevent_update=True,
            reason="u",
            source_key="b",
            expires=expiry,
        )

    def _context(self, obj):
        request = RequestFactory().get("/")
        request.user = self.user
        return SimpleNamespace(
            request=request,
            __contains__=lambda self, k: k == "object",
            __getitem__=lambda self, k: obj,
        )

    def test_no_banner_for_unlocked_object(self):
        ctx = {"object": self.unlocked, "request": self._context(self.unlocked).request}
        self.assertIsNone(object_lock_banner(ctx))

    def test_banner_names_all_modes_and_count(self):
        ctx = {"object": self.locked, "request": self._context(self.locked).request}
        banner = object_lock_banner(ctx)
        self.assertIsNotNone(banner)
        self.assertIn("Delete-locked and update-locked", banner.content)
        self.assertIn("2", banner.content)  # contributing-lock count

    def test_no_banner_on_list_views(self):
        ctx = {"object": None, "request": self._context(self.unlocked).request}
        self.assertIsNone(object_lock_banner(ctx))


class ObjectLockPanelTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ct = ContentType.objects.get_for_model(Manufacturer)
        cls.locked = Manufacturer.objects.create(name="Panel Locked")
        cls.unlocked = Manufacturer.objects.create(name="Panel Unlocked")
        expiry = timezone.now() + timedelta(days=1)
        ObjectLock.objects.create(
            content_type=cls.ct,
            object_id=cls.locked.pk,
            prevent_delete=True,
            prevent_update=False,
            reason="because",
            source_key="src-a",
            expires=expiry,
        )
        cls.viewer = User.objects.create_user(username="viewer")
        cls.privileged = User.objects.create_user(username="priv")
        perm = ObjectPermission.objects.create(name="vl", actions=["view"])
        perm.object_types.set([ContentType.objects.get(app_label="extras", model="objectlock")])
        perm.users.add(cls.privileged)

    def _render(self, obj, user):
        # Panel.render(self, context: Context) consumes a django.template.Context directly,
        # so this helper matches the real API verbatim -- no adaptation needed.
        request = RequestFactory().get("/")
        request.user = user
        panel = ObjectLockPanel(weight=750)
        ctx = Context({"object": obj, "request": request})
        return panel.render(ctx)

    def test_panel_hidden_for_unlocked_object(self):
        self.assertEqual(self._render(self.unlocked, self.privileged), "")

    def test_panel_shows_metadata_for_privileged_user(self):
        html = self._render(self.locked, self.privileged)
        self.assertIn("because", html)  # reason visible
        self.assertIn("src-a", html)  # source visible
        self.assertIn("LOCKS", html.upper())

    def test_panel_redacts_metadata_without_permission(self):
        html = self._render(self.locked, self.viewer)
        self.assertNotIn("because", html)  # reason hidden
        self.assertNotIn("src-a", html)  # source hidden
        self.assertIn("Lock details are restricted to authorized users", html)

    @override_settings(OBJECT_LOCK_ENFORCED=False)
    def test_panel_dormant_when_enforcement_disabled(self):
        """The kill switch suppresses the panel (no query, no render) even for a locked object."""
        request = RequestFactory().get("/")
        request.user = self.privileged
        panel = ObjectLockPanel(weight=750)
        ctx = Context({"object": self.locked, "request": request})
        self.assertFalse(panel.should_render(ctx))
        self.assertEqual(panel.render(ctx), "")


class ObjectLockExtensionRegistrationTestCase(TestCase):
    def test_banner_function_registered(self):
        self.assertIn(object_lock_banner, registry["plugin_banners"])

    def test_extension_registered_for_manufacturer(self):
        extensions = registry["plugin_template_extensions"].get("dcim.manufacturer", [])
        self.assertTrue(
            any(
                issubclass(ext, TemplateExtension)
                and ObjectLockPanel in [type(p) for p in (ext.object_detail_panels or [])]
                for ext in extensions
            ),
            "ObjectLock TemplateExtension with an ObjectLockPanel was not registered for dcim.manufacturer",
        )


class ObjectLockTemplateContentCoverageTestCase(TestCase):
    """Cover the remaining reachable branches in template_content.py."""

    @classmethod
    def setUpTestData(cls):
        cls.ct = ContentType.objects.get_for_model(Manufacturer)
        cls.user = User.objects.create_superuser(username="tc-cov-su")
        cls.mfr = Manufacturer.objects.create(name="TC Cov Mfr")

    def test_claim_can_release_own_claim(self):
        # Own claim + delete_objectlock (superuser) -> (can_release=True, is_own=True). The other-source
        # branch is exercised by the panel tests; this covers the is_own branch.
        claim = ObjectLock.objects.create(
            content_type=self.ct,
            object_id=self.mfr.pk,
            prevent_delete=True,
            source_key="own",
            created_by=self.user,
        )
        self.assertEqual(_claim_can_release(claim, self.user), (True, True))

    def test_panel_does_not_render_without_object(self):
        self.assertFalse(ObjectLockPanel(weight=750).should_render(Context({})))

    def test_register_object_lock_ui_is_idempotent(self):
        # register_object_lock_ui() runs at app startup; re-running must not double-register a model's
        # extension (the documented "safe to re-run" guard).
        key = f"{self.ct.app_label}.{self.ct.model}"
        before = len(registry["plugin_template_extensions"].get(key, []))
        register_object_lock_ui()
        self.assertEqual(len(registry["plugin_template_extensions"].get(key, [])), before)
