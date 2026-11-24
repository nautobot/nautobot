"""Find the records that the system jobs can delete without failing or deleting records they should not."""

from django.contrib.contenttypes.fields import GenericRel, GenericRelation
from django.db.models import CASCADE, DO_NOTHING, PROTECT, RESTRICT


def _get_reverse_relations(model):
    """
    List the relations through which deleting a `model` record affects other records.

    Returns:
        (list): `(lookup, related_model, on_delete)` triples, where `lookup` reaches the related records from `model`.
    """
    # A ManyToManyRel has no `on_delete`; deleting a record deletes only its rows in the through table. A custom
    # through model is listed here in its own right, through the ForeignKey it holds to `model`.
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


def find_relations_of_concern(model, preapproved_models_that_can_be_deleted=(), force_cascade_delete=False):
    """
    Find the reverse relations through which deleting `model` records would fail or would delete other records.

    The search follows every relation that a deletion cascades through, so that a relation several steps away
    from `model` is found as well as one that points at `model` directly. Each relation is reported as a
    lookup path from `model`, such as `job_log_entries__example_models`.

    - A relation with `on_delete` set to `PROTECT`, `RESTRICT` or `DO_NOTHING` is reported as blocking. A
      referenced record cannot be deleted, or deleting it would leave the referencing record pointing at a row
      that no longer exists.
    - A relation with `on_delete=CASCADE`, or a `GenericRelation`, is reported as cascading, because deleting a
      referenced record also deletes the referencing records. With `force_cascade_delete` the search continues
      past it instead, to find any blocking relation on the records that the cascade would delete.
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
        (tuple[list, list]): `(blocking_relations, cascading_relations)`. Each is a list of
            `(lookup, related_model)` pairs sorted by lookup, where `related_model` is the model at the end of
            the lookup.
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
        blocking_relations = {}
        cascading_relations = {}

        for lookup, related_model, on_delete in _get_reverse_relations(current_model):
            if related_model not in preapproved_models:
                if on_delete in (PROTECT, RESTRICT, DO_NOTHING):
                    blocking_relations[lookup] = related_model
                    continue
                if on_delete is not CASCADE:
                    continue
                if not force_cascade_delete:
                    cascading_relations[lookup] = related_model
                    continue

            if related_model in models_being_searched:
                # The cascade returns to a model whose relations are already being searched, so they are reported
                # where that model first appears. A lookup path cannot follow the cascade around the cycle to every
                # depth it reaches. A blocking reference further round makes the deletion raise `ProtectedError`
                # or `RestrictedError`, which stops the run rather than deleting records that should be kept.
                continue

            nested_blocking_relations, nested_cascading_relations = search(related_model, ())
            for nested_lookup, nested_related_model in nested_blocking_relations.items():
                blocking_relations[f"{lookup}__{nested_lookup}"] = nested_related_model
            for nested_lookup, nested_related_model in nested_cascading_relations.items():
                cascading_relations[f"{lookup}__{nested_lookup}"] = nested_related_model

        models_being_searched.discard(current_model)
        relations_by_model[current_model] = (blocking_relations, cascading_relations)
        return blocking_relations, cascading_relations

    blocking_relations, cascading_relations = search(model, preapproved_models_that_can_be_deleted)
    return sorted(blocking_relations.items()), sorted(cascading_relations.items())


def exclude_records_whose_relations_block_deletion(
    queryset, model, preapproved_models_that_can_be_deleted, force_cascade_delete, logger
):
    """
    Remove from a queryset the records whose deletion would fail or would delete records that should be kept.

    See `find_relations_of_concern` for which relations hold a record back. Records held by a blocking relation
    stay held even with `force_cascade_delete`, because deleting them would fail. The number of records held by
    each relation is logged.

    Args:
        queryset (QuerySet): The records being considered for deletion.
        model (Model): The model the queryset selects from.
        preapproved_models_that_can_be_deleted (tuple): Models whose records referencing `model` the caller
            deletes itself before it deletes the `model` records.
        force_cascade_delete (bool): Whether the caller accepts the deletion of records reached by a cascade.
        logger (Logger): The job logger that the held records are reported to.

    Returns:
        (QuerySet): The records that are safe to delete.
    """
    blocking_relations, cascading_relations = find_relations_of_concern(
        model, preapproved_models_that_can_be_deleted, force_cascade_delete
    )
    model_name = model._meta.object_name

    # `exclude()` is used rather than `filter(<lookup>__isnull=True)`. Across a multi-valued relation, `filter()`
    # keeps a record when any one of its related rows has no reference, for example a job result with two log
    # entries of which only one is referenced. `exclude()` removes the record when any related row has a reference.
    # Blocking relations are checked first, so that a record held for both reasons is reported as one that
    # accepting the cascade cannot release.
    for lookup, related_model in blocking_relations:
        held_record_count = queryset.filter(**{f"{lookup}__isnull": False}).distinct().count()
        if held_record_count:
            logger.info(
                "Skipping %d %s records that are referenced by %s records through `%s`, because those"
                " references prevent their deletion. To include them, first delete the referencing %s records"
                " or remove their references.",
                held_record_count,
                model_name,
                related_model._meta.label,
                lookup,
                related_model._meta.label,
            )
            queryset = queryset.exclude(**{f"{lookup}__isnull": False})

    for lookup, related_model in cascading_relations:
        held_record_count = queryset.filter(**{f"{lookup}__isnull": False}).distinct().count()
        if held_record_count:
            logger.info(
                "Skipping %d %s records that are referenced by %s records through `%s`, because deleting"
                " them would also delete those %s records.",
                held_record_count,
                model_name,
                related_model._meta.label,
                lookup,
                related_model._meta.label,
            )
            queryset = queryset.exclude(**{f"{lookup}__isnull": False})

    return queryset
