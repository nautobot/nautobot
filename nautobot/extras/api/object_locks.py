"""REST API serializer and viewset mixin for ObjectLock."""

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_field
from rest_framework import serializers as drf_serializers, status as drf_status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from nautobot.core.api.authentication import TokenPermissions
from nautobot.core.api.serializers import BaseModelSerializer
from nautobot.extras.models import ObjectLock
from nautobot.extras.models.object_locks import OBJECT_LOCK_SOURCE_KEY_MAX_LENGTH


def _batch_active_lock_claims(objects):
    """Return ``{object_pk: [ObjectLock, ...]}`` of active claims for *objects* in a single query.

    The objects are assumed to share a content type (a REST list serializes one model), so the filter
    is scoped to that content type — a shared object_id can never match another model's lock.
    """
    objects = list(objects)
    if not objects:
        return {}
    content_type = ContentType.objects.get_for_model(type(objects[0]))
    claims_by_pk = {}
    for claim in ObjectLock.objects.active().filter(
        content_type=content_type, object_id__in=[obj.pk for obj in objects]
    ):
        claims_by_pk.setdefault(claim.object_id, []).append(claim)
    return claims_by_pk


def build_object_locked_response(exc, request):
    """Build the 409 body for a blocked write, honoring ``extras.view_objectlock`` (no metadata leak without it).

    Called from a thin hook in ``nautobot.core.api.views`` (which catches the cross-cutting
    ``ObjectLockedError``) so this Object-Lock logic lives in extras, not core.

    Args:
        exc: The ``ObjectLockedError`` instance that was raised.
        request: The DRF request object.

    Returns:
        A DRF ``Response`` with HTTP 409 Conflict status.
    """
    from nautobot.extras.locking import GATE_MODE_DELETE, GATE_MODE_UPDATE

    user = getattr(request, "user", None)
    can_view = user is not None and user.has_perm("extras.view_objectlock")
    body = {"error_code": "object_locked"}
    if can_view:
        # The precise frozen field name(s) whose change triggered this block.
        body["offending_fields"] = list(getattr(exc, "offending_fields", []))
        instance = next(iter(getattr(exc, "protected_objects", []) or []), None)
        if instance is not None:
            ct = ContentType.objects.get_for_model(instance)
            claims = [
                {
                    "source_key": c.source_key,
                    "prevent_delete": c.prevent_delete,
                    "prevent_update": c.prevent_update,
                    "reason": c.reason,
                    "locked_fields": c.locked_fields,
                }
                for c in ObjectLock.objects.filter(content_type=ct, object_id=instance.pk).active()
            ]
            modes = sorted(
                {GATE_MODE_DELETE for c in claims if c["prevent_delete"]}
                | {GATE_MODE_UPDATE for c in claims if c["prevent_update"]}
            )
            body["detail"] = str(exc)
            body["modes"] = modes
            body["locks"] = claims
    else:
        body["detail"] = "This object is locked and cannot be modified or deleted."
    return Response(body, status=drf_status.HTTP_409_CONFLICT)


class ObjectLockableSerializerMixin(drf_serializers.Serializer):
    """Adds read-only lock-state fields to a model serializer.

    Booleans (`is_locked`/`locked_for_delete`/`locked_for_update`) are always visible.
    `locked_fields` is gated behind `extras.view_objectlock`.
    """

    is_locked = drf_serializers.SerializerMethodField()
    locked_for_delete = drf_serializers.SerializerMethodField()
    locked_for_update = drf_serializers.SerializerMethodField()
    locked_fields = drf_serializers.SerializerMethodField()

    def _claims_for(self, obj):
        """Return the active ObjectLock claims for *obj*, batched once per serialized page.

        Lock state is only meaningful with a request in context. Without one (e.g. change-log
        serialization, which renders objects with `context={"request": None}`) this returns an empty
        list and issues no query, so the boolean getters report False (unlocked) and `locked_fields`
        reports None for free. With a request, every
        object's active claims are resolved in a single query the first time any getter runs — in a
        list response the parent ListSerializer holds the whole page, so all rows share that one query.

        Args:
            obj: A BaseModel instance whose active lock claims are returned.

        Returns:
            list: Active ObjectLock instances, or an empty list when serialized without a request.
        """
        if not settings.OBJECT_LOCK_ENFORCED:
            return []  # kill switch: surface no lock state when the feature is off
        if self.context.get("request") is None:
            return []
        cache = self.context.get("_object_lock_claims")
        if cache is None:
            # In a list response the parent ListSerializer holds the whole page; resolve every
            # object's active claims in ONE query rather than one per row. For single-object (detail)
            # serialization the "page" is just this object.
            parent = self.parent
            if isinstance(parent, drf_serializers.ListSerializer) and parent.instance is not None:
                page = list(parent.instance)
            else:
                page = [obj]
            cache = self.context["_object_lock_claims"] = _batch_active_lock_claims(page)
        return cache.get(obj.pk, [])

    @extend_schema_field(drf_serializers.BooleanField())
    def get_is_locked(self, obj):
        """Return True if *obj* has at least one active lock claim."""
        return bool(self._claims_for(obj))

    @extend_schema_field(drf_serializers.BooleanField())
    def get_locked_for_delete(self, obj):
        """Return True if any active claim on *obj* has ``prevent_delete=True``."""
        return any(c.prevent_delete for c in self._claims_for(obj))

    @extend_schema_field(drf_serializers.BooleanField())
    def get_locked_for_update(self, obj):
        """Return True if any active claim on *obj* has ``prevent_update=True``."""
        return any(c.prevent_update for c in self._claims_for(obj))

    @extend_schema_field(drf_serializers.ListField(child=drf_serializers.CharField(), allow_null=True))
    def get_locked_fields(self, obj):
        """Return the sorted union of frozen field names from active update locks on *obj*.

        Requires ``extras.view_objectlock``; returns None when the requesting user lacks that
        permission, and None when no fields are frozen.
        """
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or not user.has_perm("extras.view_objectlock"):
            return None
        fields = set()
        for claim in self._claims_for(obj):
            if claim.prevent_update and claim.locked_fields:
                fields.update(claim.locked_fields)
        return sorted(fields) if fields else None


class ObjectLockSerializer(BaseModelSerializer):
    """Serializer for ObjectLock.

    Attribution fields (source_context, source_detail, created_by) are read-only and always derived
    server-side. source_key is also read-only on this serializer, but it is caller-supplied via the
    lock action (auto-generated when omitted).
    """

    class Meta:
        model = ObjectLock
        fields = [
            "id",
            "url",
            "display",
            "natural_slug",
            "content_type",
            "object_id",
            "prevent_delete",
            "prevent_update",
            "locked_fields",
            "reason",
            "source_context",
            "source_detail",
            "source_key",
            "created_by",
            "expires",
            "created",
            "last_updated",
        ]
        read_only_fields = ["source_context", "source_detail", "source_key", "created_by"]


class LockInputSerializer(drf_serializers.Serializer):
    """Input serializer for the `lock` action.

    All fields are optional; server-side defaults apply for any omitted field.
    """

    prevent_delete = drf_serializers.BooleanField(required=False, default=True)
    prevent_update = drf_serializers.BooleanField(required=False, default=False)
    reason = drf_serializers.CharField(required=False, default="", allow_blank=True)
    source_key = drf_serializers.CharField(
        required=False, allow_null=True, default=None, max_length=OBJECT_LOCK_SOURCE_KEY_MAX_LENGTH
    )
    expires = drf_serializers.DateTimeField(required=False, allow_null=True, default=None)
    locked_fields = drf_serializers.ListField(
        child=drf_serializers.CharField(), required=False, allow_null=True, default=None
    )

    def validate_expires(self, value):
        """Reject an expiry in the past, which would create a born-expired no-op lock."""
        if value is not None and value <= timezone.now():
            raise drf_serializers.ValidationError("expires must be in the future.")
        return value


class ReleaseInputSerializer(drf_serializers.Serializer):
    """Input serializer for the `release` action."""

    # Required: releasing by no key would match zero claims yet report success (a silent no-op).
    source_key = drf_serializers.CharField(
        required=True,
        max_length=OBJECT_LOCK_SOURCE_KEY_MAX_LENGTH,
        help_text="Source key identifying the specific claim to release.",
    )


class ReleaseResponseSerializer(drf_serializers.Serializer):
    """Response body returned by the `release` action."""

    status = drf_serializers.CharField(read_only=True)
    source_key = drf_serializers.CharField(read_only=True)


class _LockPermissions(TokenPermissions):
    """TokenPermissions subclass requiring only `extras.add_objectlock` for POST.

    The lock action gates on a cross-cutting ObjectLock permission rather than the
    target model's `add_` permission, so we bypass the default model-based mapping.
    """

    perms_map = {
        "GET": [],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["extras.add_objectlock"],
    }


class _ReleasePermissions(TokenPermissions):
    """TokenPermissions subclass requiring only `extras.delete_objectlock` for POST."""

    perms_map = {
        "GET": [],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["extras.delete_objectlock"],
    }


class ObjectLockableModelViewSetMixin:
    """Adds per-object `lock` and `release` detail actions to a model viewset."""

    def restrict_queryset(self, request, *args, **kwargs):
        """Skip the standard add/change/delete queryset restriction for `lock` / `release` actions.

        Those actions gate on `extras.add_objectlock` / `extras.delete_objectlock`
        rather than model-level add/change/delete permissions, so the normal queryset
        restriction in `initial()` is bypassed. The actions instead re-restrict object lookup to
        `view` access (`get_object_or_404(self.queryset.restrict(request.user, "view"), ...)`), so a
        caller must still be able to view the target object.
        """
        if self.action in ("lock", "release"):
            return
        super().restrict_queryset(request, *args, **kwargs)

    @extend_schema(
        methods=["post"],
        request=LockInputSerializer,
        responses={201: ObjectLockSerializer},
    )
    @action(detail=True, methods=["post"], url_path="lock", permission_classes=[_LockPermissions])
    def lock(self, request, pk=None, **kwargs):
        """Create or refresh a lock claim on this object (POST ``lock`` action).

        The request body may include ``prevent_delete``, ``prevent_update``, ``reason``, ``source_key``,
        ``expires``, and ``locked_fields``; attribution is server-derived. Responds 201 with the
        serialized ObjectLock (idempotent per ``source_key``), or 400 on manager-side validation error.
        """
        input_serializer = LockInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        # Require view access to the target object, not just the cross-cutting add_objectlock permission.
        obj = get_object_or_404(self.queryset.restrict(request.user, "view"), pk=pk)
        try:
            lock = ObjectLock.objects.lock(
                obj,
                prevent_delete=data["prevent_delete"],
                prevent_update=data["prevent_update"],
                reason=data["reason"],
                source_key=data["source_key"],
                expires=data["expires"],
                locked_fields=data["locked_fields"],
                requesting_user=request.user,
            )
        except DjangoValidationError as exc:
            # Surface manager-side validation (unknown locked_fields, past expiry) as a 400, not a 500.
            raise drf_serializers.ValidationError(exc.messages)
        serializer = ObjectLockSerializer(lock, context={"request": request})
        # Intentionally 201 for both initial create and idempotent refresh of an existing claim (the claim
        # is upserted per source_key and the response body is identical), so a single OpenAPI status holds.
        return Response(serializer.data, status=drf_status.HTTP_201_CREATED)

    @extend_schema(
        methods=["post"],
        request=ReleaseInputSerializer,
        responses={200: ReleaseResponseSerializer},
    )
    @action(detail=True, methods=["post"], url_path="release", permission_classes=[_ReleasePermissions])
    def release(self, request, pk=None, **kwargs):
        """Release a lock claim on this object (POST ``release`` action).

        The request body must include ``source_key``. Releasing a claim created by another source
        requires ``extras.force_release_objectlock``. Responds 200 with
        ``{"status": "released", "source_key": ...}``.
        """
        input_serializer = ReleaseInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        source_key = input_serializer.validated_data["source_key"]

        # Require view access to the target object, not just the cross-cutting delete_objectlock permission.
        obj = get_object_or_404(self.queryset.restrict(request.user, "view"), pk=pk)
        # Releasing a claim created by another source requires force_release_objectlock, mirroring the UI
        # and the bulk-release Job; delete_objectlock alone only releases your own claims.
        claims = ObjectLock.objects.active().for_object(obj).filter(source_key=source_key)
        if claims.exclude(created_by=request.user).exists() and not request.user.has_perm(
            "extras.force_release_objectlock"
        ):
            raise PermissionDenied("Releasing a lock created by another source requires force_release_objectlock.")
        ObjectLock.objects.release(obj, source_key=source_key)
        return Response({"status": "released", "source_key": source_key}, status=drf_status.HTTP_200_OK)
