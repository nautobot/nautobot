"""ObjectLock model: one lock claim by one source on one target object."""

from contextlib import contextmanager
import logging
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import models, transaction
from django.utils import timezone

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseManager, BaseModel
from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.extras.choices import ObjectChangeEventContextChoices
from nautobot.extras.models.change_logging import ChangeLoggedModel
from nautobot.extras.utils import extras_features

logger = logging.getLogger(__name__)

# A source key is a standard char-field identifier; track the global cap rather than duplicate 255.
OBJECT_LOCK_SOURCE_KEY_MAX_LENGTH = CHARFIELD_MAX_LENGTH


def validate_locked_field_names(model, field_names):
    """Validate that every name in `field_names` is a real field or custom-field key of `model`.

    Args:
        model (type): The Django model class the lock targets.
        field_names (Optional[Iterable[str]]): Candidate field names. None or empty means "all fields".

    Raises:
        ValidationError: If any name is neither a concrete/relational field nor a custom-field key.

    Returns:
        list: The validated, de-duplicated list of names (empty list for None/empty input).
    """
    if not field_names:
        return []

    # Only forward, enforceable fields: concrete fields (caught on pre_save) and forward M2M (caught
    # on m2m_changed). Reverse relations that get_fields() also returns are NOT enforceable, so a lock
    # naming one would silently protect nothing — exclude them.
    valid_names = {f.name for f in model._meta.concrete_fields} | {f.name for f in model._meta.many_to_many}

    # Custom-field keys are valid targets when the model supports custom fields.
    if hasattr(model, "_custom_field_data"):
        from nautobot.extras.models import CustomField  # local import to avoid circular import

        valid_names |= set(CustomField.objects.get_for_model(model).values_list("key", flat=True))

    invalid = [name for name in field_names if name not in valid_names]
    if invalid:
        raise ValidationError(
            {"locked_fields": f"Unknown field name(s) for {model._meta.label}: {', '.join(sorted(invalid))}"}
        )

    # De-duplicate while preserving order.
    seen = set()
    result = []
    for name in field_names:
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


class ObjectLockQuerySet(RestrictedQuerySet):
    """QuerySet for ObjectLock."""

    def active(self):
        """Return locks that have not expired (expires is null or in the future)."""
        return self.filter(models.Q(expires__isnull=True) | models.Q(expires__gt=timezone.now()))

    def for_object(self, obj):
        """Return locks targeting a specific object instance."""
        return self.filter(content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk)


def _derive_attribution(requesting_user):
    """Return (source_context, source_detail, created_by) from the active change context.

    Server-derived and never spoofable by caller input.

    Args:
        requesting_user: The user requesting the lock, used as fallback when no change context is active.

    Returns:
        A 3-tuple of (source_context, source_detail, created_by).
    """
    from nautobot.extras.signals import change_context_state  # lazy import — avoids circular dependency

    change_context = change_context_state.get()
    if change_context is not None:
        source_context = change_context.context
        # Bound to the column width: change_context.context_detail is capped at
        # CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL (400) but source_detail is a CHARFIELD_MAX_LENGTH (255)
        # column, so a 256-400 char detail would raise DataError (PostgreSQL) / truncate (MySQL).
        source_detail = (change_context.context_detail or "")[:CHARFIELD_MAX_LENGTH]
        created_by = change_context.get_user() or requesting_user
    else:
        source_context = ObjectChangeEventContextChoices.CONTEXT_ORM
        source_detail = ""
        created_by = requesting_user
    return source_context, source_detail, created_by


class ObjectLockManager(BaseManager.from_queryset(ObjectLockQuerySet)):
    """Manager exposing the programmatic lock/release API.

    Retains all queryset helpers (`active()`, `for_object()`) and adds
    higher-level `lock` / `release` / `lock_many` / `release_many` methods.
    """

    def _validate_target(self, obj):
        """Raise TypeError if *obj* is not a UUID-PK BaseModel instance.

        Args:
            obj: The candidate lock target to validate.

        Raises:
            TypeError: If *obj* is not a BaseModel subclass, or its PK is not a UUID.
        """
        if not isinstance(obj, BaseModel):
            raise TypeError(f"Object Lock targets must be BaseModel subclasses, got {type(obj)!r}")
        if not isinstance(obj.pk, uuid.UUID):
            raise TypeError(f"Object Lock targets must have a UUID primary key, got {obj.pk!r}")

    def _resolve_expires(self, expires, _expires_explicit):
        """Resolve the expiry datetime from caller arguments and the default-TTL setting.

        Args:
            expires: Caller-supplied expiry datetime or None.
            _expires_explicit: When True, return *expires* as-is (including None for indefinite).

        Returns:
            A datetime for the expiry, or None for indefinite.
        """
        if _expires_explicit or expires is not None:
            return expires
        ttl = getattr(settings, "OBJECT_LOCK_DEFAULT_TTL", None)
        if ttl is None:
            return None
        return timezone.now() + timezone.timedelta(seconds=ttl)

    def lock(
        self,
        obj,
        *,
        prevent_delete=True,
        prevent_update=False,
        locked_fields=None,
        reason="",
        source_key=None,
        expires=None,
        requesting_user,
        _expires_explicit=False,
        _internal_source_key=False,
    ):
        """Create or update a single lock claim on *obj*. Idempotent per *source_key*.

        Attribution (`source_context`, `source_detail`, `created_by`) is server-derived
        from the active change context and is never accepted as caller input.

        Args:
            obj: The target object to lock; must be a UUID-PK BaseModel instance.
            prevent_delete: When True (default), block deletion of the target.
            prevent_update: When True, block updates to the target.
            locked_fields: Optional list of field names to freeze; an empty/None list locks the whole object.
            reason: Human-readable explanation for the lock.
            source_key: Unique claim identifier for idempotency. Auto-generated when omitted.
            expires: Explicit expiry datetime. Defaults to now + `OBJECT_LOCK_DEFAULT_TTL`, or an
                indefinite (no-expiry) lock when that setting is unset.
            requesting_user: User on whose behalf the lock is being placed.
            _expires_explicit: Set to True to pass *expires=None* for an indefinite lock.
            _internal_source_key: Private. Set to True only by `locked()` for the `auto:` key it generates
                itself, so the reserved-prefix guard admits it while still rejecting caller `auto:` input.

        Returns:
            The created or updated ObjectLock instance.

        Raises:
            TypeError: If *obj* is not a UUID-PK BaseModel instance.
            ValidationError: If *expires* is in the past, *locked_fields* names an unknown field, or
                *source_key* is already held by a different source and the caller lacks
                force_release_objectlock.
        """
        self._validate_target(obj)
        if not obj.present_in_database:
            # Object Lock protects *existing* objects; a BaseModel gets its UUID at instantiation, so a
            # lock on an unsaved instance would write an orphan claim that protects nothing.
            raise ValidationError("Cannot place an Object Lock on an object that has not been saved.")
        if not prevent_delete and not prevent_update:
            raise ValidationError(
                "An Object Lock must prevent at least one of delete or update (a no-op lock protects nothing)."
            )
        if locked_fields:
            # Reject locked_fields names that are not real fields / custom-field keys,
            # independent of the model clean() (callers may use bare save()).
            locked_fields = validate_locked_field_names(type(obj), locked_fields)
        resolved_expires = self._resolve_expires(expires, _expires_explicit)
        if resolved_expires is not None and resolved_expires <= timezone.now():
            # Reject a past expiry on every surface (the REST serializer also checks): a born-expired
            # lock is active()==False from creation, protecting nothing while reporting success.
            raise ValidationError("Object Lock expires must be in the future.")
        if source_key is not None and not _internal_source_key and source_key.startswith("auto:"):
            # 'auto:' is reserved for server-generated keys; a caller-supplied 'auto:' key could
            # masquerade as a system/auto lock in 409 messages and the Locks panel. All caller-facing
            # paths (REST, bulk job/form, programmatic) funnel through here; only locked() sets
            # _internal_source_key=True, for the auto: key it generates itself.
            raise ValidationError("Object Lock source_key may not start with the reserved 'auto:' prefix.")
        if source_key is None:
            source_key = f"auto:{uuid.uuid4()}"[:OBJECT_LOCK_SOURCE_KEY_MAX_LENGTH]
        source_context, source_detail, created_by = _derive_attribution(requesting_user)
        content_type = ContentType.objects.get_for_model(obj)
        # Block silent cross-owner takeover: refreshing a claim created by a *different* source — to
        # weaken its mode/scope/expiry — requires force_release_objectlock. Attribution lives only in
        # create_defaults, so it is never rewritten on a refresh and an owner can never be silently
        # replaced (even by a force-release holder).
        existing = self.filter(content_type=content_type, object_id=obj.pk, source_key=source_key).first()
        if (
            existing is not None
            and existing.created_by_id is not None
            and existing.created_by_id != getattr(created_by, "pk", None)
            and not (requesting_user is not None and requesting_user.has_perm("extras.force_release_objectlock"))
        ):
            raise ValidationError(
                f"source_key '{source_key}' is already held by a different source; "
                "reuse requires the force_release_objectlock permission."
            )
        # Mutable fields are refreshed on every call; attribution is set only at creation.
        mutable = {
            "prevent_delete": prevent_delete,
            "prevent_update": prevent_update,
            "locked_fields": locked_fields,
            "reason": reason,
            "expires": resolved_expires,
        }
        lock, _ = self.update_or_create(
            content_type=content_type,
            object_id=obj.pk,
            source_key=source_key,
            defaults=mutable,
            create_defaults={
                **mutable,
                "source_context": source_context,
                "source_detail": source_detail,
                "created_by": created_by,
            },
        )
        logger.debug("Lock placed on %s with source_key=%s", obj, source_key)
        return lock

    def release(self, obj, *, source_key):
        """Delete the claim for *source_key* on *obj* (if present).

        Args:
            obj: The target object whose claim should be released.
            source_key: The claim identifier to remove.

        Returns:
            A (count, detail_dict) tuple from QuerySet.delete().

        Raises:
            TypeError: If *obj* is not a UUID-PK BaseModel instance.
        """
        self._validate_target(obj)
        logger.debug("Releasing lock on %s with source_key=%s", obj, source_key)
        return self.for_object(obj).filter(source_key=source_key).delete()

    def lock_many(self, objs, *, requesting_user, **kwargs):
        """Lock multiple objects with the same parameters.

        Args:
            objs: Iterable of UUID-PK BaseModel instances to lock.
            requesting_user: User on whose behalf the locks are placed.
            **kwargs: Forwarded to :meth:`lock`.

        Returns:
            List of created/updated ObjectLock instances.
        """
        with transaction.atomic():
            return [self.lock(obj, requesting_user=requesting_user, **kwargs) for obj in objs]

    def release_many(self, objs, *, source_key):
        """Release the *source_key* claim on multiple objects.

        Args:
            objs: Iterable of UUID-PK BaseModel instances to unlock.
            source_key: The claim identifier to remove from each object.
        """
        with transaction.atomic():
            for obj in objs:
                self.release(obj, source_key=source_key)

    @contextmanager
    def locked(self, obj_or_iterable, *, source_key=None, requesting_user, **kwargs):
        """Lock one object or an iterable for the duration of a block; release on exit (TTL backstop).

        Acquires the lock(s) on entry and releases them on exit, even if the block raises.
        When *source_key* is omitted an auto-generated key is used so the context manager
        can release exactly the claim(s) it created.

        Args:
            obj_or_iterable: A single UUID-PK BaseModel instance, or an iterable of them.
            source_key: Claim identifier forwarded to `lock_many`. Auto-generated when omitted.
            requesting_user: User on whose behalf the locks are placed.
            **kwargs: Additional keyword arguments forwarded to `lock_many`.

        Yields:
            None — the caller's `with` block body runs here.
        """
        if isinstance(obj_or_iterable, BaseModel):
            objs = [obj_or_iterable]
        else:
            objs = list(obj_or_iterable)
        internal_source_key = source_key is None
        if internal_source_key:
            source_key = f"auto:{uuid.uuid4()}"[:OBJECT_LOCK_SOURCE_KEY_MAX_LENGTH]
        self.lock_many(
            objs,
            source_key=source_key,
            requesting_user=requesting_user,
            _internal_source_key=internal_source_key,
            **kwargs,
        )
        try:
            yield
        finally:
            self.release_many(objs, source_key=source_key)


@extras_features(
    "graphql",
)
class ObjectLock(ChangeLoggedModel, BaseModel):
    """A single lock claim placed by one source on one target object.

    An object is delete-locked if it has >=1 active claim with `prevent_delete`, and
    update-locked if it has >=1 active claim with `prevent_update`. Releasing one claim
    leaves remaining claims in force (reference counting).
    """

    content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        related_name="object_locks",
    )
    object_id = models.UUIDField(db_index=True)
    locked_object = GenericForeignKey(ct_field="content_type", fk_field="object_id")

    prevent_delete = models.BooleanField(default=True)
    prevent_update = models.BooleanField(default=False)
    # Field-level scope: names of fields frozen by this claim; empty/None freezes the whole object.
    locked_fields = models.JSONField(null=True, blank=True)

    reason = models.TextField(blank=True)

    # Attribution (source_context / source_detail / created_by): server-derived and read-only (never caller input).
    source_context = models.CharField(
        max_length=50, choices=ObjectChangeEventContextChoices, default=ObjectChangeEventContextChoices.CONTEXT_ORM
    )
    source_detail = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    # Caller-supplied claim identifier (auto-generated when omitted); read-only only on the output serializer.
    source_key = models.CharField(max_length=OBJECT_LOCK_SOURCE_KEY_MAX_LENGTH)
    created_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="object_locks",
        blank=True,
        null=True,
    )

    expires = models.DateTimeField(null=True, blank=True)

    objects = ObjectLockManager()

    documentation_static_path = "docs/user-guide/platform-functionality/object-lock.html"
    natural_key_field_names = ["pk"]
    is_metadata_associable_model = False

    class Meta:
        ordering = ["content_type", "object_id", "source_key"]
        verbose_name = "Object Lock"
        verbose_name_plural = "Object Locks"
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id", "source_key"],
                name="extras_objectlock_unique_source",
            ),
        ]
        permissions = [
            ("bypass_objectlock", "Can bypass an Object Lock to modify a locked object"),
            ("force_release_objectlock", "Can release an Object Lock created by a different source"),
        ]

    def __str__(self):
        """Return a human-readable representation including lock mode and locked object."""
        modes = []
        if self.prevent_delete:
            modes.append("delete")
        if self.prevent_update:
            modes.append("update")
        return f"Lock ({'/'.join(modes) or 'none'}) on {self.locked_object} by {self.source_key}"

    def clean(self):
        """Validate locked_fields names against the target model's fields.

        Raises:
            ValidationError: If any entry in `locked_fields` is not a known field or custom-field
                key of the target model.
        """
        super().clean()
        if not self.prevent_delete and not self.prevent_update:
            raise ValidationError(
                "An Object Lock must prevent at least one of delete or update (a no-op lock protects nothing)."
            )
        model = self.content_type.model_class() if self.content_type_id else None
        if model is not None and self.locked_fields:
            self.locked_fields = validate_locked_field_names(model, self.locked_fields)

    def frozen_field_labels(self):
        """Return display labels for this claim's frozen fields (for the detail Locks panel).

        Returns:
            list[str]: `["All fields"]` for a whole-object claim; otherwise each concrete field's
            title-cased `verbose_name`, the `CustomField` label for a custom-field key, or the raw
            stored name as a fallback when it no longer resolves (field renamed/removed — drift).
        """
        if not self.locked_fields:
            return ["All fields"]
        model = self.content_type.model_class() if self.content_type_id else None
        if model is None:
            return list(self.locked_fields)
        from nautobot.extras.models import CustomField

        cf_labels = dict(CustomField.objects.get_for_model(model).values_list("key", "label"))
        labels = []
        for name in self.locked_fields:
            try:
                field = model._meta.get_field(name)
            except FieldDoesNotExist:
                labels.append(cf_labels.get(name, name))
                continue
            labels.append(str(field.verbose_name).title() if hasattr(field, "verbose_name") else name)
        return labels


class ObjectLockBypassAudit(BaseModel):
    """Durable audit record written whenever an Object Lock bypass allows an otherwise-blocked write.

    One row per `enforce_object_lock` call that was overridden by an active bypass. Provides the
    immutable trail of who bypassed which lock, on which object, under which
    change transaction, and which source-key claims were suspended.
    """

    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="object_lock_bypass_audits",
        null=True,
        blank=True,
    )
    time = models.DateTimeField(auto_now_add=True, db_index=True)
    content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        related_name="object_lock_bypass_audits",
    )
    object_id = models.UUIDField(db_index=True)
    change_id = models.UUIDField(null=True, blank=True)
    suspended_source_keys = models.JSONField(default=list)
    suspended_fields = models.JSONField(default=list)
    suspended_other_source = models.BooleanField(default=False)

    # Write-only, admin-only immutable audit table — not a Metadata association target (mirrors ObjectLock).
    natural_key_field_names = ["pk"]
    is_metadata_associable_model = False

    class Meta:
        ordering = ["-time"]
        verbose_name = "Object Lock bypass audit"
        verbose_name_plural = "Object Lock bypass audits"

    def __str__(self):
        """Return a human-readable summary of this bypass audit record."""
        username = getattr(self.user, "username", self.user_id)
        return f"Bypass by {username} on {self.content_type_id}/{self.object_id} at {self.time}"


class ObjectLockGeneration(models.Model):
    """Single-row table holding a monotonic generation token, bumped in the same transaction as any
    ObjectLock create/update/delete. Used so workers can detect gate-cache staleness cheaply and
    survive a Redis flush.

    Deliberately a plain ``models.Model`` (integer ``pk=1`` singleton), not a UUID ``BaseModel``: it is
    an internal counter with no API/UI surface, and its seed/bump logic keys on the fixed ``pk=1`` row.
    """

    token = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = "Object Lock generation token"

    def __str__(self):
        """Return the token value as a string."""
        return str(self.token)

    @classmethod
    def bump(cls):
        """Increment the singleton generation token.

        The `F()` update is atomic per-row, so the counter is monotonic and never loses increments.
        Returns nothing: cross-request correctness comes from the fail-closed, token-keyed gate cache,
        not from a read-back of this counter, so the extra SELECT would be wasted.
        """
        from django.db.models import F

        cls.objects.get_or_create(pk=1)
        cls.objects.filter(pk=1).update(token=F("token") + 1)

    @classmethod
    def current(cls):
        """Return the current token (0 if the row does not yet exist)."""
        value = cls.objects.filter(pk=1).values_list("token", flat=True).first()
        return value or 0
