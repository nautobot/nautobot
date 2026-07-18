"""REST API tests for ObjectLock."""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status

from nautobot.core.testing import APITestCase, APIViewTestCases
from nautobot.dcim.models import Manufacturer
from nautobot.extras.api.object_locks import ObjectLockSerializer
from nautobot.extras.choices import ObjectChangeEventContextChoices
from nautobot.extras.models import ObjectLock

User = get_user_model()


class ObjectLockAPITestCase(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.DeleteObjectViewTestCase,
):
    model = ObjectLock

    @classmethod
    def setUpTestData(cls):
        ct = ContentType.objects.get_for_model(Manufacturer)
        for i in range(3):
            mfg = Manufacturer.objects.create(name=f"API Lock Mfg {i}")
            ObjectLock.objects.create(
                content_type=ct,
                object_id=mfg.pk,
                source_context=ObjectChangeEventContextChoices.CONTEXT_ORM,
                source_key=f"api-{i}",
            )

    def setUp(self):
        super().setUp()
        # Fixtures are ORM-created (created_by=None), so the inherited delete tests release another
        # source's claim — which requires force_release_objectlock; grant it so those standard tests pass.
        self.add_permissions("extras.force_release_objectlock")

    def test_post_is_method_not_allowed(self):
        """POST to the list endpoint must return 405, not 400/403.

        Locks must be created via ObjectLock.objects.lock() or the per-object
        protect action. This test locks in the guarantee that disabling POST is
        explicit (http_method_names) and not merely incidental validation.
        """
        self.add_permissions("extras.add_objectlock")
        url = self._get_list_url()
        ct = self._get_queryset().first().content_type
        data = {
            "content_type": f"{ct.app_label}.{ct.model}",
            "object_id": str(self._get_queryset().first().object_id),
        }
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, 405)

    def test_created_by_is_read_only_in_serializer(self):
        serializer = ObjectLockSerializer()
        for field_name in ("source_context", "source_detail", "source_key", "created_by"):
            self.assertTrue(
                serializer.fields[field_name].read_only,
                f"{field_name} must be read-only",
            )


class ObjectLockableActionsTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.mfg = Manufacturer.objects.create(name="Action Mfg")

    def test_lock_action_creates_lock(self):
        self.add_permissions("extras.add_objectlock", "dcim.view_manufacturer")
        url = f"/api/dcim/manufacturers/{self.mfg.pk}/lock/"
        response = self.client.post(url, {"prevent_delete": True, "reason": "via api"}, format="json", **self.header)
        self.assertHttpStatus(response, 201)
        self.assertEqual(ObjectLock.objects.for_object(self.mfg).count(), 1)

    def test_release_action_removes_own_lock(self):
        self.add_permissions("extras.add_objectlock", "extras.delete_objectlock", "dcim.view_manufacturer")
        lock_url = f"/api/dcim/manufacturers/{self.mfg.pk}/lock/"
        lock_resp = self.client.post(lock_url, {"prevent_delete": True}, format="json", **self.header)
        source_key = lock_resp.data["source_key"]
        release_url = f"/api/dcim/manufacturers/{self.mfg.pk}/release/"
        response = self.client.post(release_url, {"source_key": source_key}, format="json", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(ObjectLock.objects.for_object(self.mfg).count(), 0)

    def test_lock_action_requires_permission(self):
        url = f"/api/dcim/manufacturers/{self.mfg.pk}/lock/"
        response = self.client.post(url, {"prevent_delete": True}, format="json", **self.header)
        self.assertHttpStatus(response, 403)

    def test_release_action_requires_delete_objectlock_permission(self):
        """``release`` without ``extras.delete_objectlock`` must return 403."""
        self.add_permissions("extras.add_objectlock")
        url = f"/api/dcim/manufacturers/{self.mfg.pk}/release/"
        response = self.client.post(url, {"source_key": "any-key"}, format="json", **self.header)
        self.assertHttpStatus(response, 403)

    def test_lock_action_requires_view_permission(self):
        """A user with ``extras.add_objectlock`` but no view access to the target cannot lock it."""
        self.add_permissions("extras.add_objectlock")
        url = f"/api/dcim/manufacturers/{self.mfg.pk}/lock/"
        response = self.client.post(
            url, {"prevent_delete": True, "reason": "no view perm"}, format="json", **self.header
        )
        self.assertHttpStatus(response, 404)
        self.assertEqual(ObjectLock.objects.for_object(self.mfg).count(), 0)

    def test_lock_action_rejects_malformed_expires(self):
        """A malformed ``expires`` value must return 400, not 500."""
        self.add_permissions("extras.add_objectlock")
        url = f"/api/dcim/manufacturers/{self.mfg.pk}/lock/"
        response = self.client.post(
            url, {"prevent_delete": True, "expires": "not-a-datetime"}, format="json", **self.header
        )
        self.assertHttpStatus(response, 400)

    def test_release_other_source_requires_force_release(self):
        """Releasing a claim created by another source needs force_release_objectlock, not just delete."""
        other = User.objects.create_user(username="other-locker")
        ObjectLock.objects.lock(self.mfg, prevent_delete=True, source_key="theirs", requesting_user=other)
        self.add_permissions("extras.delete_objectlock", "dcim.view_manufacturer")
        url = f"/api/dcim/manufacturers/{self.mfg.pk}/release/"
        response = self.client.post(url, {"source_key": "theirs"}, format="json", **self.header)
        self.assertHttpStatus(response, 403)
        self.assertEqual(ObjectLock.objects.for_object(self.mfg).count(), 1)

    def test_force_release_releases_other_source(self):
        """With force_release_objectlock, releasing another source's claim succeeds."""
        other = User.objects.create_user(username="other-locker-2")
        ObjectLock.objects.lock(self.mfg, prevent_delete=True, source_key="theirs", requesting_user=other)
        self.add_permissions("extras.delete_objectlock", "extras.force_release_objectlock", "dcim.view_manufacturer")
        url = f"/api/dcim/manufacturers/{self.mfg.pk}/release/"
        response = self.client.post(url, {"source_key": "theirs"}, format="json", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(ObjectLock.objects.for_object(self.mfg).count(), 0)

    def test_release_action_requires_source_key(self):
        """Releasing with no source_key must 400, not 200 with a silent zero-row no-op."""
        self.add_permissions("extras.delete_objectlock", "dcim.view_manufacturer")
        url = f"/api/dcim/manufacturers/{self.mfg.pk}/release/"
        response = self.client.post(url, {}, format="json", **self.header)
        self.assertHttpStatus(response, 400)

    def test_lock_action_rejects_cross_owner_source_key_reuse(self):
        """Reusing another source's source_key needs force_release_objectlock; the action 400s without it."""
        other = User.objects.create_user(username="other-lock-owner")
        ObjectLock.objects.lock(self.mfg, prevent_delete=True, source_key="shared", requesting_user=other)
        self.add_permissions("extras.add_objectlock", "dcim.view_manufacturer")
        url = f"/api/dcim/manufacturers/{self.mfg.pk}/lock/"
        response = self.client.post(url, {"prevent_delete": True, "source_key": "shared"}, format="json", **self.header)
        self.assertHttpStatus(response, 400)
        # The other source's single claim is left untouched (no silent takeover).
        self.assertEqual(ObjectLock.objects.for_object(self.mfg).get().created_by, other)

    def test_force_release_permits_cross_owner_source_key_reuse(self):
        """With force_release_objectlock the reuse is allowed (201) and refreshes the existing claim."""
        other = User.objects.create_user(username="other-lock-owner-2")
        ObjectLock.objects.lock(self.mfg, prevent_delete=True, source_key="shared", requesting_user=other)
        self.add_permissions("extras.add_objectlock", "extras.force_release_objectlock", "dcim.view_manufacturer")
        url = f"/api/dcim/manufacturers/{self.mfg.pk}/lock/"
        response = self.client.post(url, {"prevent_update": True, "source_key": "shared"}, format="json", **self.header)
        self.assertHttpStatus(response, 201)
        # Refreshed in place (still one claim, attribution preserved), not a second claim.
        lock = ObjectLock.objects.for_object(self.mfg).get()
        self.assertTrue(lock.prevent_update)
        self.assertEqual(lock.created_by, other)


class ObjectLockGenericDeleteAuthzTestCase(APITestCase):
    """The generic ObjectLock endpoint disables PATCH and gates DELETE on force-release."""

    def setUp(self):
        super().setUp()
        self.ct = ContentType.objects.get_for_model(Manufacturer)
        self.mfg = Manufacturer.objects.create(name="Generic Del Mfg")

    def _make_lock(self, created_by):
        return ObjectLock.objects.create(
            content_type=self.ct,
            object_id=self.mfg.pk,
            source_context=ObjectChangeEventContextChoices.CONTEXT_ORM,
            source_key="generic-del",
            created_by=created_by,
        )

    def _detail_url(self, lock):
        return reverse("extras-api:objectlock-detail", kwargs={"pk": lock.pk})

    def test_patch_is_method_not_allowed(self):
        self.add_permissions("extras.change_objectlock")
        lock = self._make_lock(None)
        response = self.client.patch(self._detail_url(lock), {"reason": "edit"}, format="json", **self.header)
        self.assertHttpStatus(response, 405)

    def test_delete_other_source_without_force_is_forbidden(self):
        self.add_permissions("extras.delete_objectlock")
        lock = self._make_lock(None)  # created_by=None -> not owned by self.user
        response = self.client.delete(self._detail_url(lock), **self.header)
        self.assertHttpStatus(response, 403)
        self.assertTrue(ObjectLock.objects.filter(pk=lock.pk).exists())

    def test_delete_with_force_release_succeeds(self):
        self.add_permissions("extras.delete_objectlock", "extras.force_release_objectlock")
        lock = self._make_lock(None)
        response = self.client.delete(self._detail_url(lock), **self.header)
        self.assertHttpStatus(response, 204)
        self.assertFalse(ObjectLock.objects.filter(pk=lock.pk).exists())

    def test_owner_deletes_own_claim(self):
        self.add_permissions("extras.delete_objectlock")
        lock = self._make_lock(self.user)  # owned by self.user
        response = self.client.delete(self._detail_url(lock), **self.header)
        self.assertHttpStatus(response, 204)


class ObjectLockableSerializerFieldsTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.mfg = Manufacturer.objects.create(name="Fields Mfg")

    def test_unlocked_object_reports_false(self):
        self.add_permissions("dcim.view_manufacturer")
        response = self.client.get(f"/api/dcim/manufacturers/{self.mfg.pk}/", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertFalse(response.data["is_locked"])
        self.assertFalse(response.data["locked_for_delete"])
        self.assertFalse(response.data["locked_for_update"])

    def test_locked_object_reports_true(self):
        ObjectLock.objects.lock(self.mfg, prevent_delete=True, requesting_user=self.user)
        self.add_permissions("dcim.view_manufacturer")
        response = self.client.get(f"/api/dcim/manufacturers/{self.mfg.pk}/", **self.header)
        self.assertTrue(response.data["is_locked"])
        self.assertTrue(response.data["locked_for_delete"])
        self.assertFalse(response.data["locked_for_update"])

    def test_locked_fields_gated_behind_view_objectlock(self):
        ObjectLock.objects.lock(self.mfg, prevent_update=True, locked_fields=["description"], requesting_user=self.user)
        self.add_permissions("dcim.view_manufacturer")
        # Without view_objectlock: locked_fields must be None (gated), booleans still present.
        response = self.client.get(f"/api/dcim/manufacturers/{self.mfg.pk}/", **self.header)
        self.assertTrue(response.data["is_locked"])
        self.assertIsNone(response.data["locked_fields"])
        # With view_objectlock: locked_fields revealed.
        self.add_permissions("extras.view_objectlock")
        response = self.client.get(f"/api/dcim/manufacturers/{self.mfg.pk}/", **self.header)
        self.assertEqual(response.data["locked_fields"], ["description"])


class ObjectLock409TestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.mfg = Manufacturer.objects.create(name="409 Mfg")
        ObjectLock.objects.lock(self.mfg, prevent_delete=True, reason="held", requesting_user=self.user)

    def test_blocked_delete_returns_409(self):
        self.add_permissions("dcim.delete_manufacturer")
        response = self.client.delete(f"/api/dcim/manufacturers/{self.mfg.pk}/", **self.header)
        self.assertHttpStatus(response, status.HTTP_409_CONFLICT)

    def test_409_body_without_view_objectlock_is_generic(self):
        self.add_permissions("dcim.delete_manufacturer")
        response = self.client.delete(f"/api/dcim/manufacturers/{self.mfg.pk}/", **self.header)
        body = str(response.data)
        self.assertNotIn("held", body)  # the reason must not leak
        self.assertIn("object_locked", body)  # stable error code

    def test_409_body_with_view_objectlock_includes_detail(self):
        self.add_permissions("dcim.delete_manufacturer", "extras.view_objectlock")
        response = self.client.delete(f"/api/dcim/manufacturers/{self.mfg.pk}/", **self.header)
        body = str(response.data)
        self.assertIn("delete", body)  # mode is disclosed to authorized viewers

    def test_blocked_update_returns_409(self):
        """A blocked PATCH of an update-locked object must return 409 (not 500), disclosing the update mode."""
        # Place an update lock on the same object so the PATCH hits the update gate (present_in_database is True).
        ObjectLock.objects.lock(self.mfg, prevent_update=True, reason="held", requesting_user=self.user)
        self.add_permissions("dcim.change_manufacturer", "extras.view_objectlock")
        response = self.client.patch(
            f"/api/dcim/manufacturers/{self.mfg.pk}/", {"description": "changed"}, format="json", **self.header
        )
        self.assertHttpStatus(response, status.HTTP_409_CONFLICT)
        body = str(response.data)
        self.assertIn("update", body)  # update mode is disclosed to authorized viewers


class ObjectLockableFilterTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.locked_mfg = Manufacturer.objects.create(name="Filter Locked Mfg")
        self.unlocked_mfg = Manufacturer.objects.create(name="Filter Unlocked Mfg")
        ObjectLock.objects.lock(self.locked_mfg, prevent_delete=True, requesting_user=self.user)
        self.add_permissions("dcim.view_manufacturer")

    def test_filter_is_locked_true(self):
        response = self.client.get("/api/dcim/manufacturers/?is_locked=true", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        names = {row["name"] for row in response.data["results"]}
        self.assertIn("Filter Locked Mfg", names)
        self.assertNotIn("Filter Unlocked Mfg", names)

    def test_filter_is_locked_false(self):
        response = self.client.get("/api/dcim/manufacturers/?is_locked=false", **self.header)
        names = {row["name"] for row in response.data["results"]}
        self.assertIn("Filter Unlocked Mfg", names)
        self.assertNotIn("Filter Locked Mfg", names)


class ObjectLockSerializerQueryCountTestCase(APITestCase):
    """Lock-state fields resolve in one query per page, not one per object."""

    def setUp(self):
        super().setUp()
        self.add_permissions("dcim.view_manufacturer")

    def test_lock_state_is_batched_per_page(self):
        for i in range(5):
            mfg = Manufacturer.objects.create(name=f"QueryCount Mfg {i}")
            ObjectLock.objects.lock(mfg, prevent_delete=True, source_key=f"qc-{i}", requesting_user=self.user)
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/api/dcim/manufacturers/", **self.header)
            self.assertHttpStatus(response, 200)
        lock_queries = [q for q in ctx.captured_queries if "extras_objectlock" in q["sql"]]
        self.assertLessEqual(
            len(lock_queries), 1, f"Lock state must batch into one query per page; got {len(lock_queries)}"
        )
