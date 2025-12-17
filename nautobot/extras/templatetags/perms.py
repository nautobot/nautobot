from django import template

from nautobot.extras.models.approvals import ApprovalWorkflow

register = template.Library()


@register.filter()
def can_cancel(user, instance):
    if isinstance(instance, ApprovalWorkflow):
        return (user.is_superuser or instance.user == user) and instance.is_active
    else:
        raise NotImplementedError
