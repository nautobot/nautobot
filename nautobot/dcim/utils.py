from copy import deepcopy
from dataclasses import dataclass
from string import Formatter
from typing import Optional
import uuid

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.html import format_html, format_html_join
from netutils.lib_mapper import NAME_TO_ALL_LIB_MAPPER, NAME_TO_LIB_MAPPER_REVERSE

from nautobot.core.choices import ColorChoices
from nautobot.core.templatetags.helpers import bettertitle, hyperlinked_object
from nautobot.core.utils.config import get_settings_or_config
from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.dcim.constants import (
    COMPATIBLE_TERMINATION_TYPES,
    DEFAULT_CABLE_TYPES,
    NONCONNECTABLE_IFACE_TYPES,
)

BREAKOUT_SUBINTERFACE_NAME_TOKENS = ("parent", "position", "position_index")


@dataclass(frozen=True)
class _BreakoutSubinterfaceCreationPlan:
    """A virtual child interface that should be created for a breakout lane."""

    parent_interface: object
    name: str
    breakout_position: int


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
        # A breakout child (sub)interface has no cable of its own; color it after its parent trunk's
        # cable when its lane is connected. `parent_interface` / `get_breakout_lane` are Interface-only,
        # so guard for other cable-terminable types (console/power ports, etc.).
        lane = record.get_breakout_lane() if getattr(record, "parent_interface_id", None) else None
        if lane and lane.far_termination:
            return cable_status_color_css(record.parent_interface)
        return ""

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


def populate_default_cable_types(apps, schema_editor=None):  # pylint: disable=redefined-outer-name
    """Create default cable type records."""
    CableType = apps.get_model("dcim", "CableType")
    for name, defaults in DEFAULT_CABLE_TYPES.items():
        CableType.objects.get_or_create(name=name, defaults=defaults)


def clear_default_cable_types(apps, schema_editor=None):  # pylint: disable=redefined-outer-name
    """Delete default cable type records."""
    CableType = apps.get_model("dcim", "CableType")
    for name in DEFAULT_CABLE_TYPES.keys():
        CableType.objects.filter(name=name).delete()


def generate_cable_breakout_mapping(
    a_connectors: int, b_connectors: int, total_lanes: int, labels: Optional[dict] = None
):
    """Generate a default mapping from the given connector and lane counts.

    Optional `labels`: dict keyed by `(a_connector, a_position, b_connector, b_position)` → label string,
    used in place of the default `str(lane_index + 1)` per lane.
    """
    a_positions = total_lanes // a_connectors
    b_positions = total_lanes // b_connectors
    mapping = []
    lane_index = 0
    for a_connector in range(a_connectors):
        for a_position in range(a_positions):
            b_connector = lane_index // b_positions
            b_position = lane_index % b_positions
            # Change 0-indexed iterations to 1-indexed mapping entries!
            entry_key = (a_connector + 1, a_position + 1, b_connector + 1, b_position + 1)
            label = labels.get(entry_key) if labels else None
            mapping.append(
                {
                    "label": label or str(lane_index + 1),
                    "a_connector": entry_key[0],
                    "a_position": entry_key[1],
                    "b_connector": entry_key[2],
                    "b_position": entry_key[3],
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


def _distribute_rowspans(num_cells, num_rows):
    """Split `num_rows` rows into `num_cells` contiguous chunks as evenly as possible.

    Returns a list of `num_cells` rowspans summing to `num_rows`, with any remainder spread
    across the leading chunks (e.g. `(2, 3)` → `[2, 1]`, `(3, 3)` → `[1, 1, 1]`).
    """
    base, remainder = divmod(num_rows, num_cells)
    return [base + (1 if i < remainder else 0) for i in range(num_cells)]


def build_connector_row_layout(mapping):
    """Build the row/rowspan layout for rendering a cable's connector-to-connector connections.

    Given a `CableType.mapping` (a list of dicts with `a_connector`/`b_connector` keys), return a
    flat list of row layout dicts::

        {"a_connector": int|None, "b_connector": int|None, "a_rowspan": int, "b_rowspan": int}

    A rowspan of 0 means that side's cell is covered by an earlier row's rowspan and should be
    skipped when rendering. Both the cable detail view and the HTMX connection-edit form consume
    this layout, so the structure stays consistent between them.

    Each side's distinct connectors are laid out independently down their own column, spread evenly
    over `max(#A connectors, #B connectors)` rows. This yields the familiar nested rowspan layout
    for breakouts (1xN, Nx1, straight NxN) while staying structurally valid for a mesh — e.g. a
    polarity-shuffled 2x2 where each A connector wires to *both* B connectors and no rowspan
    grouping could represent the crossings without overlapping cells and corrupting the table.
    """
    distinct_a = sorted({entry["a_connector"] for entry in mapping})
    distinct_b = sorted({entry["b_connector"] for entry in mapping})
    num_rows = max(len(distinct_a), len(distinct_b))

    rows = [{"a_connector": None, "b_connector": None, "a_rowspan": 0, "b_rowspan": 0} for _ in range(num_rows)]
    for side, connectors in (("a", distinct_a), ("b", distinct_b)):
        row_index = 0
        for connector, span in zip(connectors, _distribute_rowspans(len(connectors), num_rows)):
            rows[row_index][f"{side}_connector"] = connector
            rows[row_index][f"{side}_rowspan"] = span
            row_index += span

    return rows


# Cable validation utilities


def validate_cable_termination(termination, cable_id=None):
    """Run per-termination validations independent of any peer.

    Raises ValidationError if the termination is not a valid endpoint for a cable, namely:
    * an Interface of a non-connectable type (virtual or wireless),
    * a CircuitTermination attached to a provider network, or
    * a termination already attached to a different cable than `cable_id`.
    """
    from nautobot.circuits.models import CircuitTermination
    from nautobot.dcim.models import Interface

    if termination is None:
        return

    if isinstance(termination, Interface) and termination.type in NONCONNECTABLE_IFACE_TYPES:
        raise ValidationError(f"Cables cannot be terminated to {termination.get_type_display()} interfaces")

    if isinstance(termination, CircuitTermination) and termination.provider_network_id is not None:
        raise ValidationError("Circuit terminations attached to a provider network may not be cabled.")

    if termination.present_in_database:
        # Re-query through the join table rather than trusting an in-memory cable reference (which may be stale).
        current_cable_id = (
            type(termination)
            .objects.filter(pk=termination.pk)
            .values_list("cable_termination__cable_id", flat=True)
            .first()
        )
        if current_cable_id and current_cable_id != cable_id:
            raise ValidationError(f"{termination} already has a cable attached (#{current_cable_id})")


def get_breakout_subinterface_name_pattern(interface):
    """Return the DeviceType breakout subinterface naming pattern for an Interface, if any."""
    if interface.device_id:
        return interface.device.device_type.breakout_subinterface_name_pattern

    return ""


def validate_breakout_subinterface_name_pattern(pattern):
    """
    Validate a breakout subinterface naming pattern.

    Args:
        pattern (str): Naming pattern from the parent interface's DeviceType.

    Supported variables:
        - {parent}: The parent interface's name.
        - {position}: The one-based breakout position, matching the stored breakout_position value.
        - {position_index}: The zero-based breakout position, for platforms that name subinterfaces from zero.

    Raises:
        ValidationError: If the pattern uses an unsupported variable or contains malformed format syntax.
    """
    try:
        for _, field_name, _, _ in Formatter().parse(pattern):
            # Literal pattern text has no field name; only validate actual replacement fields.
            if field_name is not None and field_name not in BREAKOUT_SUBINTERFACE_NAME_TOKENS:
                raise ValidationError(f"Unsupported breakout subinterface name token: {{{field_name}}}")
    except ValueError as err:
        raise ValidationError(f"Invalid breakout subinterface name pattern: {err}") from err


def render_breakout_subinterface_name(pattern, parent_interface, position):
    """
    Render a child interface name from a validated breakout subinterface naming pattern.

    Args:
        pattern (str): Naming pattern from the parent interface's DeviceType.
        parent_interface (Interface): Physical trunk interface that will own the child interface.
        position (int): One-based breakout position from the CableType mapping.

    Returns:
        str: Rendered child interface name.

    Example:
        - Interface (name="Ethernet1")
        - pattern="{parent}.{position}"
        - position=1

        The rendered child interface name would be "Ethernet1.1".

    """
    return pattern.format(
        parent=parent_interface.name,
        position=position,
        position_index=position - 1,
    )


def _interface_name_collision(parent_interface, name):
    """Return a same-parent-scope Interface with the given name, if one exists."""
    from nautobot.dcim.models import Interface

    if parent_interface.module_id:
        return Interface.objects.filter(module=parent_interface.module, name=name).first()

    return Interface.objects.filter(device=parent_interface.device, name=name).first()


def get_breakout_subinterface_creation_plan(cable_type, trunk_terminations):
    """Return virtual child interfaces to create for breakout trunk terminations.

    Args:
        cable_type (CableType): Breakout cable type whose mapping defines the child positions.
        trunk_terminations (iterable): ``(termination, connector)`` tuples for the trunk-side
            terminations. The termination may be any cable termination object; only Interface
            terminations can produce child interfaces.

    Returns:
        list[_BreakoutSubinterfaceCreationPlan]: Child interface definitions to create.

    Raises:
        ValidationError: If a validated pattern renders an empty name or a name that is already in use.
    """
    from nautobot.dcim.models import Interface

    planned_interfaces = []

    if cable_type is None or not cable_type.is_breakout:
        return planned_interfaces

    trunk_side = cable_type.trunk_end.lower()

    for trunk_interface, connector in trunk_terminations:
        # Breakout cables can terminate on front/rear ports or circuits; only an Interface can own subinterfaces.
        if not isinstance(trunk_interface, Interface):
            continue

        pattern = get_breakout_subinterface_name_pattern(trunk_interface)
        # A blank DeviceType pattern is an explicit opt-out of breakout subinterface creation.
        if not pattern:
            continue

        lanes = [lane for lane in cable_type.mapping if lane[f"{trunk_side}_connector"] == connector]
        # If the mapping has no lanes for this connector, there is nothing to create for this trunk.
        if not lanes:
            continue

        for lane in lanes:
            position = lane[f"{trunk_side}_position"]
            # Existing children are preserved; the helper only creates missing breakout positions.
            if trunk_interface.child_interfaces.filter(breakout_position=position).exists():
                continue

            name = render_breakout_subinterface_name(pattern, trunk_interface, position)

            if not name:
                raise ValidationError(
                    f"Rendered breakout subinterface name for {trunk_interface} position {position} is empty."
                )

            # We've already checked and skipped any child interfaces in this position, so a name
            # collision here means an interface with this name already exists on the same parent.
            if _interface_name_collision(trunk_interface, name):
                raise ValidationError(f"Interface name {name} is already in use on {trunk_interface.parent}.")

            planned_interfaces.append(
                _BreakoutSubinterfaceCreationPlan(
                    parent_interface=trunk_interface,
                    name=name,
                    breakout_position=position,
                )
            )

    return planned_interfaces


def create_breakout_subinterfaces(cable):
    """Create missing virtual child interfaces for trunk-side Interface terminations on a breakout cable.

    The cable type mapping defines the one-based `breakout_position` values. The trunk interface's
    DeviceType defines the name pattern. DeviceTypes without a pattern do not create child
    interfaces, which lets users opt out of autocreation for valid operational reasons.

    Returns:
        list[Interface]: Created child interfaces.

    Raises:
        ValidationError: If a validated pattern renders an empty name or a name that is already in use.
    """
    from nautobot.dcim.choices import InterfaceTypeChoices
    from nautobot.dcim.models import Interface
    from nautobot.extras.models import Status

    created_interfaces = []

    if cable.cable_type is None or not cable.cable_type.is_breakout:
        return created_interfaces

    trunk_rows = cable.terminations.filter(cable_end=cable.cable_type.trunk_end)
    if not trunk_rows.exists():
        return created_interfaces

    try:
        default_status = Status.objects.get_for_model(Interface).get(name="Active")
    except Status.DoesNotExist:
        default_status = Status.objects.get_for_model(Interface).first()

    with transaction.atomic():
        trunk_terminations = ((trunk_row.termination, trunk_row.connector) for trunk_row in trunk_rows)
        for planned_interface in get_breakout_subinterface_creation_plan(cable.cable_type, trunk_terminations):
            parent_interface = planned_interface.parent_interface
            child_interface = Interface(
                device=parent_interface.device,
                module=parent_interface.module,
                name=planned_interface.name,
                type=InterfaceTypeChoices.TYPE_VIRTUAL,
                status=default_status,
                parent_interface=parent_interface,
                breakout_position=planned_interface.breakout_position,
            )
            child_interface.validated_save()
            created_interfaces.append(child_interface)

    return created_interfaces


# Cable disconnect utilities


def disconnect_termination(termination):
    """Disconnect a single termination from its cable without deleting the cable.

    Removes the CableToCableTermination row for this termination; the post_delete signal handler
    on `CableToCableTermination` rebuilds every CablePath that traversed the cable. The cable
    itself and any other terminations on it are left intact. Returns the cable if successful,
    None otherwise.

    For breakout cables, this correctly preserves cable paths on the surviving lanes: only the
    lane(s) involving the disconnected termination produce partial paths after the rebuild.
    """
    if not termination:
        return None
    cable_termination = getattr(termination, "cable_termination", None)
    if cable_termination is None:
        return None

    cable = cable_termination.cable
    # Wrap the row delete + signal-driven path rebuild in a transaction so a rebuild failure
    # rolls the row deletion back too. Otherwise the cable could end up with stale CablePath
    # rows referencing a now-deleted termination row.
    with transaction.atomic():
        cable_termination.delete()
    return cable


def power_ports_connected_to(target_queryset):
    """Return a queryset of PowerPorts whose cable peer is one of the objects in `target_queryset`.

    `target_queryset` must be a queryset of CableTermination subclass instances (typically
    PowerOutlet or PowerFeed).
    """
    from nautobot.dcim.models import CableToCableTermination, PowerPort
    from nautobot.dcim.models.cables import termination_fk_field

    target_fk = termination_fk_field(target_queryset.model)

    target_cables = CableToCableTermination.objects.filter(**{f"{target_fk}__in": target_queryset}).values("cable_id")

    powerport_ids = CableToCableTermination.objects.filter(power_port__isnull=False, cable_id__in=target_cables).values(
        "power_port_id"
    )

    return PowerPort.objects.filter(pk__in=powerport_ids)


def get_connected_endpoint_tables(instance):
    """Build per-type tables of the connected endpoints reachable from a `PathEndpoint`.

    Walks the instance's CablePaths (one per breakout lane for a breakout cable), groups the
    resolved destination endpoints by model, and renders each group with that model's existing
    list table (resolved via `get_table_for_model`) so that multi-termination cables show *every*
    connected endpoint rather than only the first. Returns a list of
    ``{"heading": ..., "table": ...}`` dicts, ordered by endpoint type.

    Returns an empty list for terminations that are not PathEndpoints (e.g. front/rear ports) or
    that have no resolved destinations.

    TODO: This is the legacy template-based equivalent of `get_connected_endpoint_panels()`. When the
    component detail views that use it are migrated to the UI component framework, drop this helper and
    the `connected_endpoint_tables` context + `content_full_width_page` template blocks in favor of
    spreading `*get_connected_endpoint_panels("<model_name>")` into the view's `object_detail_content`.
    """
    # Imported lazily to avoid the import cycle described in `get_connected_endpoint_panels`.
    from nautobot.core.utils.lookup import get_table_for_model

    cable_paths = getattr(instance, "cable_paths", None)
    if cable_paths is None:
        return []

    grouped = {}
    for path in cable_paths.all():
        destination = path.destination
        if destination is None:
            continue
        grouped.setdefault(destination._meta.model_name, []).append(destination)

    endpoint_tables = []
    for endpoints in grouped.values():
        table_class = get_table_for_model(endpoints[0])
        if table_class is None:
            continue
        endpoint_tables.append(
            {
                "heading": f"{bettertitle(endpoints[0]._meta.verbose_name)} Endpoints",
                "table": table_class(
                    data=endpoints, orderable=False, exclude=("pk", "actions", "connection", "cable_peer")
                ),
            }
        )
    return endpoint_tables


def get_connected_endpoint_panels(source_model_name, *, weight=200, section=None):
    """Build one `ConnectedEndpointsPanel` per endpoint type a termination can connect to.

    The candidate types come from `COMPATIBLE_TERMINATION_TYPES[source_model_name]`, intersected with
    the registered `PathEndpoint` subclasses -- only `PathEndpoint`s can be the destination of a
    `CablePath`, so non-PathEndpoint compatible types (e.g. front/rear ports) are skipped. Each panel
    hides itself when the termination has no connected endpoints of its type.

    Args:
        source_model_name (str): The `model_name` of the termination type whose detail view this is,
            e.g. "interface" or "circuittermination".
        weight (int): The weight of the first panel; subsequent panels increment from here so they
            render in `COMPATIBLE_TERMINATION_TYPES` order.
        section (str, optional): A `SectionChoices` value for the panels. Defaults to `FULL_WIDTH`.

    Returns:
        (list): A list of `ConnectedEndpointsPanel` instances, suitable for spreading into an
        `ObjectDetailContent`'s `panels`.
    """
    # Imported lazily: this module is imported during model loading (dcim.fields -> dcim.lookups ->
    # dcim.utils), so importing the UI/lookup/model layers at the top of the file would cycle.
    from nautobot.core.ui.choices import SectionChoices
    from nautobot.core.ui.object_detail import ConnectedEndpointsPanel
    from nautobot.core.utils.lookup import get_table_for_model
    from nautobot.dcim.models import PathEndpoint

    if section is None:
        section = SectionChoices.FULL_WIDTH

    path_endpoint_models = {
        model._meta.model_name: model for model in apps.get_models() if issubclass(model, PathEndpoint)
    }

    panels = []
    for index, endpoint_type in enumerate(COMPATIBLE_TERMINATION_TYPES.get(source_model_name, [])):
        model = path_endpoint_models.get(endpoint_type)
        if model is None:
            continue
        table_class = get_table_for_model(model)
        if table_class is None:
            continue
        panels.append(
            ConnectedEndpointsPanel(
                table_class=table_class,
                table_title=f"{bettertitle(model._meta.verbose_name)} Endpoints",
                section=section,
                weight=weight + index,
                exclude_columns=["connection", "cable_peer"],
            )
        )
    return panels
