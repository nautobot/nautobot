"""Public DCIM extension points for Nautobot apps."""

from nautobot.dcim.component_creation import is_auto_component_creation_suppressed, SkipAutoComponentCreation

__all__ = (
    "SkipAutoComponentCreation",
    "is_auto_component_creation_suppressed",
)
