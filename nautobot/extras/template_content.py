"""Object Lock detail-view banner and "Locks" panel."""

from typing import Optional

from django.apps import apps
from django.conf import settings
from django.urls import reverse
from django.utils.html import format_html

from nautobot.core.ui.object_detail import Panel, SectionChoices
from nautobot.extras.models import ObjectLock
from nautobot.extras.object_lock_ui import (
    LOCK_PROTECTION_BLURB,
    lock_state_for_objects,
    summarize_modes,
    user_can_view_lock_metadata,
)
from nautobot.extras.plugins import (
    Banner,
    BannerClassChoices,
    register_banner_function,
    register_template_extensions,
    TemplateExtension,
)
from nautobot.extras.registry import registry


def object_lock_banner(context) -> Optional[Banner]:
    """Return a Banner naming ALL active lock modes for the object on a detail page, else None.

    Args:
        context: Template context dict (or dict-like) containing an "object" key.

    Returns:
        A ``Banner`` instance when the object has one or more active locks, otherwise ``None``.
        Returns ``None`` for list views (``object`` is ``None``) and non-model contexts.
    """
    obj = context.get("object") if hasattr(context, "get") else None
    # List views pass object=None; non-model contexts have no `_meta`.
    if obj is None or not hasattr(obj, "_meta") or not hasattr(obj, "pk"):
        return None

    states = lock_state_for_objects([obj])
    state = states.get(obj.pk)
    if state is None:
        return None

    content = format_html(
        '<span class="mdi mdi-lock" aria-hidden="true"></span> '
        "<strong>{}</strong> &mdash; {} contributing lock(s). This object is {}.",
        summarize_modes(state),
        state.active_lock_count,
        LOCK_PROTECTION_BLURB,
    )
    return Banner(content=content, banner_class=BannerClassChoices.CLASS_WARNING)


_MODE_LABELS = {
    (True, True): "Delete + update",
    (True, False): "Delete",
    (False, True): "Update",
    (False, False): "(inactive)",
}


def _claim_can_release(claim, user):
    """Per-claim release gate based on ownership of the claim.

    Args:
        claim (ObjectLock): The lock claim being evaluated.
        user: The requesting user.

    Returns:
        tuple[bool, bool]: ``(can_release, is_own)``. Own claims (``created_by`` is the user) require
        ``extras.delete_objectlock``; another source's claim requires ``extras.force_release_objectlock``.
    """
    is_own = claim.created_by_id == getattr(user, "pk", None)
    if is_own:
        return user.has_perm("extras.delete_objectlock"), True
    return user.has_perm("extras.force_release_objectlock"), False


class ObjectLockPanel(Panel):
    """Detail-page panel listing every active lock claim on the object.

    Rendered on every lockable object's detail page via the ``TemplateExtension.object_detail_panels``
    mechanism, with no per-model templates. The panel only appears when the object has at least one
    active lock. Lock metadata (reason, source, attribution, per-claim rows, release buttons) is gated
    behind ``extras.view_objectlock``; viewers without it see only the protection blurb, the legend, the
    mode summary, the active-lock count, and a "details are restricted" notice.
    """

    label = "Locks"
    section = SectionChoices.FULL_WIDTH
    css_class = "warning"
    body_content_template_path = "extras/inc/object_lock_panel.html"

    def should_render(self, context):
        """Render the panel only for a saved object that currently has at least one active lock.

        Returns False when enforcement is disabled (``OBJECT_LOCK_ENFORCED`` off) so the feature stays
        dormant — no query, no panel — matching ``lock_state_for_objects`` and the other surfaces.

        Args:
            context (Context): The detail-page render context, expected to contain ``object``.

        Returns:
            bool: True when the object has one or more active locks, else False (panel renders "").
        """
        if not settings.OBJECT_LOCK_ENFORCED:
            return False
        obj = context.get("object")
        if obj is None or not hasattr(obj, "pk"):
            return False
        return ObjectLock.objects.active().for_object(obj).exists()

    def get_extra_context(self, context):
        """Build the panel context, redacting all lock metadata when the user lacks ``view_objectlock``.

        When the user cannot view metadata, the returned context omits ``claims`` (and any reason /
        source / attribution), so the template's ``{% else %}`` branch renders only the safe summary.

        Args:
            context (Context): The detail-page render context.

        Returns:
            dict: Context for the panel body template, merged onto the base component context.
        """
        obj = context["object"]
        request = context.get("request")
        user = getattr(request, "user", None)
        can_view = user_can_view_lock_metadata(user)

        state = lock_state_for_objects([obj]).get(obj.pk)
        extra = {
            **super().get_extra_context(context),
            "lock_protection_blurb": LOCK_PROTECTION_BLURB,
            "can_view_metadata": can_view,
            "active_lock_count": state.active_lock_count if state else 0,
            "summary": summarize_modes(state) if state else "",
        }
        if not can_view:
            return extra

        claims = list(ObjectLock.objects.active().for_object(obj).select_related("created_by"))
        has_other = False
        decorated = []
        for claim in claims:
            can_release, is_own = _claim_can_release(claim, user)
            if not is_own:
                has_other = True
            claim.mode_label = _MODE_LABELS[(claim.prevent_delete, claim.prevent_update)]
            claim.can_release = can_release
            claim.is_own = is_own
            claim.release_url = reverse("extras:objectlock_delete", kwargs={"pk": claim.pk})
            decorated.append(claim)
        extra["claims"] = decorated
        extra["has_other_source_locks"] = has_other
        return extra


def _lockable_models():
    """Yield every concrete ``BaseModel`` subclass that Object Lock can target.

    Object Lock stores a target's PK in ``ObjectLock.object_id`` (a ``UUIDField``), and every
    ``BaseModel`` subclass uses a UUID primary key, so all of them qualify. This is introspection-only --
    it uses only ``apps.get_models()`` and ``issubclass`` (no database access) -- so it is safe to call
    from ``ready()``.

    Yields:
        type: Each concrete ``BaseModel`` subclass.
    """
    from nautobot.core.models import BaseModel

    for model in apps.get_models():
        if not issubclass(model, BaseModel):
            continue
        yield model


def register_object_lock_ui():
    """Register the Object Lock banner and a detail-panel ``TemplateExtension`` for every lockable model.

    Called from ``ExtrasConfig.ready()``. Registration appends to the global registry, so this guards
    against double-registration on both the banner (membership check) and each per-model extension (via the
    ``_is_object_lock_extension`` marker), making it safe to re-run.
    """
    if object_lock_banner not in registry["plugin_banners"]:
        register_banner_function(object_lock_banner)

    for model in _lockable_models():
        model_key = f"{model._meta.app_label}.{model._meta.model_name}"
        existing = registry["plugin_template_extensions"].get(model_key, [])
        if any(getattr(ext, "_is_object_lock_extension", False) for ext in existing):
            continue

        extension = type(
            f"ObjectLock{model.__name__}TemplateExtension",
            (TemplateExtension,),
            {
                "model": model_key,
                "object_detail_panels": (ObjectLockPanel(weight=750),),
                "_is_object_lock_extension": True,
            },
        )
        register_template_extensions([extension])
