"""Migration tests for Object Lock (extras.0143_objectlock)."""

from django_test_migrations.contrib.unittest_case import MigratorTestCase


class ObjectLock0143ForwardTestCase(MigratorTestCase):
    """0143 creates the Object Lock models and seeds the singleton generation token.

    The reverse is ``migrations.RunPython.noop`` (plus the auto-generated table drops), which is safe
    because the tables are removed wholesale on reverse — there is no data to restore.
    """

    migrate_from = [("extras", "0142_remove_scheduledjob_approval_required")]
    migrate_to = [("extras", "0143_objectlock")]

    def test_generation_token_seeded(self):
        """seed_generation_token must create the singleton pk=1 row with token 0."""
        ObjectLockGeneration = self.new_state.apps.get_model("extras", "ObjectLockGeneration")
        row = ObjectLockGeneration.objects.get(pk=1)
        self.assertEqual(row.token, 0)

    def test_models_created_empty(self):
        """The lock and bypass-audit tables exist post-migration and start empty."""
        ObjectLock = self.new_state.apps.get_model("extras", "ObjectLock")
        ObjectLockBypassAudit = self.new_state.apps.get_model("extras", "ObjectLockBypassAudit")
        self.assertEqual(ObjectLock.objects.count(), 0)
        self.assertEqual(ObjectLockBypassAudit.objects.count(), 0)
