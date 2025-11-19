from django import template
from django.utils.html import format_html
from django_jinja import library

from nautobot.extras.choices import ApprovalWorkflowStateChoices

register = template.Library()


@library.filter()
@register.filter()
def render_approval_workflow_state(value):
    """
    Render an approval state value as a colored label.
    """
    if value:
        css_class = ApprovalWorkflowStateChoices.CSS_CLASSES.get(value)
        return format_html('<span class="badge bg-{}">{}</span>', css_class, value)
    return ""
