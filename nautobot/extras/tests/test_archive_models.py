"""
The contract between each archived log model and the live model it archives.

An archived model has to stay field-compatible with its live model. It differs in only two ways: each foreign key to a
model that isn't archived is stored as a `<name>_id` identifier column, and `ArchivedJobResult` adds `user_name`, since
its username can't be read through a `user` foreign key. Foreign keys between archived models are real foreign keys. Nothing else catches a field added to a live model and not to its archived model:
it produces no migration error and no failure anywhere else, and every record rotated afterwards is missing it.
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

# Each live model beside the model it is archived to.
ARCHIVED_FROM = {
    ObjectChange: ArchivedObjectChange,
    JobResult: ArchivedJobResult,
    JobLogEntry: ArchivedJobLogEntry,
    JobConsoleEntry: ArchivedJobConsoleEntry,
}
ARCHIVED_MODELS = tuple(ARCHIVED_FROM.values())


class ArchivedLogModelTestCase(TestCase):
    """The archived log models have to stay field-compatible with the live models they archive."""

    def test_archived_fields_match_live_fields(self):
        """
        Every live field is present on the archived model, by name or, for a foreign key to a model that isn't
        archived, as a `<name>_id` column.

        This is the check that catches the failure mode nothing else does: a field added to a live model
        and not to its archived model produces no migration error and no test failure anywhere else.
        """
        # Recorded on the archived model because the foreign key it was read through isn't archived.
        expected_extra = {JobResult: {"user_name"}}

        for live, archived in ARCHIVED_FROM.items():
            with self.subTest(model=live.__name__):
                archived_fields = {f.name for f in archived._meta.fields}
                missing = set()
                for field in live._meta.fields:
                    if field.name in archived_fields:
                        continue
                    if field.is_relation and f"{field.name}_id" in archived_fields:
                        continue
                    missing.add(field.name)
                self.assertEqual(missing, set(), f"{archived.__name__} is missing live fields")

                live_names = {f.name for f in live._meta.fields}
                extra = {name for name in archived_fields - live_names if name.removesuffix("_id") not in live_names}
                self.assertEqual(extra, expected_extra.get(live, set()))

    def test_archived_fields_match_live_field_types(self):
        """
        A field shared with the live model has the same type and length, so rotation can copy its value as is.

        A foreign key to another live model that is archived must point to that model's archived counterpart.
        Nullability is checked for every field, including foreign keys held as ids: an archived column that
        rejected a null its live counterpart allows would fail rotation.
        """
        for live, archived in ARCHIVED_FROM.items():
            for live_field in live._meta.fields:
                with self.subTest(model=live.__name__, field=live_field.name):
                    if live_field.is_relation and live_field.related_model in ARCHIVED_FROM:
                        archived_field = archived._meta.get_field(live_field.name)
                        self.assertIs(archived_field.related_model, ARCHIVED_FROM[live_field.related_model])
                    elif live_field.is_relation:
                        archived_field = archived._meta.get_field(f"{live_field.name}_id")
                    else:
                        archived_field = archived._meta.get_field(live_field.name)
                        self.assertIs(type(archived_field), type(live_field))
                        self.assertEqual(archived_field.max_length, live_field.max_length)
                    self.assertEqual(archived_field.null, live_field.null)

    def test_unresolved_relations_return_none(self):
        """Reaching for a live relation by name gets None, where the live record would follow the relation."""
        for live, archived in ARCHIVED_FROM.items():
            instance = archived()
            # Forward relations, including generic foreign keys, which `_meta.fields` omits. Content types are
            # resolved from their ids on the archived model instead, and relations to archived models are real.
            relations = [
                field
                for field in (*live._meta.fields, *live._meta.private_fields)
                if field.many_to_one
                and field.related_model is not ContentType
                and field.related_model not in ARCHIVED_FROM
            ]
            for live_field in relations:
                with self.subTest(model=archived.__name__, field=live_field.name):
                    self.assertIsNone(getattr(instance, live_field.name))

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
        """With no route registered for an archived model, a URL lookup gets None rather than raising."""
        for archived in ARCHIVED_MODELS:
            instance = archived(id=uuid.uuid4())
            with self.subTest(model=archived.__name__):
                self.assertIsNone(instance.get_absolute_url())
                self.assertIsNone(instance.get_absolute_url(api=True))

    def test_archived_models_offer_only_the_view_permission(self):
        """Rotation writes archived records and nothing else does, so there is no add, change or delete."""
        for archived in ARCHIVED_MODELS:
            with self.subTest(model=archived.__name__):
                self.assertEqual(archived._meta.default_permissions, ("view",))

    def test_archived_models_only_have_foreign_keys_to_archived_models(self):
        """
        A relation to any other model would become a cross-database constraint if the archive tables move to a
        separate database.

        Each such reference is a plain identifier column instead. Only concrete forward relations matter here;
        the reverse `GenericRelation` descriptors inherited from `BaseModel` add no column and no constraint.
        """
        for archived in ARCHIVED_MODELS:
            with self.subTest(model=archived.__name__):
                related_models = {f.related_model for f in archived._meta.fields if f.is_relation}
                self.assertLessEqual(related_models, set(ARCHIVED_MODELS))

    def test_archived_models_are_excluded_from_global_search(self):
        """Archived log models are excluded from global search, like the live models they archive."""
        for archived in ARCHIVED_MODELS:
            with self.subTest(model=archived.__name__):
                self.assertIn(archived._meta.model_name, GLOBAL_SEARCH_EXCLUDE_LIST)
