"""GraphQL Object Lock state for every object type.

Provides the per-request/per-content-type lookup helper (``claims_for_object``) and
``extend_schema_type_object_lock`` which adds ``is_locked`` / ``locked_for_delete`` /
``locked_for_update`` / ``locked_fields`` / ``locks`` to a generated type. Resolving lock state
across many objects costs one query per content type rather than N.
"""

from collections import defaultdict
import logging

from django.conf import settings
import graphene

from nautobot.extras.models import ObjectLock

logger = logging.getLogger(__name__)


def claims_for_object(request, content_type_id, object_id):
    """Return the active ObjectLock claims for one object, O(1) per content type per request.

    On the first lookup for a given content type within a request, all active locks for that content
    type are fetched in a single query, grouped, and cached on the request. Subsequent lookups — for
    both locked and unlocked objects — are served from that cache without further queries. This keeps a
    multi-object GraphQL query at one Object Lock query per content type rather than one per object.

    Args:
        request: The current request (carries the per-request cache).
        content_type_id (int): ContentType PK of the target model.
        object_id: PK of the target object.

    Returns:
        list: Active ObjectLock instances for the object (empty list when unlocked).
    """
    if not settings.OBJECT_LOCK_ENFORCED:
        return []  # kill switch: the whole feature (enforcement + surfacing) is off
    cache = getattr(request, "_object_lock_claims_cache", None)
    if cache is None:
        cache = {}
        request._object_lock_claims_cache = cache

    if content_type_id not in cache:
        grouped = defaultdict(list)
        for claim in ObjectLock.objects.active().filter(content_type_id=content_type_id).select_related("created_by"):
            grouped[str(claim.object_id)].append(claim)
        cache[content_type_id] = grouped

    return cache[content_type_id].get(str(object_id), [])


def extend_schema_type_object_lock(schema_type):
    """Add Object Lock state fields + a ``locks`` resolver to a generated object type.

    Adds ``is_locked`` / ``locked_for_delete`` / ``locked_for_update`` (always visible) plus
    ``locked_fields`` / ``locks`` (gated behind ``extras.view_objectlock``). All resolution flows through
    ``claims_for_object`` (which reads the per-request/per-content-type cache), so a multi-object query
    costs one Object Lock query per content type rather than one per object.

    Field declaration mirrors the existing dynamic-field helpers in
    ``nautobot.core.graphql.schema`` (``graphene.Field.mounted`` + a ``resolve_<name>`` attribute). Any
    field whose name already exists on the type (e.g. a real model field/relationship) is skipped so a
    model's own field is never clobbered.

    Args:
        schema_type (DjangoObjectType): GraphQL Object type for a given model.

    Returns:
        (DjangoObjectType): The extended schema_type object.
    """
    from django.contrib.contenttypes.models import ContentType

    from nautobot.extras.graphql.types import ObjectLockType
    from nautobot.extras.object_lock_ui import user_can_view_lock_metadata

    model = schema_type._meta.model

    def _claims(self, info):
        ct_id = ContentType.objects.get_for_model(model).pk
        return claims_for_object(info.context, ct_id, self.pk)

    def resolve_is_locked(self, info):
        return bool(_claims(self, info))

    def resolve_locked_for_delete(self, info):
        return any(c.prevent_delete for c in _claims(self, info))

    def resolve_locked_for_update(self, info):
        return any(c.prevent_update for c in _claims(self, info))

    def resolve_locked_fields(self, info):
        if not user_can_view_lock_metadata(info.context.user):
            return []
        fields = set()
        for c in _claims(self, info):
            if c.prevent_update and c.locked_fields:
                fields.update(c.locked_fields)
        return sorted(fields)

    def resolve_locks(self, info):
        if not user_can_view_lock_metadata(info.context.user):
            return []
        return _claims(self, info)

    # (field_name, mounted graphene field, resolver). Mirrors the attachment mechanism used by the other
    # extend_schema_type_* helpers (schema.py): declare in _meta.fields + set resolve_<name>.
    lock_fields = (
        ("is_locked", graphene.Field.mounted(graphene.Boolean()), resolve_is_locked),
        ("locked_for_delete", graphene.Field.mounted(graphene.Boolean()), resolve_locked_for_delete),
        ("locked_for_update", graphene.Field.mounted(graphene.Boolean()), resolve_locked_for_update),
        ("locked_fields", graphene.Field.mounted(graphene.List(graphene.String)), resolve_locked_fields),
        ("locks", graphene.Field.mounted(graphene.List(ObjectLockType)), resolve_locks),
    )

    for field_name, mounted_field, resolver in lock_fields:
        resolver_name = f"resolve_{field_name}"
        # Collision guard: never clobber a model's own field/relationship/resolver of the same name.
        if field_name in schema_type._meta.fields or hasattr(schema_type, resolver_name):
            logger.warning(
                'Unable to add Object Lock field "%s" to %s because there is already an attribute '
                "mapped to the same name; skipping.",
                field_name,
                schema_type._meta.name,
            )
            continue
        schema_type._meta.fields[field_name] = mounted_field
        setattr(schema_type, resolver_name, resolver)

    return schema_type
