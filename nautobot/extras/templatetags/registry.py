from django import template

from nautobot.extras.registry import registry

register = template.Library()


class RegistryNode(template.Node):
    """Companion to the do_registry() function that sets `registry` as a context variable for the template."""

    def __init__(self):
        pass

    def render(self, context):
        context["registry"] = registry
        return ""


@register.tag(name="registry")
def do_registry(parser, token):
    """Provide access to the Nautobot data registry as context variable `registry` within this block."""
    return RegistryNode()
