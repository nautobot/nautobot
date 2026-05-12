"""
Centralized factory for cable termination picker fields.

CableTerminationFieldSet encapsulates the complexity of selecting a cable termination
object of any type. Given a termination type string or an existing termination object,
it produces form fields with correct querysets, query_params, and initial values.
"""

from django import forms as django_forms

from nautobot.circuits.models import Circuit, CircuitTermination
from nautobot.core.forms import DynamicModelChoiceField, StaticSelect2
from nautobot.dcim.models import (
    ConsolePort,
    ConsoleServerPort,
    Device,
    FrontPort,
    Interface,
    PowerFeed,
    PowerOutlet,
    PowerPanel,
    PowerPort,
    RearPort,
)


# Maps termination model name → configuration for building form fields
def _device_term_config(term_model, term_label, display, extra_query_params=None):
    """Build a config entry for a Device-parented termination type."""
    query_params = {"device": None}
    if extra_query_params:
        query_params.update(extra_query_params)
    return {
        "parent_model": Device,
        "parent_label": "Device",
        "parent_field_name": "device",
        "term_model": term_model,
        "term_label": term_label,
        "term_query_params": query_params,
        "display": display,
    }


# Maps termination model name -> configuration for building form fields
TERMINATION_TYPE_CONFIGS = {
    # Device-parented termination types
    "interface": _device_term_config(Interface, "Interface", "Interface", {"kind": "physical"}),
    "frontport": _device_term_config(FrontPort, "Front Port", "Front Port"),
    "rearport": _device_term_config(RearPort, "Rear Port", "Rear Port"),
    "consoleport": _device_term_config(ConsolePort, "Console Port", "Console Port"),
    "consoleserverport": _device_term_config(ConsoleServerPort, "Console Server Port", "Console Server Port"),
    "powerport": _device_term_config(PowerPort, "Power Port", "Power Port"),
    "poweroutlet": _device_term_config(PowerOutlet, "Power Outlet", "Power Outlet"),
    # Non-device termination types
    "circuittermination": {
        "parent_model": Circuit,
        "parent_label": "Circuit",
        "parent_field_name": "circuit",
        "term_model": CircuitTermination,
        "term_label": "Termination",
        "term_query_params": {"circuit": None},
        "display": "Circuit Termination",
    },
    "powerfeed": {
        "parent_model": PowerPanel,
        "parent_label": "Power Panel",
        "parent_field_name": "power_panel",
        "term_model": PowerFeed,
        "term_label": "Power Feed",
        "term_query_params": {"power_panel": None},
        "display": "Power Feed",
    },
}

# Choices for the type selector dropdown
TERMINATION_TYPE_CHOICES = [("", "---------")] + [
    (key, config["display"]) for key, config in TERMINATION_TYPE_CONFIGS.items()
]


def detect_termination_type(term):
    """
    Detect the termination type string from an existing termination object.

    Returns "interface" when `term` is None (the default starting type for a blank form).
    Raises `ValueError` if `term._meta.model_name` is not a registered termination type, since
    silently substituting "interface" hides a real bug (either the caller passed something that
    isn't a CableTermination subclass, or a new termination type was added without registering
    it in TERMINATION_TYPE_CONFIGS).
    """
    if term is None:
        return "interface"  # default
    model_name = term._meta.model_name
    if model_name not in TERMINATION_TYPE_CONFIGS:
        raise ValueError(
            f"{type(term).__name__} is not a registered cable termination type "
            f"(model_name={model_name!r}, expected one of {sorted(TERMINATION_TYPE_CONFIGS)})"
        )
    return model_name


def get_parent_from_term(term):
    """Extract the parent object (Device, Circuit, PowerPanel) from a termination object."""
    if term is None:
        return None
    if hasattr(term, "device") and term.device:
        return term.device
    if hasattr(term, "module") and term.module and hasattr(term.module, "device") and term.module.device:
        return term.module.device
    if hasattr(term, "circuit"):
        return term.circuit
    if hasattr(term, "power_panel"):
        return term.power_panel
    return None


class CableTerminationFieldSet:
    """
    Factory for producing form fields for a cable termination picker.

    Usage:
        fieldset = CableTerminationFieldSet()
        fields, initial, meta = fieldset.get_fields("lane_1_a", existing_term=some_interface)
        form.fields.update(fields)
        form.initial.update(initial)
    """

    def get_fields(self, prefix, term_type=None, existing_term=None):
        """
        Produce form fields for selecting a cable termination.

        Args:
            prefix: Field name prefix (e.g., "a_conn_1")
            term_type: Termination type string (e.g., "interface"). Auto-detected if not provided.
            existing_term: Existing termination object for pre-population.

        Returns:
            dict with keys:
                "fields": dict of field_name → DynamicModelChoiceField
                "initial": dict of field_name → initial value (for form.initial)
                "meta": dict with type info for template rendering
        """
        if term_type is None:
            term_type = detect_termination_type(existing_term)
        elif term_type not in TERMINATION_TYPE_CONFIGS:
            raise ValueError(
                f"{term_type!r} is not a registered cable termination type "
                f"(expected one of {sorted(TERMINATION_TYPE_CONFIGS)})"
            )

        config = TERMINATION_TYPE_CONFIGS[term_type]
        parent = get_parent_from_term(existing_term) if existing_term else None

        fields = {}
        initial = {}

        # Type selector field. The form/view layer is expected to attach any HTMX-related widget
        # attrs after the fact — this fieldset is independent of any specific UI flow.
        type_field_name = f"{prefix}_type"
        fields[type_field_name] = django_forms.ChoiceField(
            choices=TERMINATION_TYPE_CHOICES,
            required=False,
            initial=term_type,
            label="Type",
            widget=StaticSelect2(),
        )
        initial[type_field_name] = term_type

        # Parent field (Device, Circuit, or PowerPanel)
        parent_field_name = f"{prefix}_parent"
        fields[parent_field_name] = DynamicModelChoiceField(
            queryset=config["parent_model"].objects.all(),
            label=config["parent_label"],
            required=False,
            initial=parent if parent else None,
            embedded_create=False,  # TODO: disabled for now for consistency with fields[term_field_name] below
            embedded_search=True,
        )
        if parent:
            initial[parent_field_name] = parent.pk

        # Termination field
        term_field_name = f"{prefix}_termination"
        # Build query_params with the parent field reference
        query_params = {}
        for key, value in config["term_query_params"].items():
            if value is None:
                # Replace None with a reference to the parent field
                query_params[key] = f"${parent_field_name}"
            else:
                query_params[key] = value

        fields[term_field_name] = DynamicModelChoiceField(
            queryset=config["term_model"].objects.all(),
            label=config["term_label"],
            required=False,
            disabled_indicator="cable",
            initial=existing_term if existing_term else None,
            query_params=query_params,
            embedded_create=False,  # TODO: disabled for now as ComponentCreateView doesn't work properly as embedded
            embedded_search=True,
        )
        if existing_term:
            initial[term_field_name] = existing_term.pk

        meta = {
            "type_field": type_field_name,
            "parent_field": parent_field_name,
            "term_field": term_field_name,
            "term_type": term_type,
            "config": config,
        }

        return {"fields": fields, "initial": initial, "meta": meta}
