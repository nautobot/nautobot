from logging import getLogger
import sys

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import transaction
from django.db.models.fields.json import KeyTextTransform

from nautobot.core.models.query_functions import JSONRemove, JSONSet
from nautobot.extras.choices import CustomFieldTypeChoices

logger = getLogger("nautobot.extras.customfields")


def _pks_and_display(queryset, limit=20):
    """
    Return ``(all_pks, display_string)`` for *queryset* using two DB queries.

    Fetches all PKs first (pk-only, flat), then fetches up to *limit* name/pk
    rows via a bounded SQL LIMIT query for the display string.  Falls back to
    pk-only display if the model has no ``name`` field.  A trailing ``"..."`` is
    appended when the result is truncated.
    """
    model = queryset.model
    pks = list(queryset.values_list("pk", flat=True))
    try:
        model._meta.get_field("name")
        rows = queryset.values_list("pk", "name")[:limit]
        parts = [f"{name!r} (pk={pk})" for pk, name in rows]
    except FieldDoesNotExist:
        parts = [str(pk) for pk in pks[:limit]]
    display = ", ".join(parts) + ("..." if len(pks) > limit else "")
    return pks, display


def _count_and_display(queryset, limit=20):
    """
    Return ``(count, display_string)`` using two bounded DB queries.

    Unlike ``_pks_and_display``, this does *not* materialize all PKs — only a
    ``COUNT(*)`` plus up to *limit* name/pk rows.  Use this at call sites that
    only need a count and a human-readable sample for log messages.
    """
    model = queryset.model
    count = queryset.count()
    try:
        model._meta.get_field("name")
        rows = queryset.values_list("pk", "name")[:limit]
        parts = [f"{name!r} (pk={pk})" for pk, name in rows]
    except FieldDoesNotExist:
        pks = queryset.values_list("pk", flat=True)[:limit]
        parts = [str(pk) for pk in pks]
    display = ", ".join(parts) + ("..." if count > limit else "")
    return count, display


def _generate_bulk_object_changes(context, queryset, job_logger=logger):
    # Circular import
    from nautobot.extras.context_managers import (
        change_logging,
        ChangeContext,
        deferred_change_logging_for_bulk_operation,
    )
    from nautobot.extras.signals import _handle_changed_object

    print("Creating deferred ObjectChange records for bulk operation...", file=sys.stderr)

    # Note: we use change_logging() here instead of web_request_context() because we don't want these change records to
    #       trigger jobhooks and webhooks.
    # TODO: this could be made much faster if we ensure the queryset has appropriate select_related/prefetch_related?
    change_context = ChangeContext(**context)
    index = 0
    with change_logging(change_context):
        with deferred_change_logging_for_bulk_operation():
            for index, instance in enumerate(queryset.iterator(), start=1):
                _handle_changed_object(queryset.model, instance, created=False)

    job_logger.info("Created %d ObjectChange records", index)


def update_custom_field_choice_data(field_id, old_value, new_value, change_context=None, job_logger=logger):
    # Circular Import, job_logger is passed in as an argument to avoid this
    from nautobot.extras.models import CustomField

    try:
        field = CustomField.objects.get(pk=field_id)
    except CustomField.DoesNotExist:
        job_logger.error("Custom field with ID %s not found, failing to act on choice data.", field_id)
        raise

    if field.type == CustomFieldTypeChoices.TYPE_SELECT:
        # Loop through all field content types and search for values to update
        for ct in field.content_types.all():
            model = ct.model_class()
            if model is None:
                continue
            queryset = model.objects.filter(**{f"_custom_field_data__{field.key}": old_value})
            pk_list = []
            if change_context is not None:
                pk_list = list(queryset.values_list("pk", flat=True))
            count = queryset.update(_custom_field_data=JSONSet("_custom_field_data", field.key, new_value))
            if count:
                job_logger.info(
                    "Updated `%s` from %r to %r on %d %s object(s).",
                    field.key,
                    old_value,
                    new_value,
                    count,
                    ct.model,
                    extra={"object": field},
                )
            else:
                print(f"No {ct.model} objects had value {old_value!r} for custom field `{field.key}`.", file=sys.stderr)
            if change_context is not None:
                # Since we used update() above, we bypassed ObjectChange automatic creation via signals. Create them now
                _generate_bulk_object_changes(change_context, model.objects.filter(pk__in=pk_list))

    elif field.type == CustomFieldTypeChoices.TYPE_MULTISELECT:
        # Loop through all field content types and search for values to update
        for ct in field.content_types.all():
            model = ct.model_class()
            if model is None:
                continue
            if old_value is None:
                queryset = model.objects.filter(**{f"_custom_field_data__{field.key}__contains": [None]})
            else:
                queryset = model.objects.filter(**{f"_custom_field_data__{field.key}__contains": old_value})

            pk_list = []
            total_updated = 0
            chunk = []
            for obj in queryset.iterator(chunk_size=1000):
                old_list = obj._custom_field_data.get(field.key, [])
                if not isinstance(old_list, (list, tuple)):
                    continue
                new_list = list({new_value if e == old_value else e for e in old_list} - {None})
                if new_list != old_list:
                    obj._custom_field_data[field.key] = new_list
                    chunk.append(obj)
                    pk_list.append(obj.pk)

                if len(chunk) >= 1000:
                    model.objects.bulk_update(chunk, ["_custom_field_data"])
                    total_updated += len(chunk)
                    chunk = []

            if chunk:
                model.objects.bulk_update(chunk, ["_custom_field_data"])
                total_updated += len(chunk)

            if total_updated:
                job_logger.info(
                    "Updated `%s` from %r to %r on %d %s object(s).",
                    field.key,
                    old_value,
                    new_value,
                    total_updated,
                    ct.model,
                    extra={"object": field},
                )
                if change_context is not None:
                    # Since we used bulk_update() above, we bypassed ObjectChange automatic creation via signals. Create them now
                    _generate_bulk_object_changes(change_context, model.objects.filter(pk__in=pk_list))

    else:
        job_logger.error(f"Unknown field type, failing to act on choice data for this field {field.key}.")
        raise ValueError

    return True


def delete_custom_field_data(field_key, content_type_pk_set, change_context=None, verbose=False, job_logger=logger):
    """
    Delete the values for a custom field

    Args:
        field_key (str): The key of the custom field which is being deleted
        content_type_pk_set (list): List of PKs for content types to act upon
        change_context (dict): Optional change context for ObjectChange creation
        verbose (bool): If True, log each affected object by name/pk. Defaults to False.
    """
    for ct in ContentType.objects.filter(pk__in=content_type_pk_set):
        model = ct.model_class()
        queryset = model.objects.filter(**{f"_custom_field_data__{field_key}__isnull": False})
        pks = []
        display = ""
        if change_context is not None:
            pks, display = _pks_and_display(queryset)
        elif verbose:
            _, display = _count_and_display(queryset)
        count = queryset.update(_custom_field_data=JSONRemove("_custom_field_data", field_key))
        if count:
            if verbose:
                job_logger.info(
                    "cf_cleanup.orphan_sweep: Deleted custom field `%s` values from %d %s object(s): %s",
                    field_key,
                    count,
                    ct.model,
                    display,
                )
            else:
                print(
                    f"cf_cleanup.orphan_sweep: Deleted custom field `{field_key}` values from {count} {ct.model} object(s).",
                    file=sys.stderr,
                )
        else:
            job_logger.debug("No objects had values for custom field `%s` on %s.", field_key, ct.model)
        if count and change_context is not None:
            # Since we used update() above, we bypassed ObjectChange automatic creation via signals. Create them now
            _generate_bulk_object_changes(change_context, model.objects.filter(pk__in=pks))


def _is_badtype(field, value):
    """
    Return True if `value` is the wrong Python type for `field`.

    Distinguishes type errors (type-mismatch reset) from validation errors where the type is
    correct but the value fails rules like regex/min/max/choice (validation-failure warning).
    """
    from datetime import date

    if field.type in (
        CustomFieldTypeChoices.TYPE_TEXT,
        CustomFieldTypeChoices.TYPE_URL,
        CustomFieldTypeChoices.TYPE_MARKDOWN,
        CustomFieldTypeChoices.TYPE_SELECT,
    ):
        return not isinstance(value, str)
    if field.type == CustomFieldTypeChoices.TYPE_INTEGER:
        return not isinstance(value, int)
    if field.type == CustomFieldTypeChoices.TYPE_BOOLEAN:
        return not isinstance(value, bool)
    if field.type == CustomFieldTypeChoices.TYPE_DATE:
        return not isinstance(value, (date, str))
    if field.type == CustomFieldTypeChoices.TYPE_MULTISELECT:
        return not isinstance(value, list)
    return False  # TYPE_JSON: any value is a valid type


def cleanup_custom_field_data(
    field_id=None,
    content_type_pk_set=None,
    change_context=None,
    dryrun=False,
    safe_change=False,
    verbose=False,
    job_logger=logger,
):
    """
    Cleanup values for a custom field which are no longer valid based on the field's current configuration.

    This will add defaults of any empty data, add null's where field exists but column has no key, and remove any data for select/multiselect choices which are no longer valid.
    Remove any orphaned custom field data across all models (if field_id and content_type_pk_set are both None).

    Args:
        field_id (uuid4): The PK of the custom field being cleaned up
        content_type_pk_set (list): List of PKs for content types to act upon
        change_context (dict): Optional change context for ObjectChange creation
        dryrun (bool): If True, execute all changes inside a transaction that is rolled back
            at the end. Logs reflect what would have changed. Implies verbose=True. Defaults to False.
        safe_change (bool): If True, only run the additive provision step.
            All destructive steps (scope sweep, required null→default, type-mismatch reset,
            choice repair, orphan sweep) are skipped.
            Defaults to False.
        verbose (bool): If True, log each affected object by name/pk rather than just an aggregate
            count. dryrun=True automatically enables this. Defaults to False.
    """
    # For each CustomField x ContentType pair:
    # │
    # ├─ Provision: add missing keys (absent or SQL-null) with field.default.
    # ├─ Required-field warning: log WARNING for objects still empty after provisioning.
    # ├─ Required null→default: set JSON-null values to default (covers the case
    # │             where the key exists as JSON null, which provisioning misses in PostgreSQL).
    # ├─ Scope sweep: if field has scope_filter, set key to null on out-of-scope objects.
    # ├─ Choice repair: SELECT/MULTISELECT: replace invalid choice values with default (or None).
    # └─ Type-mismatch reset / validation-failure warning: validate each non-null value;
    #                 reset wrong-type values in bulk; log (noop) for values that are the right
    #                 type but fail validation rules.
    #
    # If is_all (no field_id and no content_type_pk_set):
    # └─ Orphan sweep: scan all models for JSON keys that have no corresponding
    #                  CustomField definition and remove them.
    #
    # safe_change=True: only provision runs; all destructive steps are skipped.
    # dryrun=True: all mutations execute inside a transaction that is rolled back at the end.
    # verbose=True (or dryrun=True): log each affected object individually instead of just counts.
    from nautobot.extras.models import CustomField
    from nautobot.extras.utils import FeatureQuery

    _verbose = dryrun or verbose  # dryrun implies verbose

    is_all = False
    if field_id is None and content_type_pk_set is None:
        # If this is set, we will clean up all orphaned custom field data across all models.
        is_all = True
    if field_id is None:
        fields = CustomField.objects.all()
    else:
        fields = CustomField.objects.filter(pk=field_id)

    with transaction.atomic():
        for field in fields:
            content_types = field.content_types.all()
            if content_type_pk_set is not None:
                content_types = content_types.filter(pk__in=content_type_pk_set)
            # Pre-fetch ContentType→model mapping and scope querysets once per field so that the
            # inner loops below reuse them instead of re-querying the DB and re-instantiating
            # FilterSet classes on every pass.
            ct_list = list(content_types)
            ct_pks = [ct.pk for ct in ct_list]
            model_map = {
                ct.pk: ct.model_class() for ct in ct_list if hasattr(ct, "model_class") and ct.model_class() is not None
            }
            in_scope_map = {
                ct_pk: _get_in_scope_queryset(field, model_map[ct_pk], job_logger=job_logger) for ct_pk in ct_pks
            }

            provision_field(
                field.pk,
                ct_pks,
                change_context=change_context,
                dryrun=dryrun,
                verbose=_verbose,
                job_logger=job_logger,
            )

            # Required-field warning: log required fields that have empty values with no default to fill them.
            # We use KeyTextTransform (which generates the ->> operator in PostgreSQL) rather than a
            # plain __isnull filter. The -> operator used by __isnull preserves JSON null as a JSONB
            # value, so IS NULL does not match it. The ->> operator converts JSON null to SQL NULL,
            # so it correctly catches both absent keys and JSON null values.
            if field.required and field.default is None:
                for ct_pk in ct_pks:
                    model = model_map[ct_pk]
                    in_scope_qs = in_scope_map[ct_pk]
                    empty_qs = in_scope_qs.annotate(
                        _cf_key_text=KeyTextTransform(field.key, "_custom_field_data")
                    ).filter(_cf_key_text__isnull=True)
                    count, display = _count_and_display(empty_qs)
                    if count:
                        job_logger.warning(
                            "cf_cleanup.validation_failed_required: Required field `%s` has %d %s object(s) "
                            "with missing/empty value and no default to apply: %s",
                            field.key,
                            count,
                            model._meta.label,
                            display,
                        )

            # Required null→default: required + defaulted — set any in-scope objects whose key
            # exists but has JSON null to the default value.  provision_field already handles
            # absent keys; this pass handles the "key present with null" case which __isnull=True
            # does not detect in PostgreSQL (JSON null != SQL NULL for the -> operator).
            if field.required and field.default is not None and not safe_change:
                for ct_pk in ct_pks:
                    model = model_map[ct_pk]
                    in_scope_qs = in_scope_map[ct_pk]
                    null_with_key_qs = (
                        in_scope_qs.filter(_custom_field_data__has_key=field.key)
                        .annotate(_cf_key_text=KeyTextTransform(field.key, "_custom_field_data"))
                        .filter(_cf_key_text__isnull=True)
                    )
                    before_count, display = _count_and_display(null_with_key_qs) if _verbose else (0, "")
                    if dryrun and before_count:
                        job_logger.info(
                            "cf_cleanup.required_null_to_default: Would set `%s` = %r on %d %s object(s): %s",
                            field.key,
                            field.default,
                            before_count,
                            model._meta.label,
                            display,
                        )
                    count = null_with_key_qs.update(
                        _custom_field_data=JSONSet("_custom_field_data", field.key, field.default)
                    )
                    if count:
                        job_logger.info(
                            "cf_cleanup.default_applied: Set `%s` = %r on %d %s object(s): %s",
                            field.key,
                            field.default,
                            count,
                            model._meta.label,
                            display,
                        )

            # Scope sweep: set key to null on objects that are no longer in scope for this field
            if field.scope_filter and not safe_change:
                for ct_pk in ct_pks:
                    model = model_map[ct_pk]
                    in_scope_qs = in_scope_map[ct_pk]
                    out_of_scope_with_key = model.objects.filter(
                        **{f"_custom_field_data__{field.key}__isnull": False}
                    ).exclude(pk__in=in_scope_qs.values("pk"))
                    before_count, display = _count_and_display(out_of_scope_with_key) if _verbose else (0, "")
                    if dryrun and before_count:
                        job_logger.info(
                            "cf_cleanup.scope_sweep: Would set key `%s` to null on %d %s object(s): %s",
                            field.key,
                            before_count,
                            model._meta.label,
                            display,
                        )
                    nullified = out_of_scope_with_key.update(
                        _custom_field_data=JSONSet("_custom_field_data", field.key, None)
                    )
                    if nullified:
                        if _verbose:
                            job_logger.info(
                                "cf_cleanup.scope_sweep: Set key `%s` to null on %d %s object(s): %s",
                                field.key,
                                nullified,
                                model._meta.label,
                                display,
                            )
                        else:
                            job_logger.info(
                                "cf_cleanup.scope_sweep: Set key `%s` to null on %d %s object(s).",
                                field.key,
                                nullified,
                                model._meta.label,
                            )

            for ct_pk in ct_pks:
                model = model_map[ct_pk]

                queryset = in_scope_map[ct_pk]

                # Choice repair: replace invalid values for select/multiselect fields.
                # Note: the validation-failure warning policy recommends log-only (noop) for invalid
                # values, but SELECT/MULTISELECT auto-repair (replace invalid choice with default or
                # None) is a deliberate product decision that predates that recommendation. Stale
                # choice values are unusable in the UI, so replacing them is preferable to leaving
                # bad data in place.
                if field.type in [CustomFieldTypeChoices.TYPE_SELECT, CustomFieldTypeChoices.TYPE_MULTISELECT]:
                    if not safe_change:
                        valid_choices = set(field.choices)
                        if field.default is None:
                            valid_choices.add(None)

                        if field.type == CustomFieldTypeChoices.TYPE_SELECT:
                            queryset = queryset.exclude(**{f"_custom_field_data__{field.key}__in": valid_choices})
                            if queryset.exists():
                                new_value = field.default if field.default is not None else None
                                if (
                                    isinstance(new_value, list)
                                    and field.type == CustomFieldTypeChoices.TYPE_MULTISELECT
                                ):
                                    new_value = new_value[0]
                                for old_value in queryset.values_list(f"_custom_field_data__{field.key}", flat=True):
                                    # JSON null leaks through the __in exclude (JSONB null != SQL NULL
                                    # for the -> operator), so guard against no-op calls.
                                    if old_value != new_value:
                                        update_custom_field_choice_data(
                                            field.id, old_value, new_value, change_context=None, job_logger=job_logger
                                        )

                        if field.type == CustomFieldTypeChoices.TYPE_MULTISELECT:
                            invalid_choices = set(
                                obj
                                for obj in queryset.values_list(f"_custom_field_data__{field.key}", flat=True)
                                if obj
                                for obj in (obj if isinstance(obj, list) else [obj])
                                if obj not in valid_choices
                            )
                            for invalid in invalid_choices:
                                new_queryset = queryset
                                new_queryset = new_queryset.filter(
                                    **{f"_custom_field_data__{field.key}__contains": [invalid]}
                                )

                                if new_queryset.exists():
                                    new_value = field.default if field.default is not None else None
                                    if isinstance(new_value, list):
                                        new_value = new_value[0]
                                    old_value = invalid
                                    update_custom_field_choice_data(
                                        field.id, old_value, new_value, change_context=None, job_logger=job_logger
                                    )

                else:
                    # Type-mismatch reset / validation-failure warning: for all other field types, iterate
                    # in-scope objects with a non-null value and validate each one.
                    #
                    # Type-mismatch reset: wrong Python type → reset to default or empty (destructive).
                    # Validation-failure warning: correct type but fails validation rules → log only (noop).
                    #
                    # PKs are collected during the loop and flushed in two bulk updates afterward
                    # to avoid issuing one individual save() per invalid object.
                    objects_with_value = queryset.annotate(
                        _cf_key_text=KeyTextTransform(field.key, "_custom_field_data")
                    ).filter(_cf_key_text__isnull=False)
                    badtype_to_default_pks = []
                    badtype_to_null_pks = []
                    try:
                        model._meta.get_field("name")
                        _vl_fields = ("pk", "_custom_field_data", "name")
                    except FieldDoesNotExist:
                        _vl_fields = ("pk", "_custom_field_data")
                    for row in objects_with_value.values_list(*_vl_fields).iterator(chunk_size=1000):
                        if len(row) == 3:
                            pk, cf_data, name = row
                            obj_id = f"{name!r} (pk={pk})"
                        else:
                            pk, cf_data = row
                            obj_id = str(pk)
                        value = cf_data.get(field.key)
                        if value is None:
                            continue
                        try:
                            field.validate(value, enforce_required=False)
                        except ValidationError:
                            if _is_badtype(field, value):
                                if field.default is not None:
                                    # Type-mismatch reset: wrong type + default exists → todefault (destructive)
                                    job_logger.info(
                                        "cf_cleanup.type_reset: Resetting bad-type value for field `%s` "
                                        "on %s %s (was %r, now %r).",
                                        field.key,
                                        model._meta.label,
                                        obj_id,
                                        value,
                                        field.default,
                                    )
                                    badtype_to_default_pks.append(pk)
                                elif field.required:
                                    # Type-mismatch reset: wrong type + required + no default → log failure, noop
                                    job_logger.warning(
                                        "cf_cleanup.validation_failed_required: Field `%s` on %s %s "
                                        "has bad-type value %r and no default to recover with.",
                                        field.key,
                                        model._meta.label,
                                        obj_id,
                                        value,
                                    )
                                else:
                                    # Type-mismatch reset: wrong type + optional + no default → toempty (destructive)
                                    job_logger.info(
                                        "cf_cleanup.type_reset: Resetting bad-type value for field `%s` "
                                        "on %s %s (was %r, now None).",
                                        field.key,
                                        model._meta.label,
                                        obj_id,
                                        value,
                                    )
                                    badtype_to_null_pks.append(pk)
                            else:
                                # Validation-failure warning: correct type but fails validation rules → log, no mutation
                                job_logger.warning(
                                    "cf_cleanup.validation_failed%s: Field `%s` on %s %s has invalid value %r.",
                                    "_required" if field.required else "_optional",
                                    field.key,
                                    model._meta.label,
                                    obj_id,
                                    value,
                                )
                    # Flush accumulated type-reset PKs in at most two bulk updates.
                    if not safe_change:
                        if badtype_to_default_pks:
                            model.objects.filter(pk__in=badtype_to_default_pks).update(
                                _custom_field_data=JSONSet("_custom_field_data", field.key, field.default)
                            )
                        if badtype_to_null_pks:
                            model.objects.filter(pk__in=badtype_to_null_pks).update(
                                _custom_field_data=JSONSet("_custom_field_data", field.key, None)
                            )

        if is_all and not safe_change:
            valid_keys = set(CustomField.objects.values_list("key", flat=True))
            orphaned_keys_to_ct_pks = {}

            for ct in ContentType.objects.filter(FeatureQuery("custom_fields").get_query()):
                model = ct.model_class()
                if model is None:
                    continue
                data_iterator = (
                    model.objects.exclude(_custom_field_data={}).values_list("_custom_field_data", flat=True).iterator()
                )
                # Tracks orphaned keys this CT. As there is no need to process it again for every
                # subsequent row, since it will be bulk updated in delete_custom_field_data.
                known_orphaned_keys = set()

                for data in data_iterator:
                    if not isinstance(data, dict):
                        job_logger.warning(
                            "Skipping non-dict _custom_field_data on %s (got %r); this indicates data corruption.",
                            model._meta.label,
                            type(data).__name__,
                        )
                        continue
                    orphaned_in_obj = set(data.keys()) - valid_keys - known_orphaned_keys
                    if orphaned_in_obj:
                        for key in orphaned_in_obj:
                            orphaned_keys_to_ct_pks.setdefault(key, set()).add(ct.pk)
                            known_orphaned_keys.add(key)

            for key, ct_pk_set in orphaned_keys_to_ct_pks.items():
                delete_custom_field_data(key, list(ct_pk_set), change_context, verbose=_verbose, job_logger=job_logger)

        if dryrun:
            transaction.set_rollback(True)


def _get_in_scope_queryset(field, model, job_logger=logger):
    """
    Return a queryset of `model` objects that are in scope for `field`.

    If `field.scope_filter` is empty, returns all objects.
    Falls back to all objects if no filterset class exists for the model or the stored filter is invalid.
    """
    from nautobot.core.utils.lookup import get_filterset_for_model

    if not field.scope_filter:
        return model.objects.all()

    filterset_class = get_filterset_for_model(model)
    if not filterset_class:
        job_logger.warning(
            "Custom field `%s` has scope_filter set but no filterset exists for %s; treating all objects as in-scope.",
            field.key,
            model._meta.label,
        )
        return model.objects.all()

    filterset = filterset_class(data=field.scope_filter, queryset=model.objects.all())
    if not filterset.form.is_valid():
        job_logger.warning(
            "Custom field `%s` has an invalid scope_filter for %s: %s; treating all objects as in-scope.",
            field.key,
            model._meta.label,
            filterset.form.errors.as_text(),
        )
        return model.objects.all()

    return filterset.qs


def provision_field(field_id, content_type_pk_set, change_context=None, dryrun=False, verbose=False, job_logger=logger):
    from nautobot.extras.models import CustomField

    _verbose = dryrun or verbose

    try:
        field = CustomField.objects.get(pk=field_id)
    except CustomField.DoesNotExist:
        job_logger.error(f"Custom field with ID {field_id} not found, failing to provision.")
        raise

    for ct in ContentType.objects.filter(pk__in=content_type_pk_set):
        model = ct.model_class()
        if model is None:
            continue
        in_scope_qs = _get_in_scope_queryset(field, model, job_logger=job_logger)
        queryset = in_scope_qs.filter(**{f"_custom_field_data__{field.key}__isnull": True})
        pk_list = []
        display = ""
        before_count = 0
        if change_context is not None:
            pk_list, display = _pks_and_display(queryset)
            before_count = len(pk_list)
        elif _verbose:
            before_count, display = _count_and_display(queryset)
        if dryrun and before_count:
            job_logger.info(
                "cf_cleanup.provision: Would set `%s` = %r on %d %s object(s): %s",
                field.key,
                field.default,
                before_count,
                ct.model,
                display,
            )
        elif dryrun:
            print(f"cf_cleanup.provision: No objects to provision for `{field.key}` on {ct.model}.", file=sys.stderr)
        count = queryset.update(_custom_field_data=JSONSet("_custom_field_data", field.key, field.default))
        if count:
            if _verbose:
                job_logger.info(
                    "cf_cleanup.provision: Set `%s` = %r on %d %s object(s): %s",
                    field.key,
                    field.default,
                    count,
                    ct.model,
                    display,
                    extra={"object": field},
                )
            else:
                job_logger.info(
                    "cf_cleanup.provision: Set `%s` = %r on %d %s object(s).",
                    field.key,
                    field.default,
                    count,
                    ct.model,
                    extra={"object": field},
                )
        elif not dryrun:
            print(
                f"cf_cleanup.provision: No objects needed provisioning for `{field.key}` on {ct.model}.",
                file=sys.stderr,
            )
        if count and change_context is not None:
            # Since we used update() above, we bypassed ObjectChange automatic creation via signals. Create them now
            _generate_bulk_object_changes(change_context, model.objects.filter(pk__in=pk_list))

        # If the field has a scope_filter, out-of-scope objects also need the key initialized to
        # null so that every content-type object has the key present.  Without a scope_filter,
        # in_scope_qs is all objects, so the first pass already covered everyone.
        if field.scope_filter:
            out_of_scope_missing = model.objects.exclude(pk__in=in_scope_qs.values("pk")).filter(
                **{f"_custom_field_data__{field.key}__isnull": True}
            )
            out_of_scope_missing.update(_custom_field_data=JSONSet("_custom_field_data", field.key, None))

    return True


def enqueue_custom_field_job(job_class, user, **job_kwargs):
    """Enqueue a system Custom Field job via JobResult.enqueue_job."""
    from nautobot.extras.models import Job, JobResult

    if user is None:
        logger.error(
            "Cannot enqueue %s: no authenticated user available in the current change context.",
            job_class.__name__,
        )
        return
    try:
        job_model = job_class().job_model
    except Job.DoesNotExist:
        logger.error("Cannot enqueue %s: no Job model found in database.", job_class.__name__)
        return
    JobResult.enqueue_job(job_model, user, **job_kwargs)
