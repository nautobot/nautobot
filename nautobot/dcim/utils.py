from copy import deepcopy
import uuid

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils.html import format_html, format_html_join
from netutils.lib_mapper import NAME_TO_ALL_LIB_MAPPER, NAME_TO_LIB_MAPPER_REVERSE

from nautobot.core.choices import ColorChoices
from nautobot.core.templatetags.helpers import hyperlinked_object
from nautobot.core.utils.config import get_settings_or_config
from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.dcim.constants import DEFAULT_CABLE_BREAKOUT_TYPES


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
            ColorChoices.COLOR_GREEN: "table-success",
            ColorChoices.COLOR_AMBER: "table-warning",
            ColorChoices.COLOR_CYAN: "table-info",
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


def render_software_version_and_image_files(instance, software_version, context):
    display = hyperlinked_object(software_version)
    overridden_software_image_files = instance.software_image_files.all()
    if software_version is not None:
        display += format_html(
            '<ul class="software-image-hierarchy">{}</ul>',
            format_html_join(
                "\n",
                "<li>{}{}</li>",
                [
                    [
                        hyperlinked_object(img, "image_file_name"),
                        " (overridden)" if overridden_software_image_files.exists() else "",
                    ]
                    for img in software_version.software_image_files.restrict(context["request"].user, "view")
                ],
            ),
        )
    if overridden_software_image_files.exists():
        display += format_html(
            "<br><strong>Software Image Files Overridden:</strong>\n<ul>{}</ul>",
            format_html_join(
                "\n", "<li>{}</li>", [[hyperlinked_object(img)] for img in overridden_software_image_files.all()]
            ),
        )
    return display


def populate_default_cable_breakout_types(apps, schema_editor=None):
    """Create default cable breakout type records."""
    CableBreakoutType = apps.get_model("dcim", "CableBreakoutType")
    for name, defaults in DEFAULT_CABLE_BREAKOUT_TYPES.items():
        CableBreakoutType.objects.get_or_create(name=name, defaults=defaults)


def clear_default_cable_breakout_types(apps, schema_editor=None):
    """Delete default cable breakout type records."""
    CableBreakoutType = apps.get_model("dcim", "CableBreakoutType")
    for name in DEFAULT_CABLE_BREAKOUT_TYPES.keys():
        CableBreakoutType.objects.filter(name=name).delete()


def generate_cable_breakout_mapping(a_connectors: int, b_connectors: int, total_lanes: int):
    """Generate a default mapping from the given connector and lane counts."""
    a_positions = total_lanes // a_connectors
    b_positions = total_lanes // b_connectors
    mapping = []
    lane_index = 0
    for a_connector in range(a_connectors):
        for a_position in range(a_positions):
            b_connector = lane_index // b_positions
            b_position = lane_index % b_positions
            mapping.append(
                {
                    # Change 0-indexed iterations to 1-indexed mapping entries!
                    "label": str(lane_index + 1),
                    "a_connector": a_connector + 1,
                    "a_position": a_position + 1,
                    "b_connector": b_connector + 1,
                    "b_position": b_position + 1,
                }
            )
            lane_index += 1
    return mapping


def validate_cable_breakout_mapping(mapping: list, a_connectors=None, b_connectors=None, total_lanes=None):
    """Validate the mapping JSON structure and consistency with connector/position counts.

    If any of `a_connectors`, `b_connectors`, or `total_lanes` is not provided, it will be
    derived from the mapping itself (max `a_connector`/`b_connector` values, and `len(mapping)`
    respectively). When provided, each is enforced against the mapping.

    Missing `label` entries are filled in with the entry index as a string.
    Raises ValidationError if the mapping is invalid.

    Returns:
        tuple: (mapping, a_connectors, b_connectors, total_lanes)
    """

    if not isinstance(mapping, list):
        raise ValidationError({"mapping": "Mapping must be a JSON array."})

    if total_lanes is not None and len(mapping) != total_lanes:
        raise ValidationError({"mapping": f"Expected {total_lanes} lane definitions, but got {len(mapping)}."})
    elif not mapping:
        raise ValidationError({"mapping": "Empty mapping is not permitted."})

    required_keys = {"a_connector", "a_position", "b_connector", "b_position"}
    optional_keys = {"label"}

    # First pass: structural checks (types, keys) so we can safely derive dimensions below.
    for i, entry in enumerate(mapping):
        if not isinstance(entry, dict):
            raise ValidationError({"mapping": f"Entry {i} must be a JSON object."})

        missing_keys = required_keys - set(entry.keys())
        if missing_keys:
            raise ValidationError(
                {"mapping": f"Entry {i} is missing required keys: {', '.join(sorted(missing_keys))}."}
            )

        unknown_keys = set(entry.keys()) - required_keys - optional_keys
        if unknown_keys:
            raise ValidationError({"mapping": f"Entry {i} has unknown keys: {', '.join(sorted(unknown_keys))}"})

        for key in required_keys:
            if not isinstance(entry[key], int) or entry[key] < 1:
                raise ValidationError({"mapping": f"Entry {i} key '{key}' must be a positive integer."})

    if a_connectors is None:
        a_connectors = max(e["a_connector"] for e in mapping)
    if b_connectors is None:
        b_connectors = max(e["b_connector"] for e in mapping)
    if total_lanes is None:
        total_lanes = len(mapping)

    a_positions = total_lanes // a_connectors
    b_positions = total_lanes // b_connectors

    # Second pass: range and uniqueness checks, and fill in default labels.
    seen_a_pairs = set()
    seen_b_pairs = set()
    seen_labels = set()

    for i, entry in enumerate(mapping):
        a_connector = entry["a_connector"]
        a_position = entry["a_position"]
        b_connector = entry["b_connector"]
        b_position = entry["b_position"]

        # Range checks - note that we already checked for typing and for values less than 1 in the first pass above
        if a_connector > a_connectors:
            raise ValidationError(
                {"mapping": f"Entry {i}: a_connector {a_connector} out of range [1, {a_connectors}]."}
            )
        if a_position > a_positions:
            raise ValidationError({"mapping": f"Entry {i}: a_position {a_position} out of range [1, {a_positions}]."})
        if b_connector > b_connectors:
            raise ValidationError(
                {"mapping": f"Entry {i}: b_connector {b_connector} out of range [1, {b_connectors}]."}
            )
        if b_position > b_positions:
            raise ValidationError({"mapping": f"Entry {i}: b_position {b_position} out of range [1, {b_positions}]."})

        # Uniqueness checks
        a_pair = (a_connector, a_position)
        if a_pair in seen_a_pairs:
            raise ValidationError(
                {"mapping": f"Entry {i}: Duplicate A-side (connector, position) pair: ({a_connector}, {a_position})."}
            )
        seen_a_pairs.add(a_pair)

        b_pair = (b_connector, b_position)
        if b_pair in seen_b_pairs:
            raise ValidationError(
                {"mapping": f"Entry {i}: Duplicate B-side (connector, position) pair: ({b_connector}, {b_position})."}
            )
        seen_b_pairs.add(b_pair)

        if "label" not in entry:
            entry["label"] = str(i)
        label = entry["label"]
        if not isinstance(label, str):
            raise ValidationError({"mapping": f"Entry {i}: Label {label} must be a string"})
        if label in seen_labels:
            raise ValidationError({"mapping": f"Entry {i}: Duplicate label: {label}"})
        seen_labels.add(label)

    return mapping, a_connectors, b_connectors, total_lanes
