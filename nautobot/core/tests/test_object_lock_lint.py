"""CI lint guarding the Object Lock bypass boundary.

Flags NEW raw-bulk call sites and pre_delete.disconnect spans not present in the allowlist.
When you intentionally add such a call, add its location to the matching allowlist set below
with a comment explaining why it is a permitted bypass.
"""

import os
import re

from django.test import SimpleTestCase

import nautobot

NAUTOBOT_ROOT = os.path.dirname(os.path.abspath(nautobot.__file__))

# Patterns that constitute a raw-bulk / signal-disconnect bypass.
RAW_BULK_PATTERN = re.compile(r"\.(bulk_update|bulk_create)\(|\._raw_delete\(")
DISCONNECT_PATTERN = re.compile(r"pre_delete\.disconnect\(")

# Allowlisted bypass sites: each "relative/path.py" is permitted to contain raw-bulk usage.
# Keep this list tight; every entry is a deliberate, permitted bypass.
# NOTE: this allowlist is a coarse guard. Tighten file-by-file as needed.
RAW_BULK_ALLOWLIST = {
    # core maintenance jobs — documented bulk bypasses
    "core/jobs/cleanup.py",  # LogsCleanup _raw_delete (documented bypass)
    # extras infrastructure — change-logging helpers that batch-write ObjectChange records
    "extras/context_managers.py",  # deferred change logging bulk_create (design-permitted)
    "extras/customfields.py",  # custom-field migration helpers bulk_update/_update on _custom_field_data
    "extras/models/customfields.py",  # CustomField manager overrides — bulk_create/bulk_update wrappers
    "extras/models/groups.py",  # DynamicGroup._add_members — bulk_create of hidden StaticGroupAssociation rows
    "extras/models/mixins.py",  # ApprovableModelMixin.begin_approval_workflow — bulk_create of workflow stages
    "extras/utils.py",  # fixup_null_statuses / fixup_dynamic_group_group_types / bulk_delete helper
    # write-path / API — the REST bulk endpoint loops per object (perform_update fires pre_save), so locks
    # ARE enforced; it is allowlisted only because the regex matches the .bulk_update( method name.
    "core/api/views.py",  # REST bulk PATCH/PUT loops calling perform_update() per object -> pre_save fires
    # model save() paths — bulk_create of child components on new Device/Module creation
    "dcim/models/devices.py",  # Device.create_components / Module.create_components — template instantiation
    # IPAM maintenance jobs — Prefix/IPAddress parent-repair jobs
    "ipam/jobs/cleanup.py",  # FixIPAMParents job — bulk_update Prefix.parent / IPAddress.parent
    # IPAM model save() paths — Prefix/IPAddress reparent on save
    "ipam/models.py",  # Prefix.save / IPAddress.save — reparent children via bulk_update / .update()
    # IPAM migration helpers — one-time data-migration functions called from Django migrations
    "ipam/utils/migrations.py",  # namespace/VRF migration helpers — .update() / bulk_update on Prefix/IPAddress
}
DISCONNECT_ALLOWLIST = {
    # core maintenance jobs — documented signal-disconnect bypass
    "core/jobs/cleanup.py",  # LogsCleanup disconnects _handle_deleted_object (documented bypass)
    # DynamicGroup member removal — disconnects _handle_deleted_object for non-static group bulk-delete performance
    "extras/models/groups.py",  # DynamicGroup._remove_members — temporary disconnect for hidden SGA deletes
}


def _grep(pattern):
    """Return a set of 'relative/path.py' files containing the regex (Python files only)."""
    hits = set()
    for dirpath, _dirs, files in os.walk(NAUTOBOT_ROOT):
        if "/migrations" in dirpath or "/tests" in dirpath or "__pycache__" in dirpath:
            continue
        for fname in files:
            if not fname.endswith(".py"):
                continue
            full = os.path.join(dirpath, fname)
            with open(full, encoding="utf-8") as fh:
                content = fh.read()
            if pattern.search(content):
                hits.add(os.path.relpath(full, NAUTOBOT_ROOT))
    return hits


class ObjectLockBypassLintTestCase(SimpleTestCase):
    def test_no_unallowlisted_raw_bulk_call_sites(self):
        offenders = _grep(RAW_BULK_PATTERN) - RAW_BULK_ALLOWLIST
        self.assertEqual(
            offenders,
            set(),
            msg=(
                "New raw-bulk call site(s) detected that bypass Object Lock enforcement: "
                f"{sorted(offenders)}. If intentional, add it to RAW_BULK_ALLOWLIST "
                "with a justification comment."
            ),
        )

    def test_no_unallowlisted_pre_delete_disconnect_spans(self):
        offenders = _grep(DISCONNECT_PATTERN) - DISCONNECT_ALLOWLIST
        self.assertEqual(
            offenders,
            set(),
            msg=(
                "New pre_delete.disconnect span(s) detected that bypass Object Lock enforcement: "
                f"{sorted(offenders)}. If intentional, add it to DISCONNECT_ALLOWLIST "
                "with a justification comment."
            ),
        )
