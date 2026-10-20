"""
The contract between each retention mirror and the warm model it mirrors.

A mirror has to stay field-compatible with its warm model, and the two permitted deviations are a foreign
key demoted to an identifier column and a name denormalized because the key it was read through is gone.
Nothing else catches a field added to a warm model and not to its mirror: it produces no migration error
and no failure anywhere else, and every record rotated afterwards is missing it.
"""

import uuid

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from nautobot.core.constants import GLOBAL_SEARCH_EXCLUDE_LIST
from nautobot.core.testing import TestCase
from nautobot.dcim.models import Device, Location
from nautobot.extras.choices import ObjectChangeActionChoices, ObjectChangeEventContextChoices
from nautobot.extras.models import (
    ArchivedJobConsoleEntry,
    ArchivedJobLogEntry,
    ArchivedJobResult,
    ArchivedObjectChange,
    JobConsoleEntry,
    JobLogEntry,
    JobResult,
    ObjectChange,
)

# Each mirror beside the warm model it holds history for.
MIRRORED = {
    ObjectChange: ArchivedObjectChange,
    JobResult: ArchivedJobResult,
    JobLogEntry: ArchivedJobLogEntry,
    JobConsoleEntry: ArchivedJobConsoleEntry,
}
ARCHIVE_MODELS = tuple(MIRRORED.values())


class ChangelogArchiveSchemaTestCase(TestCase):
    """The mirrors have to stay field-compatible with the warm models they hold history for."""

    def test_mirror_fields_match_warm_fields_with_foreign_keys_demoted(self):
        """
        Every warm field is present on the mirror, with foreign keys held as `<name>_id` columns.

        This is the check that catches the failure mode nothing else does: a field added to a warm model
        and not to its mirror produces no migration error and no test failure anywhere else.
        """
        # Denormalized on the mirror to survive the loss of the foreign key it was read through.
        expected_extra = {JobResult: {"user_name"}}

        for warm, mirror in MIRRORED.items():
            with self.subTest(model=warm.__name__):
                mirror_fields = {f.name for f in mirror._meta.fields}
                missing = set()
                for field in warm._meta.fields:
                    if field.name in mirror_fields:
                        continue
                    if field.is_relation and f"{field.name}_id" in mirror_fields:
                        continue
                    missing.add(field.name)
                self.assertEqual(missing, set(), f"{mirror.__name__} is missing warm fields")

                warm_names = {f.name for f in warm._meta.fields}
                extra = {name for name in mirror_fields - warm_names if name.removesuffix("_id") not in warm_names}
                self.assertEqual(extra, expected_extra.get(warm, set()))

    def test_mirror_fields_match_warm_field_types(self):
        """
        A field shared with the warm model has the same type and length, so rotation can copy its value as is.

        Nullability is checked for every field, including demoted foreign keys: a mirror column that rejected a
        null its warm counterpart allows would fail rotation.
        """
        for warm, mirror in MIRRORED.items():
            for warm_field in warm._meta.fields:
                with self.subTest(model=warm.__name__, field=warm_field.name):
                    if warm_field.is_relation:
                        mirror_field = mirror._meta.get_field(f"{warm_field.name}_id")
                    else:
                        mirror_field = mirror._meta.get_field(warm_field.name)
                        self.assertIs(type(mirror_field), type(warm_field))
                        self.assertEqual(mirror_field.max_length, warm_field.max_length)
                    self.assertEqual(mirror_field.null, warm_field.null)

    def test_demoted_relations_resolve_to_none(self):
        """Reaching for a warm relation by name gets None, where the warm record would follow the relation."""
        for warm, mirror in MIRRORED.items():
            instance = mirror()
            # Forward relations, including generic foreign keys, which `_meta.fields` omits. Content types are
            # resolved from their ids on the mirror rather than demoted.
            demoted = [
                field
                for field in (*warm._meta.fields, *warm._meta.private_fields)
                if field.many_to_one and field.related_model is not ContentType
            ]
            for warm_field in demoted:
                with self.subTest(model=mirror.__name__, field=warm_field.name):
                    self.assertIsNone(getattr(instance, warm_field.name))

    def test_content_types_resolve_from_their_ids(self):
        device_ct = ContentType.objects.get_for_model(Device)
        location_ct = ContentType.objects.get_for_model(Location)
        record = ArchivedObjectChange(
            changed_object_type_id=device_ct.pk,
            related_object_type_id=location_ct.pk,
            object_repr="device 1",
            action=ObjectChangeActionChoices.ACTION_UPDATE,
            user_name="admin",
        )
        self.assertEqual(record.changed_object_type, device_ct)
        self.assertEqual(record.related_object_type, location_ct)
        self.assertEqual(str(record), f"{device_ct} device 1 updated by admin")

    def test_get_related_changes_honors_object_permissions(self):
        device_ct = ContentType.objects.get_for_model(Device)
        changed_object_id = uuid.uuid4()
        records = [
            ArchivedObjectChange.objects.create(
                time=timezone.now(),
                request_id=uuid.uuid4(),
                action=action,
                changed_object_type_id=device_ct.pk,
                changed_object_id=changed_object_id,
                change_context=ObjectChangeEventContextChoices.CONTEXT_WEB,
                object_repr="device 1",
                object_data={},
                user_name="admin",
            )
            for action in (
                ObjectChangeActionChoices.ACTION_CREATE,
                ObjectChangeActionChoices.ACTION_UPDATE,
                ObjectChangeActionChoices.ACTION_DELETE,
            )
        ]
        self.add_permissions(
            "extras.view_archivedobjectchange", constraints={"action": ObjectChangeActionChoices.ACTION_UPDATE}
        )

        self.assertQuerySetEqual(records[0].get_related_changes(), records[1:], ordered=False)
        self.assertQuerySetEqual(records[0].get_related_changes(user=self.user), [records[1]])

    def test_get_absolute_url_is_none_without_a_route(self):
        """No retained record type has a page or endpoint yet, so a URL lookup gets None rather than raising."""
        for mirror in ARCHIVE_MODELS:
            instance = mirror(id=uuid.uuid4())
            with self.subTest(model=mirror.__name__):
                self.assertIsNone(instance.get_absolute_url())
                self.assertIsNone(instance.get_absolute_url(api=True))

    def test_mirrors_offer_only_the_view_permission(self):
        """Rotation writes retained records and nothing else does, so there is no add, change or delete."""
        for mirror in ARCHIVE_MODELS:
            with self.subTest(model=mirror.__name__):
                self.assertEqual(mirror._meta.default_permissions, ("view",))

    def test_mirrors_hold_no_foreign_keys(self):
        """
        A real relation would become a cross-database constraint if the archive tables move to a separate database.

        Each reference is a plain identifier column instead. Only concrete forward relations matter here;
        the reverse `GenericRelation` descriptors inherited from `BaseModel` add no column and no
        constraint.
        """
        for mirror in ARCHIVE_MODELS:
            with self.subTest(model=mirror.__name__):
                relations = [f.name for f in mirror._meta.fields if f.is_relation]
                self.assertEqual(relations, [])

    def test_mirrors_are_excluded_from_global_search(self):
        """Retained history is excluded from global search, like the warm models it mirrors."""
        for mirror in ARCHIVE_MODELS:
            with self.subTest(model=mirror.__name__):
                self.assertIn(mirror._meta.model_name, GLOBAL_SEARCH_EXCLUDE_LIST)
