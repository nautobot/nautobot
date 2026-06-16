from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import override_settings, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from nautobot.core.graphql import execute_query
from nautobot.dcim.models import Manufacturer
from nautobot.extras.models import ObjectLock
from nautobot.users.models import ObjectPermission

User = get_user_model()


class _GraphQLTestMixin:
    @classmethod
    def setUpTestData(cls):
        cls.ct = ContentType.objects.get_for_model(Manufacturer)
        cls.locked = Manufacturer.objects.create(name="GQL Locked")
        cls.unlocked = Manufacturer.objects.create(name="GQL Unlocked")
        cls.expiry = timezone.now() + timedelta(days=1)
        ObjectLock.objects.create(
            content_type=cls.ct,
            object_id=cls.locked.pk,
            prevent_delete=True,
            prevent_update=False,
            reason="gql reason",
            source_key="gql-src",
            expires=cls.expiry,
        )
        cls.superuser = User.objects.create_superuser(username="gql-su")

    def _execute(self, query, user):
        """Execute ``query`` as ``user`` and return a dict with ``data``/``errors`` keys.

        Object-level permissions are enforced (no ``EXEMPT_VIEW_PERMISSIONS``) so the gating tests
        exercise the same permission path as production.
        """
        result = execute_query(query, user=user)
        out = {}
        if result.errors:
            out["errors"] = result.errors
        out["data"] = result.data
        return out


class ObjectLockGraphQLTypeTestCase(_GraphQLTestMixin, TestCase):
    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_object_locks_query_returns_claims(self):
        resp = execute_query("{ object_locks { reason source_key prevent_delete } }", user=self.superuser)
        self.assertIsNone(resp.errors, resp.errors)
        rows = resp.data["object_locks"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["reason"], "gql reason")
        self.assertTrue(rows[0]["prevent_delete"])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_object_locks_filterable_by_prevent_delete(self):
        resp = execute_query("{ object_locks(prevent_delete: true) { source_key } }", user=self.superuser)
        self.assertIsNone(resp.errors, resp.errors)
        self.assertEqual(len(resp.data["object_locks"]), 1)


class ObjectLockSchemaFieldsTestCase(_GraphQLTestMixin, TestCase):
    def test_object_exposes_lock_state_fields(self):
        query = """
        { manufacturers { name is_locked locked_for_delete locked_for_update } }
        """
        result = self._execute(query, self.superuser)
        self.assertNotIn("errors", result, result.get("errors"))
        by_name = {m["name"]: m for m in result["data"]["manufacturers"]}
        self.assertTrue(by_name["GQL Locked"]["is_locked"])
        self.assertTrue(by_name["GQL Locked"]["locked_for_delete"])
        self.assertFalse(by_name["GQL Locked"]["locked_for_update"])
        self.assertFalse(by_name["GQL Unlocked"]["is_locked"])

    def test_locks_resolver_returns_metadata_for_privileged_user(self):
        query = '{ manufacturers(name: "GQL Locked") { locks { reason source_key } } }'
        result = self._execute(query, self.superuser)
        self.assertNotIn("errors", result, result.get("errors"))
        locks = result["data"]["manufacturers"][0]["locks"]
        self.assertEqual(len(locks), 1)
        self.assertEqual(locks[0]["reason"], "gql reason")

    def test_locks_resolver_empty_without_view_permission(self):
        viewer = User.objects.create_user(username="gql-viewer")
        perm = ObjectPermission.objects.create(name="view mfr gql", actions=["view"])
        perm.object_types.set([self.ct])
        perm.users.add(viewer)
        query = '{ manufacturers(name: "GQL Locked") { is_locked locks { reason } } }'
        result = self._execute(query, viewer)
        self.assertNotIn("errors", result, result.get("errors"))
        row = result["data"]["manufacturers"][0]
        self.assertTrue(row["is_locked"])  # boolean still visible
        self.assertEqual(row["locks"], [])  # richer metadata gated off

    def test_locked_fields_resolver_gated_by_view_permission(self):
        """locked_fields lists frozen names for a privileged user and is empty ([]) for a gated user."""
        field_locked = Manufacturer.objects.create(name="GQL FieldLocked")
        ObjectLock.objects.create(
            content_type=self.ct,
            object_id=field_locked.pk,
            prevent_update=True,
            locked_fields=["description"],
            reason="field freeze",
            source_key="gql-field",
            expires=self.expiry,
        )
        query = '{ manufacturers(name: "GQL FieldLocked") { is_locked locked_fields } }'

        privileged = self._execute(query, self.superuser)
        self.assertNotIn("errors", privileged, privileged.get("errors"))
        self.assertEqual(privileged["data"]["manufacturers"][0]["locked_fields"], ["description"])

        viewer = User.objects.create_user(username="gql-fields-viewer")
        perm = ObjectPermission.objects.create(name="view mfr fields gql", actions=["view"])
        perm.object_types.set([self.ct])
        perm.users.add(viewer)
        gated = self._execute(query, viewer)
        self.assertNotIn("errors", gated, gated.get("errors"))
        row = gated["data"]["manufacturers"][0]
        self.assertTrue(row["is_locked"])  # boolean still visible
        self.assertEqual(row["locked_fields"], [])  # frozen-field list gated off


class ObjectLockGraphQLQueryCountTestCase(_GraphQLTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Add 5 more locked manufacturers (total: 7 = 1 locked + 1 unlocked from mixin + 5 here).
        # More objects make an N+1 visible: if is_locked issues a query per object,
        # range(5) vs range(50) would produce different query counts.
        for i in range(5):
            mfr = Manufacturer.objects.create(name=f"GQL Bulk {i}")
            ObjectLock.objects.create(
                content_type=cls.ct,
                object_id=mfr.pk,
                prevent_delete=True,
                reason="bulk",
                source_key=f"k{i}",
                expires=cls.expiry,
            )

    @staticmethod
    def _lock_query_count(captured_queries):
        """Count queries against the ObjectLock *records* table (excluding the generation/audit tables)."""
        return sum(
            1
            for q in captured_queries
            # Bare table name (no surrounding quote char) matches both Postgres ("x") and MySQL (`x`)
            # identifier quoting; the two excludes below drop the sibling generation/audit tables.
            if "extras_objectlock" in q["sql"]
            and "extras_objectlockgeneration" not in q["sql"]
            and "extras_objectlockbypassaudit" not in q["sql"]
        )

    def test_lock_fields_do_not_n_plus_one(self):
        """Resolving is_locked/locks across many objects costs ONE batched ObjectLock query, not N.

        We count only ObjectLock-records queries (the total query count is brittle — it includes
        unrelated schema/cache warmup — and the row count is non-deterministic under ``--keepdb`` because
        the integration tests commit Manufacturer rows). The invariance proof: adding 20 more locked
        manufacturers must NOT increase the ObjectLock query count, because claims_for_object batches the
        whole content type into a single per-request query.
        """
        query = "{ manufacturers { name is_locked locks { reason } } }"

        with CaptureQueriesContext(connection) as ctx_small:
            result_small = self._execute(query, self.superuser)
        self.assertNotIn("errors", result_small, result_small.get("errors"))
        by_name = {m["name"]: m for m in result_small["data"]["manufacturers"]}
        self.assertTrue(by_name["GQL Locked"]["is_locked"])  # field actually resolved (non-vacuous)
        small_count = self._lock_query_count(ctx_small.captured_queries)
        # Exactly one ObjectLock query batches the entire Manufacturer content type.
        self.assertEqual(small_count, 1, f"expected 1 batched ObjectLock query, got {small_count}")

        # Add 20 more locked manufacturers; the ObjectLock query count must be unchanged (no N+1).
        for i in range(20):
            mfr = Manufacturer.objects.create(name=f"GQL Scale {i}")
            ObjectLock.objects.create(
                content_type=self.ct,
                object_id=mfr.pk,
                prevent_delete=True,
                reason="scale",
                source_key=f"s{i}",
                expires=self.expiry,
            )
        with CaptureQueriesContext(connection) as ctx_large:
            result_large = self._execute(query, self.superuser)
        self.assertNotIn("errors", result_large, result_large.get("errors"))
        large_count = self._lock_query_count(ctx_large.captured_queries)
        self.assertEqual(
            large_count, small_count, f"ObjectLock query count scaled with object count: {small_count} -> {large_count}"
        )


class ObjectLockGraphQLKillSwitchTestCase(_GraphQLTestMixin, TestCase):
    @override_settings(OBJECT_LOCK_ENFORCED=False)
    def test_claims_for_object_returns_empty_when_enforcement_disabled(self):
        """With OBJECT_LOCK_ENFORCED off, the GraphQL claims lookup surfaces no lock state for a locked object."""
        from nautobot.extras.graphql.object_lock import claims_for_object

        # The kill-switch branch returns before touching the request, so a bare None proves it fired first.
        self.assertEqual(claims_for_object(None, self.ct.pk, self.locked.pk), [])
