"""Find the records that the system jobs can delete without failing or deleting records they should not."""

from typing import NamedTuple

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation
from django.db.models import CASCADE, DO_NOTHING, ForeignObjectRel, PROTECT, RESTRICT

from nautobot.core.models.querysets import restrict_queryset

# `on_delete` options with which a referenced record cannot be deleted, or whose deletion would leave the referencing
# record pointing at a row that no longer exists.
BLOCKING_ON_DELETE = (PROTECT, RESTRICT, DO_NOTHING)


class RelationsOfConcern(NamedTuple):
    """
    The relations that `find_relations_of_concern` found, each a list sorted by lookup.

    `blocking`, `cascading` and `followed` contain `(lookup, related_model)` pairs, where `lookup` is a lookup path
    from the searched model and `related_model` is the model at its end.

    `hidden_blocking` contains `(lookup, field)` pairs for foreign keys that have no reverse lookup, because they are
    declared with a `related_name` ending in `+`. `lookup` reaches the referenced records from the searched model, or
    is empty when they are the searched model's own records, and `field` is the foreign key that references them.
    """

    blocking: list
    cascading: list
    followed: list
    hidden_blocking: list


def _get_reverse_relations(model):
    """
    List the relations through which deleting a `model` record affects other records.

    Returns:
        (list): `(lookup, related_model, on_delete)` triples, where `lookup` reaches the related records from `model`.
    """
    # A ManyToManyRel has no `on_delete`; deleting a record deletes only its rows in the through table. A custom
    # through model is listed here as a separate model, through its ForeignKey to `model`.
    # A GenericRel is the reverse side of a GenericRelation on another model that points at `model`, for example
    # `ObjectMetadata` gets one for every model's `associated_object_metadata`. Django gives it `DO_NOTHING`, but
    # deleting a `model` record leaves the other model's records alone, so it is not a concern.
    # TODO: Handle DB_CASCADE and the other database-level `on_delete` options when Nautobot adopts Django 6.1.
    reverse_relations = [
        (relation.field.related_query_name(), relation.related_model, relation.on_delete)
        for relation in model._meta.related_objects
        if relation.on_delete is not None and not isinstance(relation, GenericRel)
    ]
    # Deleting a record also deletes the records that a GenericRelation on its model points to.
    reverse_relations += [
        (field.name, field.related_model, CASCADE)
        for field in model._meta.private_fields
        if isinstance(field, GenericRelation)
    ]
    return reverse_relations


def _get_hidden_foreign_keys(model):
    """
    List the foreign keys to `model` that have no reverse lookup and that would affect other records on deletion.

    `_meta.related_objects` leaves out a relation whose `related_name` ends in `+`, but Django still applies its
    `on_delete` when a `model` record is deleted. No lookup path can include such a relation, so every `on_delete`
    other than the `SET...` options is a concern. The foreign keys of an automatically created many-to-many through table are left out,
    because deleting a record deletes only its rows there.

    Returns:
        (list): The foreign key fields, on other models, that reference `model`.
    """
    return [
        relation.field
        for relation in model._meta.get_fields(include_hidden=True)
        if isinstance(relation, ForeignObjectRel)
        and relation.hidden
        and not isinstance(relation, GenericRel)
        and not relation.field.model._meta.auto_created
        and (relation.on_delete in BLOCKING_ON_DELETE or relation.on_delete is CASCADE)
    ]


def find_relations_of_concern(model, preapproved_models_that_can_be_deleted=(), force_cascade_delete=False):
    """
    Find the reverse relations through which deleting `model` records would fail or would delete other records.

    The search continues through every relation that a deletion cascades through, so that it finds a relation several
    steps away from `model` as well as one that points at `model` directly. Each relation is reported as a
    lookup path from `model`, such as `job_log_entries__example_models`.

    - A relation with `on_delete` set to `PROTECT`, `RESTRICT` or `DO_NOTHING` is reported as blocking. A
      referenced record cannot be deleted, or deleting it would leave the referencing record pointing at a row
      that no longer exists. `RESTRICT` is treated as blocking even where Django would allow the deletion, which is
      when the referencing record is deleted by the same cascade.
    - A relation with `on_delete=CASCADE`, or a `GenericRelation`, is reported as cascading, because deleting a
      referenced record also deletes the referencing records. With `force_cascade_delete` the search continues
      past it instead, to find any blocking relation on the records that the cascade would delete.
    - A cascade that returns to a model whose relations are already being searched is reported as blocking. A
      lookup path cannot repeat the cycle to every depth, so the records deeper in the cycle cannot be checked.
    - A foreign key with no reverse lookup, because its `related_name` ends in `+`, is reported in `hidden_blocking`
      unless its `on_delete` is one of the `SET...` options. No lookup path can include it, so the records that
      reference through it cannot be checked.
    - A relation with `on_delete` set to `SET_NULL`, `SET_DEFAULT` or `SET(...)`, or a many-to-many relation, is
      not reported. Deleting a record changes or removes only the reference; the referencing records survive.

    Args:
        model (Model): The model whose records are to be deleted.
        preapproved_models_that_can_be_deleted (tuple): Models whose records referencing `model` the caller
            deletes itself before it deletes the `model` records, whatever their `on_delete`. Their own relations
            are still searched. This applies only to relations that point at `model` directly, because only those
            records are deleted by the caller.
        force_cascade_delete (bool): Whether the caller accepts the deletion of records reached by a cascade.

    Returns:
        (RelationsOfConcern): The relations found. `followed` contains the relations that the search continued
            through, which are the relations to a preapproved model and, with `force_cascade_delete`, every cascading
            relation. Their records are deleted along with the `model` records.
    """
    # Many models are reached by more than one path. For example, every `BaseModel` has GenericRelations to
    # `ObjectMetadata` and `DataCompliance`, which are `BaseModel`s too. Each model's relations are therefore
    # searched once and the result is reused, rather than searched again for every path that reaches the model.
    relations_by_model = {}
    models_being_searched = set()

    def search(current_model, preapproved_models):
        if current_model in relations_by_model:
            return relations_by_model[current_model]

        models_being_searched.add(current_model)
        relations = RelationsOfConcern(blocking={}, cascading={}, followed={}, hidden_blocking={})
        for field in _get_hidden_foreign_keys(current_model):
            relations.hidden_blocking[("", field)] = field

        for lookup, related_model, on_delete in _get_reverse_relations(current_model):
            if related_model not in preapproved_models:
                if on_delete in BLOCKING_ON_DELETE:
                    relations.blocking[lookup] = related_model
                    continue
                if on_delete is not CASCADE:
                    continue
                if not force_cascade_delete:
                    relations.cascading[lookup] = related_model
                    continue

            if related_model in models_being_searched:
                relations.blocking[lookup] = related_model
                continue

            relations.followed[lookup] = related_model
            nested_relations = search(related_model, ())
            for kind in ("blocking", "cascading", "followed"):
                for nested_lookup, nested_related_model in getattr(nested_relations, kind).items():
                    getattr(relations, kind)[f"{lookup}__{nested_lookup}"] = nested_related_model
            for (nested_lookup, field), _ in nested_relations.hidden_blocking.items():
                nested_path = f"{lookup}__{nested_lookup}" if nested_lookup else lookup
                relations.hidden_blocking[(nested_path, field)] = field

        models_being_searched.discard(current_model)
        relations_by_model[current_model] = relations
        return relations

    found_relations = search(model, preapproved_models_that_can_be_deleted)
    return RelationsOfConcern(
        blocking=sorted(found_relations.blocking.items()),
        cascading=sorted(found_relations.cascading.items()),
        followed=sorted(found_relations.followed.items()),
        hidden_blocking=sorted(found_relations.hidden_blocking, key=lambda pair: (pair[0], str(pair[1]))),
    )


def _describe_reference_path(model, lookup, referencing_field=None):
    """
    Describe how records reference a `model` record, as the chain of foreign keys from the referencing record.

    A reverse lookup path names each step by the name of its reverse relation, which some relations do not have. The
    description names each step by its foreign key instead, starting from the referencing record. For example, the
    lookup `job_log_entries__more_example_models` from `JobResult` is described as
    `example_app.AnotherExampleModel.job_log_entry -> extras.JobLogEntry.job_result`.

    Args:
        model (Model): The model that `lookup` starts from.
        lookup (str): A reverse lookup path from `model`, or an empty string.
        referencing_field (Field): A foreign key with no reverse relation that references the records at the end of
            `lookup`, or `None`.

    Returns:
        (str): The foreign keys, joined by ` -> `.
    """
    foreign_key_names = []
    current_model = model
    for segment in lookup.split("__") if lookup else []:
        relation = current_model._meta.get_field(segment)
        referencing_model = relation.related_model
        if isinstance(relation, GenericRelation):
            # The step is named by the generic foreign key that matches the GenericRelation's object ID field.
            foreign_key_name = next(
                (
                    generic_foreign_key.name
                    for generic_foreign_key in referencing_model._meta.private_fields
                    if isinstance(generic_foreign_key, GenericForeignKey)
                    and generic_foreign_key.fk_field == relation.object_id_field_name
                ),
                relation.object_id_field_name,
            )
        else:
            foreign_key_name = relation.field.name
        foreign_key_names.append(f"{referencing_model._meta.label}.{foreign_key_name}")
        current_model = referencing_model
    if referencing_field is not None:
        foreign_key_names.append(f"{referencing_field.model._meta.label}.{referencing_field.name}")
    return " -> ".join(reversed(foreign_key_names))


def exclude_records_whose_relations_block_deletion(
    queryset, model, preapproved_models_that_can_be_deleted, force_cascade_delete, logger
):
    """
    Remove from a queryset the records whose deletion would fail or would delete records that should be kept.

    See `find_relations_of_concern` for which relations keep a record from deletion. Records that a blocking relation
    keeps from deletion are still skipped with `force_cascade_delete`, because deleting them would fail or could not
    be checked. The number of records skipped for each relation is logged.

    Args:
        queryset (QuerySet): The records being considered for deletion.
        model (Model): The model the queryset selects from.
        preapproved_models_that_can_be_deleted (tuple): Models whose records referencing `model` the caller
            deletes itself before it deletes the `model` records.
        force_cascade_delete (bool): Whether the caller accepts the deletion of records reached by a cascade.
        logger (Logger): The job logger that the skipped records are reported to.

    Returns:
        (QuerySet): The records that are safe to delete.
    """
    relations = find_relations_of_concern(model, preapproved_models_that_can_be_deleted, force_cascade_delete)
    model_name = model._meta.object_name

    # `exclude()` is used rather than `filter(<lookup>__isnull=True)`. Across a multi-valued relation, `filter()`
    # keeps a record when any one of its related rows has no reference, for example a job result with two log
    # entries of which only one is referenced. `exclude()` removes the record when any related row has a reference.
    # Blocking relations are checked first. A record that is skipped for both reasons is then reported as blocked,
    # because accepting the cascade would still not make it deletable.
    # Each blocking relation, with or without a reverse relation, is a filter on the queryset and the referencing model.
    blocking_filters = [
        ({f"{lookup}__isnull": False}, _describe_reference_path(model, lookup), related_model)
        for lookup, related_model in relations.blocking
    ]
    for lookup, field in relations.hidden_blocking:
        referenced_values = field.model._base_manager.filter(**{f"{field.name}__isnull": False}).values(field.attname)
        target_lookup = f"{lookup}__{field.target_field.attname}__in" if lookup else f"{field.target_field.attname}__in"
        blocking_filters.append(
            ({target_lookup: referenced_values}, _describe_reference_path(model, lookup, field), field.model)
        )

    for referenced_filter, reference_path, referencing_model in blocking_filters:
        skipped_record_count = queryset.filter(**referenced_filter).distinct().count()
        if skipped_record_count:
            logger.info(
                "Skipping %d %s records that are still referenced through %s. To include them, first delete the"
                " referencing %s records or remove their references.",
                skipped_record_count,
                model_name,
                reference_path,
                referencing_model._meta.label,
            )
            queryset = queryset.exclude(**referenced_filter)

    for lookup, related_model in relations.cascading:
        skipped_record_count = queryset.filter(**{f"{lookup}__isnull": False}).distinct().count()
        if skipped_record_count:
            logger.info(
                "Skipping %d %s records that are referenced through %s, because deleting them would also delete"
                " those %s records.",
                skipped_record_count,
                model_name,
                _describe_reference_path(model, lookup),
                related_model._meta.label,
            )
            queryset = queryset.exclude(**{f"{lookup}__isnull": False})

    return queryset


def exclude_records_whose_dependents_the_user_cannot_delete(
    queryset, model, preapproved_models_that_can_be_deleted, force_cascade_delete, user, logger
):
    """
    Remove from a queryset the records whose deletion would delete records that the user may not delete.

    Deleting a record deletes the records that cascade from it, whatever the user's permissions on them. A user who
    may delete a record, but not everything that is deleted with it, would otherwise delete those records too. The
    records that are checked are those reached through the `followed` relations that `find_relations_of_concern`
    returns for the same arguments. A model whose queryset has no
    `restrict()` method is not permission-checked, so its records count as permitted. The number of records skipped
    for each relation is logged.

    Args:
        queryset (QuerySet): The records being considered for deletion.
        model (Model): The model the queryset selects from.
        preapproved_models_that_can_be_deleted (tuple): See `find_relations_of_concern`.
        force_cascade_delete (bool): See `find_relations_of_concern`.
        user (User): The user whose permissions are checked.
        logger (Logger): The job logger that the skipped records are reported to.

    Returns:
        (QuerySet): The records whose deletion deletes only records that the user may delete.
    """
    relations = find_relations_of_concern(model, preapproved_models_that_can_be_deleted, force_cascade_delete)
    model_name = model._meta.object_name

    for lookup, related_model in relations.followed:
        all_related_records = related_model._default_manager.all()
        permitted_related_records = restrict_queryset(all_related_records, user, "delete")
        # A queryset with no filter means the user may delete every record, so there is nothing to skip.
        if not permitted_related_records.query.where:
            continue
        unpermitted_related_records = all_related_records.exclude(pk__in=permitted_related_records.values("pk"))
        # As in `exclude_records_whose_relations_block_deletion`, `exclude()` removes a record when any one of its
        # related records matches, across a multi-valued relation.
        skipped_record_count = queryset.filter(**{f"{lookup}__in": unpermitted_related_records}).distinct().count()
        if skipped_record_count:
            logger.info(
                "Skipping %d %s records whose deletion would also delete the %s records that reference them through"
                " %s. User %s is not permitted to delete those %s records.",
                skipped_record_count,
                model_name,
                related_model._meta.label,
                _describe_reference_path(model, lookup),
                user,
                related_model._meta.label,
            )
            queryset = queryset.exclude(**{f"{lookup}__in": unpermitted_related_records})

    return queryset
