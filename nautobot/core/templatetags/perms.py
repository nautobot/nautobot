from django import template

from nautobot.extras.models.approvals import ApprovalWorkflow

register = template.Library()


def _check_permission(user, instance, action):
    return user.has_perm(
        perm=f"{instance._meta.app_label}.{action}_{instance._meta.model_name}",
        obj=instance,
    )


@register.filter()
def can_view(user, instance):
    return _check_permission(user, instance, "view")


@register.filter()
def can_add(user, instance):
    return _check_permission(user, instance, "add")


@register.filter()
def can_change(user, instance):
    return _check_permission(user, instance, "change")


@register.filter()
def can_delete(user, instance):
    return _check_permission(user, instance, "delete")


@register.filter()
def can_cancel(user, instance):
    if isinstance(instance, ApprovalWorkflow):
        return (user.is_superuser or instance.user == user) and instance.is_active
    else:
        raise NotImplementedError
