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

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
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
from nautobot.extras.models.archive import ArchivedLogModel

# --------------------------------------------------------------------------------------------------
# Schema Drift Test Helpers
# --------------------------------------------------------------------------------------------------
# An archived model has to stay field-compatible with the live model it archives. Nothing in Django
# enforces that. The two are separate models with separate migrations, so a field added to `ObjectChange`
# and not to `ArchivedObjectChange` needs to produce a loud failure.
#
# An archived model is named with a prefix of `Archived<LiveModel>`, there should
# be no deviation from this.
ARCHIVED_MODEL_NAME_PREFIX = "Archived"


def get_all_archived_models():
    """
    Every concrete archived log model.

    Returns:
        (list[type]): The subclasses of `ArchivedLogModel`.
    """
    return [model for model in apps.get_models() if issubclass(model, ArchivedLogModel)]


def get_live_model_name_from_archived_model(archived_model):
    """
    The name of the live model an archived model is derived from.

    Args:
        archived_model (type): The archived model to read the name of.

    Returns:
        (str | None): The live model's name, or None where the archived model is not named for one.
    """
    if not archived_model.__name__.startswith(ARCHIVED_MODEL_NAME_PREFIX):
        return None
    else:
        return archived_model.__name__.removeprefix(ARCHIVED_MODEL_NAME_PREFIX) or None


def get_live_model_from_archived_model(archived_model):
    """
    Retrieves the live model that an archived model is derived from.

    Args:
        archived_model (type): The archived model to resolve the live model for.

    Returns:
        (type | None): The live model, or None where the archived model is not named for one or names
            one that is not registered.
    """
    live_model_name = get_live_model_name_from_archived_model(archived_model)
    if live_model_name is None:
        return None
    try:
        return apps.get_model(archived_model._meta.app_label, live_model_name)
    except LookupError:
        return None


def get_archived_model_from_live_model(live_model):
    """
    Retrieves the archived model derived from a live model.

    Args:
        live_model (type): The live model to resolve the archived model for.

    Returns:
        (type | None): The archived model, or None where no model named `Archived<LiveModel>` is
            registered in the live model's app.
    """
    try:
        return apps.get_model(live_model._meta.app_label, f"{ARCHIVED_MODEL_NAME_PREFIX}{live_model.__name__}")
    except LookupError:
        return None


def get_archived_model_and_live_model_pairs():
    """
    Each archived model beside the live model it archives, resolved from the archived model's name.

    Returns:
        (list[tuple[type, type]]): Each archived model paired with the live model it archives.

    Raises:
        (LookupError): An archived model is not named for a live model, or names one that is not registered.
    """
    archived_model_and_live_models = []
    for archived_model in get_all_archived_models():
        expected_live_model_name = get_live_model_name_from_archived_model(archived_model)
        live_model = get_live_model_from_archived_model(archived_model)
        if live_model is None:
            raise LookupError(
                f"{archived_model._meta.label} does not resolve to a registered model named "
                f"{expected_live_model_name}. There is nothing to compare it against"
            )
        archived_model_and_live_models.append((archived_model, live_model))

    return archived_model_and_live_models


def _validate_plain_field(archived_model, archived_model_field, live_model, live_model_field):
    """
    Validates a plain field of an archived model and a live model.

    A plain field has no relationship.
    """
    drift_messages = []

    do_both_field_types_match = type(archived_model_field) is type(live_model_field)
    if do_both_field_types_match is False:
        drift_messages.append(
            f"`{archived_model._meta.label}.{archived_model_field.name}` is a "
            f"`{type(archived_model_field).__name__}` but `{live_model._meta.label}.{live_model_field.name}` "
            f"is a `{type(live_model_field).__name__}`"
        )

    # length only matters if they're the same type
    if do_both_field_types_match is True and archived_model_field.max_length != live_model_field.max_length:
        drift_messages.append(
            f"`{archived_model._meta.label}.{archived_model_field.name}` has a max_length of `{archived_model_field.max_length}`"
            f" and does not match the `{live_model._meta.label}.{live_model_field.name}` max_length of `{live_model_field.max_length}`."
        )

    return drift_messages


def _validate_dropped_relation_field(archived_model, archived_model_field, live_model, live_model_field):
    """
    Validates a dropped relation field of an archived model and a live model.

    A dropped relation points at a model that is not archived, so the archived model holds it as a plain
    identifier column rather than as a relation.
    """
    drift_messages = []

    is_archived_model_field_still_a_relation = archived_model_field.is_relation is True
    if is_archived_model_field_still_a_relation is True:
        drift_messages.append(
            f"`{archived_model._meta.label}.{archived_model_field.name}` is a relation to "
            f"`{archived_model_field.related_model._meta.label}` but it must be a plain identifier column, "
            f"because `{live_model._meta.label}.{live_model_field.name}` points at "
            f"`{live_model_field.related_model._meta.label}` which is not archived."
        )
        return drift_messages

    archived_model_field_column_type = archived_model_field.db_type(connection)
    live_model_field_referent_column_type = live_model_field.target_field.rel_db_type(connection)
    do_both_column_types_match = archived_model_field_column_type == live_model_field_referent_column_type
    if do_both_column_types_match is False:
        drift_messages.append(
            f"`{archived_model._meta.label}.{archived_model_field.name}` is a "
            f"`{archived_model_field_column_type}` column but it must be a "
            f"`{live_model_field_referent_column_type}` column to hold a "
            f"`{live_model_field.related_model._meta.label}` primary key."
        )

    return drift_messages


def _validate_persisted_relation_field(archived_model, archived_model_field, live_model, live_model_field):
    """
    Validates a persisted relation field of an archived model and a live model.

    A persisted relation points at a model that is archived, so the archived model keeps it as a relation,
    pointed at that archived model rather than at the live one.
    """
    drift_messages = []

    archived_model_for_live_model_field_relation = get_archived_model_from_live_model(live_model_field.related_model)

    is_archived_model_field_a_relation = archived_model_field.is_relation is True
    if is_archived_model_field_a_relation is False:
        drift_messages.append(
            f"`{archived_model._meta.label}.{archived_model_field.name}` is a plain field but it must be a "
            f"relation to `{archived_model_for_live_model_field_relation._meta.label}`, because "
            f"`{live_model._meta.label}.{live_model_field.name}` points at "
            f"`{live_model_field.related_model._meta.label}` which is archived."
        )
        return drift_messages

    does_archived_model_field_point_at_the_archived_model = (
        archived_model_field.related_model is archived_model_for_live_model_field_relation
    )
    if does_archived_model_field_point_at_the_archived_model is False:
        drift_messages.append(
            f"`{archived_model._meta.label}.{archived_model_field.name}` points at "
            f"`{archived_model_field.related_model._meta.label}` but it must point at "
            f"`{archived_model_for_live_model_field_relation._meta.label}`, the archived model for "
            f"`{live_model_field.related_model._meta.label}`."
        )

    return drift_messages


def _find_archived_model_drift(archived_model, live_model):
    """
    What has drifted on one archived model.

    Returns:
        (list[str]): One message per difference found, empty when the two models match.
    """
    archived_fields = {field.name: field for field in archived_model._meta.fields}
    live_fields = {field.name: field for field in live_model._meta.fields}

    drift_messages = []

    for live_model_field in live_model._meta.fields:
        # --------------------
        # Live Model Classification
        # --------------------
        is_live_model_field_a_foreign_relationship = live_model_field.is_relation is True
        is_live_model_field_a_plain_field = is_live_model_field_a_foreign_relationship is False

        # --------------------
        # Archived Model Classification
        # --------------------
        archived_model_relational_field_reference = (
            get_archived_model_from_live_model(live_model_field.related_model)
            if is_live_model_field_a_foreign_relationship is True
            else None
        )
        is_archived_model_relational_field_dropped = (
            is_live_model_field_a_foreign_relationship is True and archived_model_relational_field_reference is None
        )
        is_archived_model_relational_field_kept = (
            is_live_model_field_a_foreign_relationship is True and archived_model_relational_field_reference is not None
        )
        expected_archived_model_field_name = (
            f"{live_model_field.name}_id"
            if is_archived_model_relational_field_dropped is True
            else live_model_field.name
        )
        archived_model_field = archived_fields.get(expected_archived_model_field_name)

        # --------------------
        # Checks
        # --------------------
        # First check - does the field even exist
        does_archive_model_have_live_model_field = archived_model_field is not None
        if does_archive_model_have_live_model_field is False:
            new_drift_message = (
                f"`{archived_model._meta.label}` is missing the field "
                f"`{live_model._meta.label}.{live_model_field.name}`"
            )
            drift_messages.append(new_drift_message)
            # If there's no matching attribute, there's no point in continuing further checks
            continue

        # Second check - does nullability settings match
        does_archive_model_field_nullability_match_live_model_field_nullability = (
            archived_model_field.null == live_model_field.null
        )
        if does_archive_model_field_nullability_match_live_model_field_nullability is False:
            drift_messages.append(
                f"`{archived_model._meta.label}.{archived_model_field.name}` has nullability set to `null={archived_model_field.null}`."
                f" This differs with `{live_model._meta.label}.{live_model_field.name}` which has nullability set to `null={live_model_field.null}`."
            )

        # Third check - is it a plain field? If so what are the possible issues?
        if is_live_model_field_a_plain_field is True:
            plain_field_drift_messages = _validate_plain_field(
                archived_model, archived_model_field, live_model, live_model_field
            )
            drift_messages.extend(plain_field_drift_messages)

        # Fourth check - is it a relation the archived model dropped? If so what are the possible issues?
        if is_archived_model_relational_field_dropped is True:
            dropped_relation_field_drift_messages = _validate_dropped_relation_field(
                archived_model, archived_model_field, live_model, live_model_field
            )
            drift_messages.extend(dropped_relation_field_drift_messages)

        # Fifth check - is it a relation the archived model persisted? If so what are the possible issues?
        if is_archived_model_relational_field_kept is True:
            kept_relation_field_drift_messages = _validate_persisted_relation_field(
                archived_model, archived_model_field, live_model, live_model_field
            )
            drift_messages.extend(kept_relation_field_drift_messages)

    # Sixth check - does the archived model hold a column that no live model field feeds?
    for archived_model_field in archived_model._meta.fields:
        does_live_model_have_a_field_of_the_same_name = archived_model_field.name in live_fields
        is_archived_model_field_declared_as_archive_only = (
            archived_model_field.name in archived_model.archived_only_field_names
        )
        live_model_field_the_relation_was_dropped_from = live_fields.get(archived_model_field.name.removesuffix("_id"))
        is_archived_model_field_a_dropped_relation_column = (
            live_model_field_the_relation_was_dropped_from is not None
            and live_model_field_the_relation_was_dropped_from.is_relation is True
        )

        if (
            does_live_model_have_a_field_of_the_same_name is False
            and is_archived_model_field_declared_as_archive_only is False
            and is_archived_model_field_a_dropped_relation_column is False
        ):
            drift_messages.append(
                f"`{archived_model._meta.label}.{archived_model_field.name}` has no counterpart on "
                f"`{live_model._meta.label}` and is not in `archived_only_field_names`."
            )

    # Seventh check - does the live model hold a many to many field, which cannot be archived at all?
    for live_model_many_to_many_field in live_model._meta.many_to_many:
        drift_messages.append(
            f"`{archived_model._meta.label}` cannot hold "
            f"`{live_model._meta.label}.{live_model_many_to_many_field.name}` because it is a many-to-many "
            f"field, so its values are lost when a record is archived."
        )

    return drift_messages


def find_archive_schema_drift(archived_model_pairs=None):
    """
    Compare each archived model against the live model it archives.

    Args:
        archived_model_pairs (list[tuple[type, type]] | None): Each archived model paired with the live
            model it archives.

    Returns:
        (list[tuple[type, type, list[str]]]): Each archived model that has drifted, with the live model it
            archives and what has drifted on it. Empty when each archived model matches the live model it
            archives.

    Raises:
        (LookupError): An archived model is not named for a live model, or names one that is not registered.
    """
    if archived_model_pairs is None:
        archived_model_pairs = get_archived_model_and_live_model_pairs()

    archived_model_and_drifts = []
    for archived_model, live_model in archived_model_pairs:
        drift = _find_archived_model_drift(archived_model, live_model)
        if drift:
            archived_model_and_drifts.append((archived_model, live_model, drift))

    return archived_model_and_drifts


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


# --------------------------------------------------------------------------------------------------
# Schema Drift Testing
# --------------------------------------------------------------------------------------------------
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
        with mock.patch("nautobot.extras.tests.test_archive_models.ARCHIVED_MODEL_NAME_PREFIX", "Retained"):
            with self.assertRaisesRegex(
                LookupError, r"does not resolve to a registered model named None\. There is nothing to compare it"
            ):
                find_archive_schema_drift()

    def test_an_archived_model_whose_live_model_does_not_exist_raises(self):
        with mock.patch(
            "nautobot.extras.tests.test_archive_models.get_live_model_name_from_archived_model",
            return_value="NoSuchModel",
        ):
            with self.assertRaisesRegex(
                LookupError,
                r"does not resolve to a registered model named NoSuchModel\. There is nothing to compare it",
            ):
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


# --------------------------------------------------------------------------------------------------
# Testing
# --------------------------------------------------------------------------------------------------
class ArchivedLogModelTestCase(TestCase):
    """How an archived record behaves when compared against its live counterpart."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.archived_from = {
            live_model: archived_model for archived_model, live_model in get_archived_model_and_live_model_pairs()
        }
        cls.archived_models = tuple(cls.archived_from.values())

    def test_unresolved_relations_return_none(self):
        """Reaching for a live relation by name gets None, where the live record would follow the relation."""
        for live, archived in self.archived_from.items():
            instance = archived()
            # Forward relations, including generic foreign keys, which `_meta.fields` omits. Content types are
            # resolved from their ids on the archived model instead, and relations to archived models are real.
            relations = [
                field
                for field in (*live._meta.fields, *live._meta.private_fields)
                if field.many_to_one
                and field.related_model is not ContentType
                and field.related_model not in self.archived_from
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
        for archived in self.archived_models:
            instance = archived(id=uuid.uuid4())
            with self.subTest(model=archived.__name__):
                self.assertIsNone(instance.get_absolute_url())
                self.assertIsNone(instance.get_absolute_url(api=True))

    def test_archived_models_offer_only_the_view_permission(self):
        """Rotation writes archived records and nothing else does, so there is no add, change or delete."""
        for archived in self.archived_models:
            with self.subTest(model=archived.__name__):
                self.assertEqual(archived._meta.default_permissions, ("view",))

    def test_archived_models_only_have_foreign_keys_to_archived_models(self):
        """
        A relation to any other model would become a cross-database constraint if the archive tables move to a
        separate database.

        Each such reference is a plain identifier column instead. Only concrete forward relations matter here;
        the reverse `GenericRelation` descriptors inherited from `BaseModel` add no column and no constraint.
        """
        for archived in self.archived_models:
            with self.subTest(model=archived.__name__):
                related_models = {f.related_model for f in archived._meta.fields if f.is_relation}
                self.assertLessEqual(related_models, set(self.archived_models))

    def test_archived_models_are_excluded_from_global_search(self):
        """Archived log models are excluded from global search, like the live models they archive."""
        for archived in self.archived_models:
            with self.subTest(model=archived.__name__):
                self.assertIn(archived._meta.model_name, GLOBAL_SEARCH_EXCLUDE_LIST)
