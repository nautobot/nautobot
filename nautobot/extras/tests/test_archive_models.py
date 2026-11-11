"""
The contract between each archived log model and the live model it archives.

An archived model has to stay field-compatible with its live model. It differs in only two ways: each foreign key to a
model that isn't archived is stored as a `<name>_id` identifier column, and `ArchivedJobResult` adds `user_name`, since
its username can't be read through a `user` foreign key. Foreign keys between archived models are real foreign keys.

`find_archive_schema_drift()` is what compares the two, and `ArchiveSchemaDriftTestCase` covers that
comparison. Nothing else catches a field added to a live model and not to its archived model: it produces
no migration error and no failure anywhere else, and every record rotated afterwards is missing it.
"""

from unittest import mock
import uuid

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.test import SimpleTestCase
from django.utils import timezone

from nautobot.core.constants import GLOBAL_SEARCH_EXCLUDE_LIST
from nautobot.core.testing import TestCase
from nautobot.dcim.models import Device, Location
from nautobot.extras.choices import ObjectChangeActionChoices, ObjectChangeEventContextChoices
from nautobot.extras.models import (
    ArchivedJobLogEntry,
    ArchivedJobResult,
    ArchivedObjectChange,
    JobLogEntry,
    JobResult,
    ObjectChange,
)
from nautobot.extras.models.archive import (
    _find_archived_model_drift,
    ARCHIVED_MODEL_NAME_PREFIX,
    find_archive_schema_drift,
    get_all_archived_models,
    get_archived_model_and_live_model_pairs,
    get_live_model_from_archived_model,
    get_live_model_name_from_archived_model,
)

# Each live model beside the model it is archived to. Resolved from the archived models' names rather than
# written out here, so that this module cannot disagree with what the comparison resolves. A model that
# fails to resolve is caught by
# `ArchiveSchemaDriftTestCase.test_every_archived_model_resolves_its_live_model_from_its_name`.
ARCHIVED_FROM = {live_model: archived_model for archived_model, live_model in get_archived_model_and_live_model_pairs()}
ARCHIVED_MODELS = tuple(ARCHIVED_FROM.values())


def format_drift_check_data(drift):
    """Render drift findings one per line, so an assertion failure names each one."""
    return "\n".join(
        f"  - {archived_model._meta.label}: {message}"
        for archived_model, _live_model, messages in drift
        for message in messages
    )


def stub_field(field, name):
    """A real Django field instance carrying the name a model would have given it."""
    field.name = name
    return field


class StubRelation:
    """Stands in for a relation field, which cannot be built outside a model class."""

    is_relation = True

    def __init__(self, name, related_model, null=False):
        self.name = name
        self.related_model = related_model
        self.null = null


class StubMeta:
    def __init__(self, label, fields, many_to_many=()):
        self.label = label
        self.fields = fields
        self.many_to_many = many_to_many


def stub_model(label, fields, many_to_many=(), archived_only_field_names=()):
    """A stand-in model exposing only what the drift comparison reads."""
    return type(
        label.rpartition(".")[2],
        (),
        {
            "_meta": StubMeta(label, fields, many_to_many),
            "archived_only_field_names": archived_only_field_names,
        },
    )


class ArchivedLogModelTestCase(TestCase):
    """How an archived record behaves when compared against its live counterpart."""

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


class ArchiveSchemaDriftTestCase(SimpleTestCase):
    """
    The comparison between each archived model and the live model it archives.

    `test_no_schema_drift_from_the_live_models` asserts the real models are in step. The rest drive one
    comparison branch each, so that a branch which silently checks nothing cannot pass as a clean archive.
    """

    def test_no_schema_drift_from_the_live_models(self):
        drift_check_data = find_archive_schema_drift()
        self.assertEqual(
            drift_check_data,
            [],
            f"archived models no longer match the live models they archive:\n{format_drift_check_data(drift_check_data)}",
        )

    def test_every_archived_model_resolves_its_live_model_from_its_name(self):
        archived_model_pairs = get_archived_model_and_live_model_pairs()

        self.assertEqual(set(get_all_archived_models()), {archived_model for archived_model, _ in archived_model_pairs})
        for archived_model, live_model in archived_model_pairs:
            with self.subTest(archived_model=archived_model.__name__):
                self.assertEqual(archived_model.__name__, f"{ARCHIVED_MODEL_NAME_PREFIX}{live_model.__name__}")
                self.assertEqual(archived_model._meta.app_label, live_model._meta.app_label)

    def test_a_name_that_does_not_follow_the_convention_resolves_to_nothing(self):
        class NotNamedForALiveModel:
            pass

        class ArchivedNoSuchModel:
            _meta = ArchivedObjectChange._meta

        self.assertIsNone(get_live_model_name_from_archived_model(NotNamedForALiveModel))
        self.assertEqual(get_live_model_name_from_archived_model(ArchivedNoSuchModel), "NoSuchModel")
        self.assertEqual(get_live_model_name_from_archived_model(ArchivedObjectChange), "ObjectChange")

        self.assertIs(get_live_model_from_archived_model(ArchivedObjectChange), ObjectChange)
        self.assertIsNone(get_live_model_from_archived_model(NotNamedForALiveModel))
        self.assertIsNone(get_live_model_from_archived_model(ArchivedNoSuchModel))

    def test_a_mismatched_pair_reports_the_gaps_against_real_models(self):
        """Two real models that do not archive each other, so every kind of gap appears at once."""
        drift_check_data = find_archive_schema_drift([(ArchivedJobLogEntry, JobResult)])

        archived_model, live_model, messages = drift_check_data[0]
        self.assertIs(archived_model, ArchivedJobLogEntry)
        self.assertIs(live_model, JobResult)
        self.assertIn("`extras.ArchivedJobLogEntry` is missing the field `extras.JobResult.name`", messages)
        self.assertIn("`extras.ArchivedJobLogEntry` is missing the field `extras.JobResult.status`", messages)
        # A live foreign key to a model that is not archived is held as `<name>_id`.
        self.assertIn("`extras.ArchivedJobLogEntry` is missing the field `extras.JobResult.job_model`", messages)

    def test_a_column_only_on_the_archived_model_is_reported(self):
        """The reverse gap: a column rotation would never populate, because no live field feeds it."""
        drift_check_data = find_archive_schema_drift([(ArchivedJobResult, JobLogEntry)])

        self.assertEqual(len(drift_check_data), 1)
        _archived_model, _live_model, messages = drift_check_data[0]
        self.assertIn(
            "`extras.ArchivedJobResult.worker` has no counterpart on `extras.JobLogEntry` and is not in "
            "`archived_only_field_names`.",
            messages,
        )

    def test_a_declared_denormalization_is_not_reported(self):
        """
        `ArchivedJobResult.user_name` has no live counterpart on purpose, and says so.

        The live model reads the username through its `user` foreign key, which can't be followed from an
        archived record, so rotation copies it. Declared in `archived_only_field_names`, it is not drift.
        """
        self.assertIn("user_name", ArchivedJobResult.archived_only_field_names)
        self.assertNotIn(
            ArchivedJobResult,
            [archived_model for archived_model, _live_model, _messages in find_archive_schema_drift()],
        )

    def test_an_archived_model_not_named_for_a_live_model_raises(self):
        with mock.patch("nautobot.extras.models.archive.ARCHIVED_MODEL_NAME_PREFIX", "Retained"):
            with self.assertRaises(LookupError):
                find_archive_schema_drift()

    def test_an_archived_model_whose_live_model_does_not_exist_raises(self):
        with mock.patch(
            "nautobot.extras.models.archive.get_live_model_name_from_archived_model", return_value="NoSuchModel"
        ):
            with self.assertRaises(LookupError):
                find_archive_schema_drift()

    def test_a_field_missing_from_the_archived_model_is_reported(self):
        live_model = stub_model("extras.Widget", [stub_field(models.CharField(max_length=10), "name")])
        archived_model = stub_model("extras.ArchivedWidget", [])

        self.assertEqual(
            _find_archived_model_drift(archived_model, live_model),
            ["`extras.ArchivedWidget` is missing the field `extras.Widget.name`"],
        )

    def test_a_field_of_a_different_type_is_reported(self):
        live_model = stub_model("extras.Widget", [stub_field(models.CharField(max_length=10), "name")])
        archived_model = stub_model("extras.ArchivedWidget", [stub_field(models.IntegerField(), "name")])

        self.assertEqual(
            _find_archived_model_drift(archived_model, live_model),
            ["`extras.ArchivedWidget.name` is a `IntegerField` but `extras.Widget.name` is a `CharField`"],
        )

    def test_a_field_that_holds_fewer_characters_is_reported(self):
        live_model = stub_model("extras.Widget", [stub_field(models.CharField(max_length=100), "name")])
        archived_model = stub_model("extras.ArchivedWidget", [stub_field(models.CharField(max_length=50), "name")])

        self.assertEqual(
            _find_archived_model_drift(archived_model, live_model),
            [
                "`extras.ArchivedWidget.name` has a max_length of `50` and does not match the "
                "`extras.Widget.name` max_length of `100`."
            ],
        )

    def test_a_field_with_different_nullability_is_reported(self):
        live_model = stub_model("extras.Widget", [stub_field(models.CharField(max_length=10, null=False), "name")])
        archived_model = stub_model(
            "extras.ArchivedWidget", [stub_field(models.CharField(max_length=10, null=True), "name")]
        )

        self.assertEqual(
            _find_archived_model_drift(archived_model, live_model),
            [
                "`extras.ArchivedWidget.name` has nullability set to `null=True`. This differs with "
                "`extras.Widget.name` which has nullability set to `null=False`."
            ],
        )

    def test_a_many_to_many_field_on_the_live_model_is_reported(self):
        """An archived model holds no many-to-many table, so the values are lost whatever else matches."""
        live_model = stub_model("extras.Widget", [], many_to_many=[stub_field(models.CharField(), "tags")])
        archived_model = stub_model("extras.ArchivedWidget", [])

        self.assertEqual(
            _find_archived_model_drift(archived_model, live_model),
            [
                "`extras.ArchivedWidget` cannot hold `extras.Widget.tags` because it is a many-to-many "
                "field, so its values are lost when a record is archived."
            ],
        )

    def test_an_undeclared_column_on_the_archived_model_is_reported(self):
        live_model = stub_model("extras.Widget", [])
        archived_model = stub_model("extras.ArchivedWidget", [stub_field(models.CharField(max_length=10), "extra")])

        self.assertEqual(
            _find_archived_model_drift(archived_model, live_model),
            [
                "`extras.ArchivedWidget.extra` has no counterpart on `extras.Widget` and is not in "
                "`archived_only_field_names`."
            ],
        )

    def test_a_demoted_column_of_the_wrong_type_is_reported(self):
        """`Job` uses a UUID primary key, so an integer column cannot hold the reference."""
        archived_model = stub_model("extras.ArchivedWidget", [stub_field(models.IntegerField(), "job_model_id")])

        messages = _find_archived_model_drift(archived_model, JobResult)

        self.assertIn(
            "`extras.ArchivedWidget.job_model_id` is a `integer` column but it must be a `uuid` column "
            "to hold a `extras.Job` primary key.",
            messages,
        )

    def test_a_demoted_column_that_is_still_a_relation_is_reported(self):
        archived_model = stub_model("extras.ArchivedWidget", [StubRelation("job_model_id", ArchivedObjectChange)])

        messages = _find_archived_model_drift(archived_model, JobResult)

        self.assertIn(
            "`extras.ArchivedWidget.job_model_id` is a relation to `extras.ArchivedObjectChange` but it must "
            "be a plain identifier column, because `extras.JobResult.job_model` points at `extras.Job` "
            "which is not archived.",
            messages,
        )

    def test_a_relation_pointing_at_the_wrong_archived_model_is_reported(self):
        """`JobLogEntry.job_result` is archived, so the archived field must point at `ArchivedJobResult`."""
        archived_model = stub_model("extras.ArchivedWidget", [StubRelation("job_result", ArchivedObjectChange)])

        messages = _find_archived_model_drift(archived_model, JobLogEntry)

        self.assertIn(
            "`extras.ArchivedWidget.job_result` points at `extras.ArchivedObjectChange` but it must point at "
            "`extras.ArchivedJobResult`, the archived model for `extras.JobResult`.",
            messages,
        )
