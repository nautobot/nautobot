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
from nautobot.dcim.models import Cable, CableBreakoutType
from nautobot.extras.tables import StatusTableMixin

from .template_code import CABLE_LENGTH, CABLE_TERMINATION_PARENT

__all__ = ("CableTable",)


#
# Cables
#


class CableBreakoutTypeTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    is_shuffle = BooleanColumn()
    total_lanes = tables.Column(orderable=False)
    total_strands = tables.Column(orderable=False)
    is_breakout = BooleanColumn()
    tags = TagColumn(url_name="dcim:cablebreakouttype_list")
    actions = ButtonsColumn(CableBreakoutType)

    class Meta(BaseTable.Meta):
        model = CableBreakoutType
        fields = (
            "pk",
            "name",
            "description",
            "a_connectors",
            "a_positions",
            "b_connectors",
            "b_positions",
            "is_shuffle",
            "strands_per_lane",
            "polarity_method",
            "total_lanes",
            "total_strands",
            "is_breakout",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
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
    length = tables.TemplateColumn(template_code=CABLE_LENGTH, order_by="_abs_length")
    color = ColorColumn()
    tags = TagColumn(url_name="dcim:cable_list")

    class Meta(BaseTable.Meta):
        model = Cable
        fields = (
            "pk",
            "id",
            "label",
            "termination_a_parent",
            "termination_a",
            "termination_b_parent",
            "termination_b",
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
            "termination_a_parent",
            "termination_a",
            "termination_b_parent",
            "termination_b",
            "status",
            "type",
        )
