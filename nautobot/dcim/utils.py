from copy import deepcopy
import uuid

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from netutils.lib_mapper import NAME_TO_ALL_LIB_MAPPER, NAME_TO_LIB_MAPPER_REVERSE

from nautobot.core.choices import ColorChoices
from nautobot.core.utils.config import get_settings_or_config
from nautobot.dcim.choices import InterfaceModeChoices


def compile_path_node(ct_id, object_id):
    return f"{ct_id}:{object_id}"


def decompile_path_node(representation):
    ct_id, object_id = representation.split(":")
    # The value is stored as a string, but the lookup later uses UUID objects as keys so we convert it now.
    # Note that the content type ID is still an integer because we have no control over that model.
    return int(ct_id), uuid.UUID(object_id)


def object_to_path_node(obj):
    """
    Return a representation of an object suitable for inclusion in a CablePath path. Node representation is in the
    form <ContentType ID>:<Object ID>.
    """
    ct = ContentType.objects.get_for_model(obj)
    return compile_path_node(ct.pk, obj.pk)


def path_node_to_object(representation):
    """
    Given the string representation of a path node, return the corresponding instance.
    """
    ct_id, object_id = decompile_path_node(representation)
    ct = ContentType.objects.get_for_id(ct_id)
    return ct.model_class().objects.get(pk=object_id)


def cable_status_color_css(record):
    """
    Given a record such as an Interface, return the CSS needed to apply appropriate coloring to it.
    """
    if not record.cable:
        return ""
    else:
        CABLE_STATUS_TO_CSS_CLASS = {
            ColorChoices.COLOR_GREEN: "success",
            ColorChoices.COLOR_AMBER: "warning",
            ColorChoices.COLOR_CYAN: "info",
        }
        status_color = record.cable.get_status_color().strip("#")
        return CABLE_STATUS_TO_CSS_CLASS.get(status_color, "")


def get_network_driver_mapping_tool_names():
    """
    Return a list of all available network driver tool names derived from the netutils library and the optional NETWORK_DRIVERS setting.

    Tool names are "ansible", "hier_config", "napalm", "netmiko", etc...
    """
    network_driver_names = set(NAME_TO_LIB_MAPPER_REVERSE.keys())
    network_driver_names.update(get_settings_or_config("NETWORK_DRIVERS", fallback={}).keys())
    return sorted(network_driver_names)


def get_all_network_driver_mappings():
    """
    Return a dict of all available network driver mappings derived from the netutils library and the optional NETWORK_DRIVERS setting.

    Example output:
        {
            "cisco_ios": {
                "ansible": "cisco.ios.ios",
                "napalm": "ios",
            },
            "cisco_nxos": {
                "ansible": "cisco.nxos.nxos",
                "napalm": "nxos",
            },
            etc...
        }
    """
    network_driver_mappings = deepcopy(NAME_TO_ALL_LIB_MAPPER)

    # add mappings from optional NETWORK_DRIVERS setting
    network_drivers_config = get_settings_or_config("NETWORK_DRIVERS", fallback={})
    for tool_name, mappings in network_drivers_config.items():
        for normalized_name, mapped_name in mappings.items():
            network_driver_mappings.setdefault(normalized_name, {})
            network_driver_mappings[normalized_name][tool_name] = mapped_name

    return network_driver_mappings


def validate_interface_tagged_vlans(instance, model, pk_set):
    """
    Validate that the VLANs being added to the 'tagged_vlans' field of an Interface instance are all from the same location
    as the parent device or are global and that the mode of the Interface is set to `InterfaceModeChoices.MODE_TAGGED`.

    Args:
        instance (Interface): The instance of the Interface model that the VLANs are being added to.
        model (Model): The model of the related VLAN objects.
        pk_set (set): The primary keys of the VLAN objects being added to the 'tagged_vlans' field.
    """

    if instance.mode != InterfaceModeChoices.MODE_TAGGED:
        raise ValidationError(
            {"tagged_vlans": f"Mode must be set to {InterfaceModeChoices.MODE_TAGGED} when specifying tagged_vlans"}
        )

    # Filter the model objects based on the primary keys passed in kwargs and exclude the ones that have
    # a location that is not the parent's location, or parent's location's ancestors, or None
    location = getattr(instance.parent, "location", None)
    if location:
        location_ids = location.ancestors(include_self=True).values_list("id", flat=True)
    else:
        location_ids = []
    tagged_vlans = (
        model.objects.filter(pk__in=pk_set).exclude(locations__isnull=True).exclude(locations__in=location_ids)
    )

    if tagged_vlans.count():
        raise ValidationError(
            {
                "tagged_vlans": (
                    f"Tagged VLAN with names {list(tagged_vlans.values_list('name', flat=True))} must all belong to the "
                    "same location as the interface's parent device, "
                    "one of the parent locations of the interface's parent device's location, or it must be global."
                )
            }
        )


def convert_watts_to_va(watts, power_factor):
    """
    Convert watts to VA using power factor.
    """
    if not watts:
        return 0
    return int(watts / power_factor)
