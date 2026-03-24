import json

from django.contrib.contenttypes.models import ContentType

from nautobot.extras.jobs import (
    BooleanVar,
    DryRunVar,
    Job,
    MultiObjectVar,
    ObjectVar,
    RunJobTaskFailed,
    StringVar,
    TextVar,
)
from nautobot.extras.models import CustomField


class CleanupCustomFieldsData(Job):
    """System Job to cleanup Custom Fields."""

    field = MultiObjectVar(
        model=CustomField,
        description="Custom Field(s) to clean up data for. Leave blank to clean up data for all Custom Fields.",
        label="Custom Field",
        required=False,
    )
    content_types = MultiObjectVar(
        model=ContentType,
        description="Type(s) of objects to act upon. Leave blank to act on all applicable Content Types.",
        label="Content Types",
        query_params={"can_view": True, "feature": "custom_fields"},
        required=False,
    )
    dryrun = DryRunVar(
        description="Execute all changes inside a rolled-back transaction. Logs reflect what would have changed. Implies verbose output."
    )
    safe_change = BooleanVar(
        default=False,
        label="Safe changes only",
        description="Only run the additive provision step; skip any removal or mutation of existing data.",
    )
    verbose = BooleanVar(default=False, label="Verbose output?")

    class Meta:
        name = "Cleanup Custom Fields"
        description = """System Job to cleanup Custom Field data, which may be destructive.

Please review the documentation before running this job. It is recommended to run this job in a test environment and dry-run first."""
        has_sensitive_variables = False
        soft_time_limit = 3600
        time_limit = 4000

    def run(self, *, field=None, content_types=None, dryrun=False, safe_change=False, verbose=False):  # pylint:disable=arguments-differ
        from nautobot.extras.customfields import cleanup_custom_field_data

        ct_pks = [ct.pk for ct in content_types] if content_types else None
        if field:
            for f in field:
                cleanup_custom_field_data(
                    field_id=f.pk,
                    content_type_pk_set=ct_pks,
                    dryrun=dryrun,
                    safe_change=safe_change,
                    verbose=verbose,
                    job_logger=self.logger,
                )
        else:
            cleanup_custom_field_data(
                field_id=None,
                content_type_pk_set=ct_pks,
                dryrun=dryrun,
                safe_change=safe_change,
                verbose=verbose,
                job_logger=self.logger,
            )


class DeleteCustomFieldData(Job):
    """System Job to delete all stored values for a Custom Field key across a set of Content Types."""

    field_key = StringVar(
        label="Custom Field Key",
        description="The key of the custom field whose data should be deleted. Ignored when Field Specs are provided.",
        required=False,
    )
    content_types = MultiObjectVar(
        model=ContentType,
        description="Type(s) of objects to act upon. Ignored when Field Specs are provided.",
        label="Content Types",
        query_params={"can_view": True, "feature": "custom_fields"},
        required=False,
    )
    field_specs = TextVar(
        label="Field Specs (JSON)",
        description=(
            'Optional. JSON list of {"field_key": str, "content_types": [pk, ...]} dicts for bulk use. '
            "When provided, Field Key and Content Types are ignored."
        ),
        required=False,
    )
    verbose = BooleanVar(default=False, label="Verbose output?")

    class Meta:
        name = "Delete Custom Field Data"
        description = "Delete all stored values for a given Custom Field key across the specified Content Types."
        has_sensitive_variables = False
        soft_time_limit = 3600
        time_limit = 4000

    def run(self, *, field_key=None, content_types=None, field_specs=None, verbose=False):  # pylint:disable=arguments-differ
        from nautobot.extras.customfields import delete_custom_field_data

        # Normalize both input paths into a uniform list of specs before processing.
        if field_specs:
            try:
                specs = json.loads(field_specs)
            except json.JSONDecodeError as exc:
                raise RunJobTaskFailed(f"field_specs is not valid JSON: {exc}") from exc
            if not isinstance(specs, list):
                raise RunJobTaskFailed("field_specs must be a JSON list.")
            for item in specs:
                if (
                    not isinstance(item, dict)
                    or not isinstance(item.get("field_key"), str)
                    or not isinstance(item.get("content_types"), list)
                ):
                    raise RunJobTaskFailed(
                        f"Each field_specs item must be a dict with 'field_key' (str) and 'content_types' (list); got {item!r}"
                    )
        elif field_key and content_types is not None:
            specs = [{"field_key": field_key, "content_types": [str(ct.pk) for ct in content_types]}]
        else:
            raise RunJobTaskFailed("Provide either field_specs (JSON) or both field_key and content_types.")

        for item in specs:
            delete_custom_field_data(
                field_key=item["field_key"],
                content_type_pk_set=item["content_types"],
                verbose=verbose,
                job_logger=self.logger,
            )


class ProvisionCustomField(Job):
    """System Job to provision missing Custom Field values across a set of Content Types."""

    field = ObjectVar(
        model=CustomField,
        description="Custom Field to provision.",
        label="Custom Field",
        required=True,
    )
    content_types = MultiObjectVar(
        model=ContentType,
        description="Type(s) of objects to act upon.",
        label="Content Types",
        query_params={"can_view": True, "feature": "custom_fields"},
        required=True,
    )
    dryrun = DryRunVar(
        description="Execute all changes inside a rolled-back transaction. Logs reflect what would have changed. Implies verbose output."
    )
    verbose = BooleanVar(default=False, label="Verbose output?")

    class Meta:
        name = "Provision Custom Field"
        description = "Add missing Custom Field default values to all in-scope objects for the specified Content Types."
        has_sensitive_variables = False
        soft_time_limit = 3600
        time_limit = 4000

    def run(self, *, field, content_types, dryrun=False, verbose=False):  # pylint:disable=arguments-differ
        from nautobot.extras.customfields import provision_field

        provision_field(
            field_id=field.pk,
            content_type_pk_set=[ct.pk for ct in content_types],
            dryrun=dryrun,
            verbose=verbose,
            job_logger=self.logger,
        )


class UpdateCustomFieldChoiceData(Job):
    """System Job to rename a choice value across all objects that reference a Select/Multi-Select Custom Field."""

    field = ObjectVar(
        model=CustomField,
        description="The Select or Multi-Select Custom Field whose choice value is being renamed. Ignored when Field Specs are provided.",
        label="Custom Field",
        required=False,
    )
    old_value = StringVar(
        label="Old Value",
        description="The existing choice value to replace. Ignored when Field Specs are provided.",
        required=False,
    )
    new_value = StringVar(
        label="New Value",
        description="The new choice value to set in place of the old value. Ignored when Field Specs are provided.",
        required=False,
    )
    field_specs = TextVar(
        label="Field Specs (JSON)",
        description=(
            'Optional. JSON list of {"field_id": str, "old_value": str, "new_value": str} dicts for bulk use. '
            "When provided, Field, Old Value, and New Value are ignored."
        ),
        required=False,
    )

    class Meta:
        name = "Update Custom Field Choice Data"
        description = "Rename a choice value on a Select or Multi-Select Custom Field across all affected objects."
        has_sensitive_variables = False
        soft_time_limit = 3600
        time_limit = 4000

    def run(self, *, field=None, old_value=None, new_value=None, field_specs=None):  # pylint:disable=arguments-differ
        from nautobot.extras.customfields import update_custom_field_choice_data

        # Normalize both input paths into a uniform list of specs before processing.
        if field_specs:
            try:
                specs = json.loads(field_specs)
            except json.JSONDecodeError as exc:
                raise RunJobTaskFailed(f"field_specs is not valid JSON: {exc}") from exc
            if not isinstance(specs, list):
                raise RunJobTaskFailed("field_specs must be a JSON list.")
            for item in specs:
                if (
                    not isinstance(item, dict)
                    or not isinstance(item.get("field_id"), str)
                    or not isinstance(item.get("old_value"), str)
                    or not isinstance(item.get("new_value"), str)
                ):
                    raise RunJobTaskFailed(
                        f"Each field_specs item must be a dict with 'field_id', 'old_value', and 'new_value' (all str); got {item!r}"
                    )
        elif field and old_value is not None and new_value is not None:
            specs = [{"field_id": str(field.pk), "old_value": old_value, "new_value": new_value}]
        else:
            raise RunJobTaskFailed("Provide either field_specs (JSON) or all of field, old_value, and new_value.")

        for item in specs:
            update_custom_field_choice_data(
                field_id=item["field_id"],
                old_value=item["old_value"],
                new_value=item["new_value"],
                job_logger=self.logger,
            )
