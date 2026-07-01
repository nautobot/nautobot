"""Tests for Object Lock core enforcement."""

from datetime import timedelta
from unittest import mock
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction
from django.db.models import ProtectedError
from django.db.utils import IntegrityError
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
import redis.exceptions

from nautobot.core.testing import TestCase
from nautobot.dcim.models import Manufacturer
from nautobot.extras.choices import ObjectChangeEventContextChoices, ObjectLockModeChoices
from nautobot.extras.context_managers import web_request_context
from nautobot.extras.factory import ObjectLockFactory
from nautobot.extras.jobs_object_lock_sweep import purge_expired_and_orphaned_locks
from nautobot.extras.locking import (
    _current_token,
    _GATE_SNAPSHOT_ATTR,
    bypass_object_lock,
    enforce_object_lock,
    GATE_MODE_DELETE,
    GATE_MODE_UPDATE,
    get_gate,
    invalidate_gate_cache,
    is_bypass_active,
    ObjectLockedError,
)
from nautobot.extras.models import ObjectLock, ScheduledJobs
from nautobot.extras.models.object_locks import ObjectLockBypassAudit
from nautobot.extras.signals import _object_lock_enforce_update, change_context_state
from nautobot.users.models import ObjectPermission


class ObjectLockedErrorTestCase(TestCase):
    def test_is_subclass_of_protected_error(self):
        """ObjectLockedError must subclass Django's ProtectedError so delete views handle it."""
        self.assertTrue(issubclass(ObjectLockedError, ProtectedError))

    def test_can_be_raised_with_message_only(self):
        """ProtectedError requires (msg, protected_objects); allow a message-only convenience."""
        err = ObjectLockedError("locked")
        self.assertEqual(str(err), "locked")
        self.assertEqual(list(err.protected_objects), [])


class ObjectLockModeChoicesTestCase(TestCase):
    def test_delete_value(self):
        self.assertEqual(ObjectLockModeChoices.DELETE, "delete")

    def test_update_value(self):
        self.assertEqual(ObjectLockModeChoices.UPDATE, "update")

    def test_both_value(self):
        self.assertEqual(ObjectLockModeChoices.BOTH, "both")

    def test_choices_tuple(self):
        values = [c[0] for c in ObjectLockModeChoices.CHOICES]
        self.assertIn("delete", values)
        self.assertIn("update", values)
        self.assertIn("both", values)


class ObjectLockModelTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manufacturer = Manufacturer.objects.create(name="ACME Object Lock")
        cls.ct = ContentType.objects.get_for_model(Manufacturer)

    def _make_lock(self, **overrides):
        kwargs = {
            "content_type": self.ct,
            "object_id": self.manufacturer.pk,
            "source_context": ObjectChangeEventContextChoices.CONTEXT_ORM,
            "source_key": "test-key",
        }
        kwargs.update(overrides)
        return ObjectLock.objects.create(**kwargs)

    def test_defaults(self):
        lock = self._make_lock()
        self.assertTrue(lock.prevent_delete)
        self.assertFalse(lock.prevent_update)
        self.assertIsNone(lock.locked_fields)
        self.assertEqual(lock.reason, "")
        self.assertIsNone(lock.expires)

    def test_generic_foreign_key_resolves(self):
        lock = self._make_lock()
        self.assertEqual(lock.locked_object, self.manufacturer)

    def test_unique_constraint_ct_object_source_key(self):
        self._make_lock(source_key="dup")
        with self.assertRaises(IntegrityError):
            self._make_lock(source_key="dup")

    def test_str(self):
        lock = self._make_lock()
        self.assertIn("ACME Object Lock", str(lock))

    def test_has_custom_permissions(self):
        perms = dict(ObjectLock._meta.permissions)
        self.assertIn("bypass_objectlock", perms)
        self.assertIn("force_release_objectlock", perms)

    def test_active_excludes_expired(self):
        """active() includes non-expired locks and excludes expired ones."""
        expired_lock = self._make_lock(source_key="expired-key", expires=timezone.now() - timedelta(seconds=1))
        active_lock = self._make_lock(source_key="active-key", expires=None)

        active_qs = ObjectLock.objects.filter(pk__in=[expired_lock.pk, active_lock.pk]).active()

        self.assertIn(active_lock, active_qs)
        self.assertNotIn(expired_lock, active_qs)

    def test_natural_key_is_pk_based(self):
        """ObjectLock.natural_key() must return [str(pk)] to avoid UUID-derived composite keys."""
        lock = self._make_lock()
        self.assertEqual(lock.natural_key(), [str(lock.pk)])

    def test_for_object_returns_matching_locks(self):
        """for_object() returns only locks targeting the given object instance."""
        other_manufacturer = Manufacturer.objects.create(name="Other Manufacturer for Lock Test")
        lock_on_self = self._make_lock(source_key="key-self")
        lock_on_other = ObjectLock.objects.create(
            content_type=self.ct,
            object_id=other_manufacturer.pk,
            source_context=ObjectChangeEventContextChoices.CONTEXT_ORM,
            source_key="key-other",
        )

        result = ObjectLock.objects.filter(pk__in=[lock_on_self.pk, lock_on_other.pk]).for_object(self.manufacturer)

        self.assertIn(lock_on_self, result)
        self.assertNotIn(lock_on_other, result)


class ObjectLockFactoryTestCase(TestCase):
    def test_factory_creates_valid_lock(self):
        lock = ObjectLockFactory.create()
        self.assertIsNotNone(lock.content_type_id)
        self.assertIsNotNone(lock.object_id)
        self.assertNotEqual(lock.source_key, "")


class ObjectLockManagerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="ol-manager-user")
        cls.m1 = Manufacturer.objects.create(name="OL Mfg 1")
        cls.m2 = Manufacturer.objects.create(name="OL Mfg 2")

    def test_lock_creates_claim_with_server_derived_attribution(self):
        lock = ObjectLock.objects.lock(self.m1, reason="sync", source_key="job-1", requesting_user=self.user)
        self.assertEqual(lock.created_by, self.user)
        self.assertEqual(lock.locked_object, self.m1)
        self.assertTrue(lock.prevent_delete)
        # source_context is derived; defaults to ORM when no change context is active
        self.assertEqual(lock.source_context, ObjectChangeEventContextChoices.CONTEXT_ORM)

    def test_lock_is_idempotent_per_source_key(self):
        ObjectLock.objects.lock(self.m1, source_key="k", requesting_user=self.user)
        again = ObjectLock.objects.lock(self.m1, reason="updated", source_key="k", requesting_user=self.user)
        self.assertEqual(ObjectLock.objects.for_object(self.m1).count(), 1)
        self.assertEqual(again.reason, "updated")

    def test_lock_generates_run_unique_source_key_when_omitted(self):
        a = ObjectLock.objects.lock(self.m1, requesting_user=self.user)
        b = ObjectLock.objects.lock(self.m2, requesting_user=self.user)
        self.assertTrue(a.source_key)
        self.assertNotEqual(a.source_key, b.source_key)

    def test_caller_supplied_auto_prefixed_source_key_is_rejected(self):
        """A caller-facing lock may not supply a source_key with the reserved 'auto:' prefix."""
        with self.assertRaises(ValidationError):
            ObjectLock.objects.lock(self.m1, prevent_delete=True, source_key="auto:evil", requesting_user=self.user)

    def test_lock_rejects_unsaved_target(self):
        """Object Lock protects existing objects; locking an unsaved instance is rejected, not orphaned."""
        with self.assertRaises(ValidationError):
            ObjectLock.objects.lock(Manufacturer(name="Unsaved Mfr"), prevent_delete=True, requesting_user=self.user)

    def test_cross_owner_source_key_reuse_is_blocked(self):
        """Reusing another source's source_key to weaken its claim requires force_release."""
        other = get_user_model().objects.create_user(username="ol-other-owner")
        ObjectLock.objects.lock(self.m1, prevent_delete=True, source_key="shared", requesting_user=other)
        with self.assertRaises(ValidationError):
            ObjectLock.objects.lock(
                self.m1, prevent_delete=False, prevent_update=True, source_key="shared", requesting_user=self.user
            )
        # The original claim is untouched — still owned by `other`, still delete-locked.
        claim = ObjectLock.objects.for_object(self.m1).get(source_key="shared")
        self.assertEqual(claim.created_by, other)
        self.assertTrue(claim.prevent_delete)

    def test_owner_refresh_preserves_attribution(self):
        """An owner refreshing their own claim updates mutable fields but never rewrites attribution."""
        original = ObjectLock.objects.lock(self.m1, reason="first", source_key="mine", requesting_user=self.user)
        refreshed = ObjectLock.objects.lock(self.m1, reason="second", source_key="mine", requesting_user=self.user)
        self.assertEqual(refreshed.pk, original.pk)
        self.assertEqual(refreshed.reason, "second")
        self.assertEqual(refreshed.created_by, self.user)

    def test_force_release_holder_may_reuse_key_attribution_preserved(self):
        """A force_release holder may reuse another source's key; attribution still isn't rewritten."""
        other = get_user_model().objects.create_user(username="ol-other-owner-2")
        ObjectLock.objects.lock(self.m2, prevent_delete=True, source_key="shared2", requesting_user=other)
        forcer = get_user_model().objects.create_superuser(username="ol-forcer")
        refreshed = ObjectLock.objects.lock(
            self.m2, prevent_delete=False, prevent_update=True, source_key="shared2", requesting_user=forcer
        )
        self.assertFalse(refreshed.prevent_delete)
        self.assertEqual(refreshed.created_by, other)  # original owner preserved, not the forcer

    def test_lock_rejects_non_uuid_pk_target(self):
        bad = ScheduledJobs(ident=1)
        with self.assertRaises(TypeError):
            ObjectLock.objects.lock(bad, requesting_user=self.user)

    def test_lock_rejects_non_basemodel_target(self):
        class PlainModel:
            pk = 1

        with self.assertRaises(TypeError):
            ObjectLock.objects.lock(PlainModel(), requesting_user=self.user)

    @override_settings(OBJECT_LOCK_DEFAULT_TTL=3600)
    def test_lock_applies_default_ttl_when_expires_omitted(self):
        lock = ObjectLock.objects.lock(self.m1, requesting_user=self.user)
        self.assertIsNotNone(lock.expires)

    @override_settings(OBJECT_LOCK_DEFAULT_TTL=3600)
    def test_lock_honors_explicit_indefinite_expiry(self):
        lock = ObjectLock.objects.lock(self.m1, expires=None, requesting_user=self.user, _expires_explicit=True)
        self.assertIsNone(lock.expires)

    def test_release_removes_only_named_source_claim(self):
        ObjectLock.objects.lock(self.m1, source_key="a", requesting_user=self.user)
        ObjectLock.objects.lock(self.m1, source_key="b", requesting_user=self.user)
        ObjectLock.objects.release(self.m1, source_key="a")
        remaining = list(ObjectLock.objects.for_object(self.m1).values_list("source_key", flat=True))
        self.assertEqual(remaining, ["b"])

    def test_lock_many_and_release_many(self):
        locks = ObjectLock.objects.lock_many([self.m1, self.m2], source_key="batch", requesting_user=self.user)
        self.assertEqual(len(locks), 2)
        ObjectLock.objects.release_many([self.m1, self.m2], source_key="batch")
        self.assertEqual(ObjectLock.objects.count(), 0)


class ObjectLockGateTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="gate-user")
        cls.m1 = Manufacturer.objects.create(name="Gate Mfg")
        cls.ct_id = ContentType.objects.get_for_model(Manufacturer).id

    def setUp(self):
        invalidate_gate_cache()

    def test_lock_created_mid_context_blocks_later_write_in_same_context(self):
        """A lock created mid-request must be honored by a later write in the same change context."""
        with web_request_context(self.user):
            # Prime the per-context gate snapshot with an enforced (allowed) write while still unlocked.
            self.m1.description = "before lock"
            self.m1.save()
            ObjectLock.objects.lock(self.m1, prevent_update=True, requesting_user=self.user, source_key="mid-ctx")
            self.m1.description = "after lock"
            with self.assertRaises(ObjectLockedError):
                self.m1.save()

    def test_empty_gate_contains_nothing(self):
        gate = get_gate()
        self.assertEqual(gate[GATE_MODE_DELETE], frozenset())
        self.assertEqual(gate[GATE_MODE_UPDATE], frozenset())

    def test_delete_lock_appears_in_delete_gate_only(self):
        ObjectLock.objects.lock(self.m1, prevent_delete=True, prevent_update=False, requesting_user=self.user)
        invalidate_gate_cache()
        gate = get_gate()
        self.assertIn(self.ct_id, gate[GATE_MODE_DELETE])
        self.assertNotIn(self.ct_id, gate[GATE_MODE_UPDATE])

    def test_update_lock_appears_in_update_gate(self):
        ObjectLock.objects.lock(self.m1, prevent_delete=False, prevent_update=True, requesting_user=self.user)
        invalidate_gate_cache()
        gate = get_gate()
        self.assertIn(self.ct_id, gate[GATE_MODE_UPDATE])

    def test_gate_rebuilds_from_db_on_cache_flush(self):
        ObjectLock.objects.lock(self.m1, requesting_user=self.user)
        invalidate_gate_cache()  # simulate a Redis flush of the gate keys
        gate = get_gate()
        self.assertIn(self.ct_id, gate[GATE_MODE_DELETE])

    def test_redis_exception_fails_closed_not_open(self):
        """On a Redis ConnectionError the gate must rebuild from DB, never return 'nothing locked'."""
        ObjectLock.objects.lock(self.m1, requesting_user=self.user)
        invalidate_gate_cache()

        with patch("nautobot.extras.locking.cache") as mock_cache:
            mock_cache.get.side_effect = redis.exceptions.ConnectionError("redis down")
            gate = get_gate()

        # Must still see the lock — fail CLOSED, not open.
        self.assertIn(self.ct_id, gate[GATE_MODE_DELETE])


class ObjectLockTokenBumpTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="token-user")
        cls.m1 = Manufacturer.objects.create(name="Token Mfg")

    def test_token_increments_on_lock_create(self):
        before = _current_token()
        ObjectLock.objects.lock(self.m1, source_key="t", requesting_user=self.user)
        self.assertGreater(_current_token(), before)

    def test_token_increments_on_lock_release(self):
        ObjectLock.objects.lock(self.m1, source_key="t", requesting_user=self.user)
        before = _current_token()
        ObjectLock.objects.release(self.m1, source_key="t")
        self.assertGreater(_current_token(), before)


class EnforceObjectLockFunctionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="enforce-user")
        cls.locked = Manufacturer.objects.create(name="Locked Mfg")
        cls.unlocked = Manufacturer.objects.create(name="Unlocked Mfg")

    def setUp(self):
        invalidate_gate_cache()

    def test_no_lock_means_no_raise(self):
        # Should be a no-op (gate miss) for an unlocked object — must NOT query the ObjectLock table.
        # Pre-warm the gate cache so only the generation-token check (1 query) occurs.
        get_gate()
        with self.assertNumQueries(1):
            # Exactly 1 query: the generation-token freshness check in get_gate().
            # No ObjectLock table scan should happen because the content type is not in the gate.
            enforce_object_lock(Manufacturer, self.unlocked, GATE_MODE_DELETE)

    def test_delete_locked_object_raises_on_delete_mode(self):
        ObjectLock.objects.lock(self.locked, prevent_delete=True, requesting_user=self.user)
        invalidate_gate_cache()
        with self.assertRaises(ObjectLockedError):
            enforce_object_lock(Manufacturer, self.locked, GATE_MODE_DELETE)

    def test_delete_locked_object_does_not_raise_on_update_mode(self):
        ObjectLock.objects.lock(self.locked, prevent_delete=True, prevent_update=False, requesting_user=self.user)
        invalidate_gate_cache()
        # Update mode should not trip on a delete-only lock.
        enforce_object_lock(Manufacturer, self.locked, GATE_MODE_UPDATE)

    def test_gate_hit_but_live_query_empty_does_not_raise(self):
        # Lock a *different* object of the same type, then check the unlocked one:
        ObjectLock.objects.lock(self.locked, prevent_delete=True, requesting_user=self.user)
        invalidate_gate_cache()
        # self.unlocked is the same content type (gate hit) but has no claim (live query empty) -> no raise.
        enforce_object_lock(Manufacturer, self.unlocked, GATE_MODE_DELETE)


class GateSnapshotPerRequestTestCase(TestCase):
    """Gate is resolved once per request/job, not once per object."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="snapshot-user")
        cls.m1 = Manufacturer.objects.create(name="Snapshot Mfg 1")
        cls.m2 = Manufacturer.objects.create(name="Snapshot Mfg 2")
        cls.m3 = Manufacturer.objects.create(name="Snapshot Mfg 3")

    def setUp(self):
        invalidate_gate_cache()

    def test_repeated_get_gate_calls_within_context_cost_one_token_query(self):
        """Within a change context, N calls to get_gate() must issue exactly one token query — not N.

        The first call pays the full compute cost (token query + cache/DB).  The second and
        subsequent calls return the snapshot from the context object with zero additional queries.
        """
        with web_request_context(self.user) as _request:
            ctx = change_context_state.get()
            # Ensure no stale snapshot from a prior call.
            if hasattr(ctx, _GATE_SNAPSHOT_ATTR):
                delattr(ctx, _GATE_SNAPSHOT_ATTR)

            # Count queries for the first call alone (token check + possible cache rebuild).
            with CaptureQueriesContext(connection) as first_call_ctx:
                gate_first = get_gate()

            first_call_count = len(first_call_ctx.captured_queries)
            self.assertGreaterEqual(first_call_count, 1, "First get_gate() call must issue at least one DB query.")

            # Now call get_gate() 9 more times inside the same context — total N=10.
            # All subsequent calls must be free (zero additional queries): snapshot is already set.
            with self.assertNumQueries(0):
                for _ in range(9):
                    gate_n = get_gate()
                    self.assertEqual(gate_first, gate_n)

    def test_repeated_enforce_calls_within_context_do_not_repeat_token_query(self):
        """N enforce_object_lock() calls on unlocked-type objects inside one context cost 0 token queries after the first."""
        # No locks — gate is empty, so every enforce call hits the "not in gate" fast path.
        with web_request_context(self.user) as _request:
            ctx = change_context_state.get()
            if hasattr(ctx, _GATE_SNAPSHOT_ATTR):
                delattr(ctx, _GATE_SNAPSHOT_ATTR)

            # First enforce call: snapshot is absent, so get_gate() runs and pays the DB cost.
            # Subsequent calls: snapshot present, zero additional queries.
            # We measure the TOTAL query count for 5 enforce calls and assert it equals
            # the first-call cost (proving calls 2-5 are free).
            with CaptureQueriesContext(connection) as ctx_queries:
                for obj in [self.m1, self.m2, self.m3]:
                    enforce_object_lock(Manufacturer, obj, GATE_MODE_DELETE)
                    enforce_object_lock(Manufacturer, obj, GATE_MODE_UPDATE)

            # The ContentType lookup for Manufacturer is cached by Django's ContentType framework,
            # so after the first call it adds 0 queries.  The only DB queries are the token check
            # (once) and possibly a gate rebuild (once on cache miss).  With an empty cache, we
            # expect 2 queries total (token + rebuild path), never scaling with N.
            self.assertLessEqual(
                len(ctx_queries.captured_queries),
                4,  # generous upper bound: token + lock (rebuild), each up to twice in edge cases
                f"Expected at most 4 queries for 6 enforce calls, got {len(ctx_queries.captured_queries)}. "
                "Snapshot caching is not working — query count is scaling with N.",
            )

    def test_snapshot_is_not_shared_across_contexts(self):
        """A snapshot stale in context A must not leak into a fresh context B."""
        # Create a lock so the first context's gate sees a non-empty set.
        ObjectLock.objects.lock(self.m1, prevent_delete=True, requesting_user=self.user)
        invalidate_gate_cache()

        ct_id = ContentType.objects.get_for_model(Manufacturer).id

        # Context A: snapshot is taken with the lock present.
        with web_request_context(self.user) as _req_a:
            gate_a = get_gate()
            self.assertIn(ct_id, gate_a[GATE_MODE_DELETE], "Context A must see the lock.")

        # Release the lock and invalidate the cache so the next context loads a fresh gate.
        ObjectLock.objects.release(self.m1, source_key=ObjectLock.objects.for_object(self.m1).first().source_key)
        invalidate_gate_cache()

        # Context B: must NOT inherit context A's snapshot; the lock is gone.
        with web_request_context(self.user) as _req_b:
            gate_b = get_gate()
            self.assertNotIn(ct_id, gate_b[GATE_MODE_DELETE], "Context B must NOT see a stale snapshot from context A.")

    def test_no_context_computes_gate_fresh_each_call(self):
        """Without an active change context, get_gate() computes fresh on each call (out-of-band path)."""
        # Verify there is truly no context active.
        self.assertIsNone(change_context_state.get())

        # Call get_gate() twice; each should issue queries (no caching on None context).
        with CaptureQueriesContext(connection) as first:
            get_gate()

        with CaptureQueriesContext(connection) as second:
            get_gate()

        # Both calls cost the same (non-zero) amount.  If snapshot caching were incorrectly
        # applied here, the second call would be free and the assertion below would fail.
        self.assertGreater(len(first.captured_queries), 0, "Out-of-band first call must issue queries.")
        self.assertGreater(len(second.captured_queries), 0, "Out-of-band second call must also issue queries.")


class GateSnapshotFailClosedTestCase(TestCase):
    """Fail-closed behavior still holds on the first compute inside a context."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="failclosed-user")
        cls.m1 = Manufacturer.objects.create(name="FailClosed Mfg")

    def setUp(self):
        invalidate_gate_cache()

    def test_cache_error_on_first_call_within_context_still_returns_real_gate(self):
        """If cache.get raises inside a context, the first get_gate() still rebuilds from DB (fail-closed)."""
        ct_id = ContentType.objects.get_for_model(Manufacturer).id
        ObjectLock.objects.lock(self.m1, prevent_delete=True, requesting_user=self.user)

        with web_request_context(self.user) as _request:
            ctx = change_context_state.get()
            # Ensure no stale snapshot.
            if hasattr(ctx, _GATE_SNAPSHOT_ATTR):
                delattr(ctx, _GATE_SNAPSHOT_ATTR)

            with patch("nautobot.extras.locking.cache") as mock_cache:
                mock_cache.get.side_effect = redis.exceptions.ConnectionError("redis down")

                gate = get_gate()

            # Must still see the lock — fail CLOSED, not open.
            self.assertIn(
                ct_id, gate[GATE_MODE_DELETE], "Fail-closed: gate must reflect real DB state even on cache error."
            )

            # Snapshot must have been stored so the next call is free.
            self.assertIsNotNone(
                getattr(ctx, _GATE_SNAPSHOT_ATTR, None), "Snapshot must be stored after fail-closed rebuild."
            )


class ObjectLockSignalEnforcementTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="signal-user", is_superuser=True)

    def setUp(self):
        invalidate_gate_cache()

    def test_delete_blocked_when_delete_locked(self):
        mfg = Manufacturer.objects.create(name="Sig Delete Mfg")
        ObjectLock.objects.lock(mfg, prevent_delete=True, requesting_user=self.user)
        invalidate_gate_cache()
        with web_request_context(self.user):
            with self.assertRaises(ObjectLockedError):
                with transaction.atomic():
                    mfg.delete()
        self.assertTrue(Manufacturer.objects.filter(pk=mfg.pk).exists())

    def test_update_blocked_when_update_locked(self):
        mfg = Manufacturer.objects.create(name="Sig Update Mfg")
        ObjectLock.objects.lock(mfg, prevent_update=True, requesting_user=self.user)
        invalidate_gate_cache()
        with web_request_context(self.user):
            mfg.description = "changed"
            with self.assertRaises(ObjectLockedError):
                mfg.save()

    def test_create_of_locked_type_is_allowed(self):
        # Lock an existing manufacturer for update; creating a NEW manufacturer must still work.
        existing = Manufacturer.objects.create(name="Sig Existing Mfg")
        ObjectLock.objects.lock(existing, prevent_update=True, requesting_user=self.user)
        invalidate_gate_cache()
        with web_request_context(self.user):
            Manufacturer.objects.create(name="Sig Brand New Mfg")  # must not raise

    def test_delete_only_lock_allows_update(self):
        mfg = Manufacturer.objects.create(name="Sig DelOnly Mfg")
        ObjectLock.objects.lock(mfg, prevent_delete=True, prevent_update=False, requesting_user=self.user)
        invalidate_gate_cache()
        with web_request_context(self.user):
            mfg.description = "ok to edit"
            mfg.save()  # must not raise

    def test_no_change_context_is_permitted_bypass(self):
        mfg = Manufacturer.objects.create(name="Sig NoCtx Mfg")
        ObjectLock.objects.lock(mfg, prevent_delete=True, requesting_user=self.user)
        invalidate_gate_cache()
        # No web_request_context => no change context => permitted bypass, delete succeeds.
        mfg.delete()
        self.assertFalse(Manufacturer.objects.filter(pk=mfg.pk).exists())

    @override_settings(OBJECT_LOCK_ENFORCED=False)
    def test_kill_switch_disables_enforcement(self):
        mfg = Manufacturer.objects.create(name="Sig Kill Mfg")
        ObjectLock.objects.lock(mfg, prevent_delete=True, requesting_user=self.user)
        invalidate_gate_cache()
        with web_request_context(self.user):
            mfg.delete()  # kill switch on => no enforcement
        self.assertFalse(Manufacturer.objects.filter(pk=mfg.pk).exists())

    @override_settings(OBJECT_LOCK_ENFORCED=False)
    def test_kill_switch_short_circuits_before_cache_access(self):
        """Kill switch returns before any cache access, so it works even when Redis is down.

        If the enforcement signal checked the kill switch AFTER a cache call, the patched
        cache below would raise ConnectionError and the delete would fail.  A clean delete
        proves the kill switch fires before the cache is ever touched.
        """
        mfg = Manufacturer.objects.create(name="Sig KillSwitch NoCacheAccess Mfg")
        # Set up the lock while the cache is working.
        ObjectLock.objects.lock(mfg, prevent_delete=True, requesting_user=self.user)
        invalidate_gate_cache()

        with patch("nautobot.extras.locking.cache") as mock_cache:
            mock_cache.get.side_effect = redis.exceptions.ConnectionError("redis down")
            mock_cache.lock.side_effect = redis.exceptions.ConnectionError("redis down")
            with web_request_context(self.user):
                # Must succeed: OBJECT_LOCK_ENFORCED=False causes an early return in the
                # signal handler before any call to nautobot.extras.locking.cache.
                mfg.delete()

        self.assertFalse(Manufacturer.objects.filter(pk=mfg.pk).exists())
        # Cache was never consulted — the kill switch exited the signal before get_gate().
        mock_cache.get.assert_not_called()

    def test_saving_objectlock_does_not_recurse(self):
        """ObjectLock writes are exempt from enforcement so they never re-enter the signal.

        If the exemption were absent, creating / updating / deleting an ObjectLock inside a
        web_request_context would trigger the enforcement signal recursively and could raise
        ObjectLockedError or hit a stack overflow.
        """
        with web_request_context(self.user):
            # Create: must not raise ObjectLockedError or recurse.
            lock = ObjectLock.objects.lock(
                self.user,  # any UUID-PK BaseModel works; User is convenient and always present
                prevent_delete=True,
                reason="initial",
                source_key="no-recurse-test",
                requesting_user=self.user,
            )
            self.assertTrue(lock.pk)

            # Update (re-lock same source_key, different reason): must also complete cleanly.
            updated = ObjectLock.objects.lock(
                self.user,
                prevent_delete=True,
                reason="updated",
                source_key="no-recurse-test",
                requesting_user=self.user,
            )
            self.assertEqual(updated.pk, lock.pk)
            self.assertEqual(updated.reason, "updated")

            # Release (delete the ObjectLock row): must not re-enter enforcement.
            ObjectLock.objects.release(self.user, source_key="no-recurse-test")

        self.assertFalse(ObjectLock.objects.filter(pk=lock.pk).exists())


class ObjectLockBypassTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = get_user_model().objects.create_user(username="bypass-super", is_superuser=True)
        cls.plain = get_user_model().objects.create_user(username="bypass-plain")

    def setUp(self):
        invalidate_gate_cache()

    def test_flag_defaults_false(self):
        self.assertFalse(is_bypass_active())

    def test_bypass_sets_and_resets_flag(self):
        with web_request_context(self.superuser):
            with bypass_object_lock():
                self.assertTrue(is_bypass_active())
            self.assertFalse(is_bypass_active())

    def test_bypass_resets_flag_on_exception(self):
        with web_request_context(self.superuser):
            try:
                with bypass_object_lock():
                    raise RuntimeError("boom")
            except RuntimeError:
                pass
            self.assertFalse(is_bypass_active())

    def test_bypass_allows_modifying_update_locked_object(self):
        mfg = Manufacturer.objects.create(name="Bypass Mfg")
        ObjectLock.objects.lock(mfg, prevent_update=True, requesting_user=self.superuser)
        invalidate_gate_cache()
        with web_request_context(self.superuser):
            with bypass_object_lock():
                mfg.description = "edited under bypass"
                mfg.save()  # must not raise
        mfg.refresh_from_db()
        self.assertEqual(mfg.description, "edited under bypass")

    def test_bypass_denied_without_permission(self):
        with web_request_context(self.plain):
            with self.assertRaises(PermissionDenied):
                with bypass_object_lock():
                    pass

    def test_bypass_writes_audit_record(self):
        """Modifying a locked object under bypass writes an ObjectLockBypassAudit row."""
        mfg = Manufacturer.objects.create(name="Bypass Audit Mfg")
        ObjectLock.objects.lock(mfg, prevent_update=True, source_key="audit-src", requesting_user=self.superuser)
        invalidate_gate_cache()
        before_count = ObjectLockBypassAudit.objects.count()
        with web_request_context(self.superuser):
            with bypass_object_lock():
                mfg.description = "bypassed"
                mfg.save()
        after_count = ObjectLockBypassAudit.objects.count()
        self.assertEqual(after_count, before_count + 1)
        audit = ObjectLockBypassAudit.objects.order_by("-time").first()
        self.assertEqual(audit.user, self.superuser)
        self.assertEqual(audit.object_id, mfg.pk)
        self.assertIn("audit-src", audit.suspended_source_keys)

    def test_bypass_audit_log_emitted(self):
        """bypass_object_lock() always logs an INFO message on entry."""
        with self.assertLogs("nautobot.extras.locking", level="INFO") as cm:
            with web_request_context(self.superuser):
                with bypass_object_lock():
                    pass
        self.assertTrue(any("Object Lock bypass" in line for line in cm.output))

    def test_no_bypass_enforcement_still_blocks(self):
        """Without bypass_object_lock(), a write to an update-locked object raises ObjectLockedError."""
        mfg = Manufacturer.objects.create(name="Bypass Enforcement Mfg")
        ObjectLock.objects.lock(mfg, prevent_update=True, requesting_user=self.superuser)
        invalidate_gate_cache()
        with web_request_context(self.superuser):
            mfg.description = "should be blocked"
            with self.assertRaises(ObjectLockedError):
                mfg.save()


class ObjectLockContextManagerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="ctx-user")
        cls.m1 = Manufacturer.objects.create(name="Ctx Mfg 1")
        cls.m2 = Manufacturer.objects.create(name="Ctx Mfg 2")

    def test_locked_single_object_locks_then_releases(self):
        with ObjectLock.objects.locked(self.m1, reason="work", source_key="ctx", requesting_user=self.user):
            self.assertEqual(ObjectLock.objects.for_object(self.m1).count(), 1)
        self.assertEqual(ObjectLock.objects.for_object(self.m1).count(), 0)

    def test_locked_iterable_locks_all_then_releases_all(self):
        with ObjectLock.objects.locked([self.m1, self.m2], source_key="ctx", requesting_user=self.user):
            self.assertEqual(ObjectLock.objects.count(), 2)
        self.assertEqual(ObjectLock.objects.count(), 0)

    def test_locked_releases_on_exception(self):
        with self.assertRaises(RuntimeError):
            with ObjectLock.objects.locked(self.m1, source_key="ctx", requesting_user=self.user):
                raise RuntimeError("boom")
        self.assertEqual(ObjectLock.objects.for_object(self.m1).count(), 0)


class ObjectLockSweepTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="sweep-user", is_superuser=True)

    def _run_sweep(self):
        return purge_expired_and_orphaned_locks()

    def test_expired_lock_is_purged(self):
        mfg = Manufacturer.objects.create(name="Sweep Expired Mfg")
        lock = ObjectLock.objects.lock(mfg, source_key="exp", requesting_user=self.user)
        # Force it expired in the past.
        ObjectLock.objects.filter(pk=lock.pk).update(expires=timezone.now() - timezone.timedelta(hours=1))
        purged = self._run_sweep()
        self.assertEqual(ObjectLock.objects.count(), 0)
        self.assertGreaterEqual(purged["expired"], 1)

    def test_unexpired_lock_is_kept(self):
        mfg = Manufacturer.objects.create(name="Sweep Keep Mfg")
        ObjectLock.objects.lock(
            mfg, source_key="keep", expires=timezone.now() + timezone.timedelta(hours=1), requesting_user=self.user
        )
        self._run_sweep()
        self.assertEqual(ObjectLock.objects.count(), 1)

    def test_orphaned_lock_is_purged(self):
        mfg = Manufacturer.objects.create(name="Sweep Orphan Mfg")
        ObjectLock.objects.lock(
            mfg, source_key="orphan", expires=timezone.now() + timezone.timedelta(days=1), requesting_user=self.user
        )
        # Delete the target out-of-band (no change context => permitted bypass) to orphan the lock.
        Manufacturer.objects.filter(pk=mfg.pk).delete()
        purged = self._run_sweep()
        self.assertEqual(ObjectLock.objects.count(), 0)
        self.assertGreaterEqual(purged["orphaned"], 1)

    def test_per_content_type_failure_does_not_abort_sweep(self):
        """A failure purging one content type is logged + counted, not propagated."""
        mfg = Manufacturer.objects.create(name="Sweep Fail Mfg")
        ObjectLock.objects.lock(mfg, source_key="f", requesting_user=self.user)
        Manufacturer.objects.filter(pk=mfg.pk).delete()  # orphan it
        with mock.patch(
            "nautobot.extras.jobs_object_lock_sweep.ContentType.objects.get_for_id",
            side_effect=Exception("simulated content-type failure"),
        ):
            result = self._run_sweep()  # must not raise
        self.assertEqual(result["failed_content_types"], 1)
        self.assertEqual(ObjectLock.objects.count(), 1)  # the orphan survived its CT's failure, gracefully


class ObjectLockAdminTestCase(TestCase):
    def test_objectlock_registered_in_admin(self):
        self.assertIn(ObjectLock, admin.site._registry)

    def test_bypass_audit_registered_in_admin(self):
        """The bypass audit must have a (read-only) admin surface."""
        self.assertIn(ObjectLockBypassAudit, admin.site._registry)

    def test_objectlock_admin_is_read_only(self):
        """Locks are view-only in admin; add/change/delete are disabled."""
        model_admin = admin.site._registry[ObjectLock]
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None))
        self.assertFalse(model_admin.has_delete_permission(None))


class ObjectLockPerformanceTestCase(TestCase):
    """Zero-overhead invariants encoded as query-count assertions (NOT wall-clock).

    These prove the *enforcement* hot path imposes no measurable cost on the common case:
    writes against unlocked types and writes while the kill switch is off must not touch the
    ObjectLock lock-records table, and the per-request gate snapshot must read the
    generation token at most once regardless of how many writes a request performs.

    Scope note — why these measure the enforcement entrypoint, not a full ``save()``:
    a changelogged ``save()`` serializes the object into an ``ObjectChange`` via
    ``serialize_object_v2`` (extras.signals._handle_changed_object -> to_objectchange).  That
    serialization renders ``ObjectLockableSerializerMixin.get_is_locked``, which issues ONE
    ``extras_objectlock`` lock-records query per changelogged object — independent of enforcement
    and independent of ``OBJECT_LOCK_ENFORCED``.  That per-object serializer query is a separate,
    already-tracked concern (``_claims_for`` in ``nautobot/extras/api/object_locks.py`` issues one
    lock query per object on the request-present read path; it could be batched via serializer
    context).  Wrapping
    a full ``save()`` here would conflate that unrelated read into the enforcement benchmark, so we
    invoke the enforcement decision (``enforce_object_lock`` / the ``pre_save`` receiver) directly —
    exactly what the receivers call — to isolate the enforcement-overhead invariant.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="perf-user", is_superuser=True)

    def setUp(self):
        invalidate_gate_cache()

    def test_unlocked_type_write_does_no_object_lock_query(self):
        """Enforcing a write on an unlocked-type object hits the gate (set test) but issues no lock-records query."""
        with web_request_context(self.user):
            mfg = Manufacturer.objects.create(name="Perf Warm Mfg")
            # Warm the per-request gate snapshot so the generation-token read is already amortized;
            # what remains to measure is whether the enforcement decision itself touches the
            # lock-records table for an unlocked content type.
            get_gate()
            with CaptureQueriesContext(connection) as ctx:
                # This is exactly the call the pre_save receiver makes for an update.
                enforce_object_lock(Manufacturer, mfg, GATE_MODE_UPDATE)
        # PRECISE filter: target ONLY the lock-records table ("extras_objectlock"), and EXCLUDE the
        # generation-token table ("extras_objectlockgeneration") and the bypass-audit table
        # ("extras_objectlockbypassaudit").  A naive `"extras_objectlock" in sql` substring match
        # would also match those two sibling tables.  The invariant is "zero ObjectLock DB
        # queries BEYOND the gate snapshot" — the gate snapshot reads the generation token, which is
        # explicitly permitted, so we must not count it here.  What must NOT appear is a query against
        # the lock-records table, which would mean _active_claims ran instead of short-circuiting on
        # the in-memory gate set-membership test (`content_type_id not in gate[mode]`).
        object_lock_queries = [
            q
            for q in ctx.captured_queries
            if '"extras_objectlock"' in q["sql"]
            and "extras_objectlockgeneration" not in q["sql"]
            and "extras_objectlockbypassaudit" not in q["sql"]
        ]
        self.assertEqual(object_lock_queries, [], f"Unexpected ObjectLock lock-records queries: {object_lock_queries}")

    @override_settings(OBJECT_LOCK_ENFORCED=False)
    def test_kill_switch_skips_gate_entirely(self):
        """With the kill switch off, the receiver reads NOTHING object-lock-related — not even the gate token."""
        with web_request_context(self.user):
            mfg = Manufacturer.objects.create(name="Perf Kill Mfg")
            with CaptureQueriesContext(connection) as ctx:
                # Invoke the real pre_save receiver. With OBJECT_LOCK_ENFORCED=False it must return
                # at the kill-switch check before any get_gate() / cache / DB access.
                _object_lock_enforce_update(sender=Manufacturer, instance=mfg)
        # BROAD filter (intentionally): match ANY object-lock table, INCLUDING the generation-token
        # table.  The receiver checks the kill switch FIRST and returns before calling get_gate(),
        # so when enforcement is disabled it must read NOTHING object-lock-related — not even the
        # gate snapshot token.  Counting the generation table here is correct and desirable: the
        # kill-switch path must not even read the token.
        object_lock_queries = [q for q in ctx.captured_queries if "extras_objectlock" in q["sql"]]
        self.assertEqual(object_lock_queries, [], f"Kill switch leaked object-lock queries: {object_lock_queries}")

    def test_gate_snapshot_taken_once_per_request(self):
        """The gate token is read at most once per request, not once per write.

        Across many enforcement decisions inside a single change context, the per-request gate
        snapshot is computed on the first get_gate() call and cached on the context object; every
        later decision reuses it.  Without the snapshot we would expect one generation-token read
        per decision (here N reads); with it we expect <= 1 read amortized across all of them.
        """
        # No locks exist, so every decision hits the "not in gate" fast path. Three distinct
        # objects, each enforced for both modes => 6 enforcement decisions in ONE request.
        mfgs = [Manufacturer.objects.create(name=f"Perf Snapshot Mfg {i}") for i in range(3)]
        with web_request_context(self.user):
            with CaptureQueriesContext(connection) as ctx:
                for mfg in mfgs:
                    enforce_object_lock(Manufacturer, mfg, GATE_MODE_UPDATE)
                    enforce_object_lock(Manufacturer, mfg, GATE_MODE_DELETE)
        # Count reads against the generation-token table only.  The per-request snapshot must read it
        # at most once no matter how many decisions occurred; a count > 1 means the snapshot is not
        # being reused and the token is re-read per write.  (Without the per-request snapshot,
        # _compute_gate would run on every call and we would observe one token read per decision — here 6.)
        token_reads = [q for q in ctx.captured_queries if "extras_objectlockgeneration" in q["sql"]]
        self.assertLessEqual(
            len(token_reads),
            1,
            f"Gate token read {len(token_reads)} times across 6 enforcement decisions; expected <= 1 "
            f"(per-request snapshot not reused). Queries: {token_reads}",
        )

    def test_changelogged_save_of_locked_object_does_no_serializer_lock_query(self):
        """A changelogged save serializes the object but must NOT query the lock-records table.

        The change-log path serializes every changelogged object with ``request=None``
        (``serialize_object_v2`` -> serializer with ``context={"request": None, ...}``).
        ``ObjectLockableSerializerMixin`` (carried by ``ManufacturerSerializer``) renders four
        lock-state fields whose getters previously called ``_claims_for``, issuing ONE
        ``extras_objectlock`` lock-records query per changelogged object — even for a locked object,
        and regardless of enforcement.  Lock state is request-contextual and has no place in a
        change-log snapshot, so with no request in the serializer context the getters must
        short-circuit and issue zero lock-records queries.

        The object IS locked here (with ``prevent_update=False`` so the update itself is allowed and
        the change-log serializer actually runs) to prove the serializer skips the query even when a
        live claim exists.
        """
        mfg = Manufacturer.objects.create(name="Perf ChangeLog Mfg")
        # Lock for DELETE only (prevent_update=False) so the save() is NOT blocked by enforcement;
        # we want the changelogged save to proceed and exercise the change-log serializer.
        ObjectLock.objects.lock(mfg, prevent_delete=True, prevent_update=False, requesting_user=self.user)
        invalidate_gate_cache()

        with web_request_context(self.user):
            mfg.description = "changed to trigger a changelogged update"
            # Warm the per-request gate snapshot BEFORE measuring. The first get_gate() after a
            # cache flush rebuilds the gate by scanning the lock-records table (_compute_gate) —
            # an enforcement query that would otherwise land in the capture window and mask what
            # we are isolating. The sibling enforcement perf tests warm the gate for the same
            # reason. After warm-up, the only lock-records query a save() could add is the
            # per-object claim query from the change-log serializer — which is what we assert
            # against.
            get_gate()
            with CaptureQueriesContext(connection) as ctx:
                mfg.save()  # changelogged update -> serialize_object_v2 -> serializer lock fields

        # SAME precise filter as the enforcement perf tests: target ONLY the lock-records table and
        # exclude the generation-token and bypass-audit sibling tables.  The change-log serializer
        # must not touch the lock-records table at all when serializing without a request context.
        object_lock_queries = [
            q
            for q in ctx.captured_queries
            if '"extras_objectlock"' in q["sql"]
            and "extras_objectlockgeneration" not in q["sql"]
            and "extras_objectlockbypassaudit" not in q["sql"]
        ]
        self.assertEqual(
            object_lock_queries,
            [],
            f"Change-log serialization issued lock-records queries: {object_lock_queries}",
        )


class ObjectLockDetailAffordanceRenderTestCase(TestCase):
    """The locked-detail Edit/Delete affordances respect can_change/can_delete."""

    @classmethod
    def setUpTestData(cls):
        cls.ct = ContentType.objects.get_for_model(Manufacturer)
        cls.mfg = Manufacturer.objects.create(name="Affordance Mfg")
        ObjectLock.objects.create(
            content_type=cls.ct,
            object_id=cls.mfg.pk,
            prevent_delete=True,
            prevent_update=True,
            reason="m3",
            source_key="m3",
            expires=timezone.now() + timezone.timedelta(days=1),
        )

    def _grant(self, user, *actions):
        for action in actions:
            perm = ObjectPermission.objects.create(name=f"m3-{action}-{user.pk}", actions=[action])
            perm.object_types.set([self.ct])
            perm.users.add(user)

    def _detail_html(self, user):
        self.client.force_login(user)
        response = self.client.get(self.mfg.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        return response.content.decode(response.charset)

    def test_view_only_user_sees_no_lock_affordances(self):
        user = get_user_model().objects.create_user(username="m3-viewonly")
        self._grant(user, "view")
        self.assertNotIn("data-nb-object-lock-blocked", self._detail_html(user))

    def test_change_and_delete_user_sees_blocked_affordances(self):
        user = get_user_model().objects.create_user(username="m3-editor")
        self._grant(user, "view", "change", "delete")
        html = self._detail_html(user)
        self.assertIn('data-nb-object-lock-blocked="edit"', html)
        self.assertIn('data-nb-object-lock-blocked="delete"', html)
