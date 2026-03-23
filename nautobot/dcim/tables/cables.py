import django_tables2 as tables
from django_tables2.utils import Accessor

from nautobot.core.tables import (
    BaseTable,
    BooleanColumn,
    ButtonsColumn,
    ColorColumn,
    TagColumn,
    ToggleColumn,
)
from nautobot.dcim.models import Cable, CableType
from nautobot.extras.tables import StatusTableMixin

from .template_code import CABLE_LENGTH, CABLE_TERMINATION_PARENT, CABLE_TERMINATIONS_MULTI

__all__ = ("CableTable", "CableTypeTable")


#
# Cables
#


class CableTypeTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    manufacturer = tables.Column(linkify=True)
    has_embedded_transceivers = BooleanColumn()
    is_shuffle = BooleanColumn()
    total_strands = tables.Column(orderable=False)
    is_breakout = BooleanColumn(orderable=False)
    tags = TagColumn(url_name="dcim:cabletype_list")
    actions = ButtonsColumn(CableType)

    class Meta(BaseTable.Meta):
        model = CableType
        fields = (
            "pk",
            "name",
            "description",
            "manufacturer",
            "part_number",
            "a_connectors",
            "b_connectors",
            "total_lanes",
            "has_embedded_transceivers",
            "is_shuffle",
            "strands_per_lane",
            "polarity_method",
            "total_strands",
            "is_breakout",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "manufacturer",
            "part_number",
            "a_connectors",
            "b_connectors",
            "total_lanes",
            "is_shuffle",
            "tags",
            "actions",
        )


class CableTable(StatusTableMixin, BaseTable):
    pk = ToggleColumn()
    id = tables.Column(linkify=True, verbose_name="ID")
    cable_type = tables.Column(linkify=True, verbose_name="Cable Type")
    termination_a_parent = tables.TemplateColumn(
        template_code=CABLE_TERMINATION_PARENT,
        accessor=Accessor("termination_a"),
        orderable=False,
        verbose_name="Side A",
    )
    termination_a = tables.LinkColumn(
        accessor=Accessor("termination_a"),
        orderable=False,
        verbose_name="Termination A",
    )
    terminations_a = tables.TemplateColumn(
        template_code=CABLE_TERMINATIONS_MULTI,
        accessor=Accessor("terminations_a"),
        orderable=False,
        verbose_name="A-Side Terminations",
    )
    termination_b_parent = tables.TemplateColumn(
        template_code=CABLE_TERMINATION_PARENT,
        accessor=Accessor("termination_b"),
        orderable=False,
        verbose_name="Side B",
    )
    termination_b = tables.LinkColumn(
        accessor=Accessor("termination_b"),
        orderable=False,
        verbose_name="Termination B",
    )
    terminations_b = tables.TemplateColumn(
        template_code=CABLE_TERMINATIONS_MULTI,
        accessor=Accessor("terminations_b"),
        orderable=False,
        verbose_name="B-Side Terminations",
    )
    length = tables.TemplateColumn(template_code=CABLE_LENGTH, order_by="_abs_length")
    color = ColorColumn()
    tags = TagColumn(url_name="dcim:cable_list")

    class Meta(BaseTable.Meta):
        model = Cable
        fields = (
            "pk",
            "id",
            "label",
            "cable_type",
            "termination_a_parent",
            "termination_a",
            "terminations_a",
            "termination_b_parent",
            "termination_b",
            "terminations_b",
            "status",
            "type",
            "color",
            "length",
            "tags",
        )
        default_columns = (
            "pk",
            "id",
            "label",
            "terminations_a",
            "terminations_b",
            "status",
            "type",
        )
