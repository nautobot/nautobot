from django import template

register = template.Library()


@register.simple_tag()
def termination_type_icon(termination):
    """Return an MDI icon class string for a cable termination object based on its type."""
    if termination is None:
        return "mdi-help-circle-outline"
    model_name = termination._meta.model_name
    icons = {
        "interface": "mdi-ethernet",
        "frontport": "mdi-arrow-right-bold-box",
        "rearport": "mdi-arrow-left-bold-box",
        "consoleport": "mdi-console",
        "consoleserverport": "mdi-console-network",
        "powerport": "mdi-power-plug",
        "poweroutlet": "mdi-power-socket",
        "powerfeed": "mdi-flash",
        "circuittermination": "mdi-cable-data",
    }
    return icons.get(model_name, "mdi-cable-data")
