import django_tables2 as tables
from django_tables2.utils import Accessor
from django.utils.safestring import mark_safe

from nautobot.dcim.models import Cable
from nautobot.extras.tables import StatusTableMixin
from nautobot.utilities.tables import (
    BaseTable,
    ColorColumn,
    TagColumn,
    ToggleColumn,
)
from .template_code import CABLE_LENGTH, CABLE_TERMINATION_PARENT

__all__ = ("CableTable",)


#
# Cables
#
class CableTerminationsColumn(tables.Column):
    """
    Args:
        cable_side: Which side of the cable to report on (A or B)
        attr: The CableTermination attribute to return for each instance (returns the termination object by default)
    """
    def __init__(self, attr, cable_side, *args, **kwargs):
        self.cable_side = cable_side
        self.attr = attr
        super().__init__(accessor=Accessor('endpoints'), *args, **kwargs)

    def _get_terminations(self, manager):
        terminations = set()
        for cable_endpoint in manager.all():
            if cable_endpoint.cable_side == self.cable_side:
                if termination := getattr(cable_endpoint, self.attr, None):
                    terminations.add(termination)

        return terminations

    def render(self, value):
        links = [
            f'<a href="{term.get_absolute_url()}">{term}</a>' for term in self._get_terminations(value)
        ]
        return mark_safe('<br />'.join(links) or '&mdash;')

    def value(self, value):
        return ','.join([str(t) for t in self._get_terminations(value)])


class CableTable(StatusTableMixin, BaseTable):
    pk = ToggleColumn()
    id = tables.Column(linkify=True, verbose_name="ID")

    a_terminations = CableTerminationsColumn(
        cable_side='A',
        attr="termination",
        orderable=False,
        verbose_name='Termination A',
    )
    b_terminations = CableTerminationsColumn(
        cable_side='B',
        attr="termination",
        orderable=False,
        verbose_name='Termination B',
    )
    device_a = CableTerminationsColumn(
        cable_side='A',
        attr='_device',
        orderable=False,
        verbose_name='Device A'
    )
    device_b = CableTerminationsColumn(
        cable_side='B',
        attr='_device',
        orderable=False,
        verbose_name='Device B'
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
            "device_a",
            "device_b",
            "a_terminations",
            "b_terminations",
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
            "a_terminations",
            "b_terminations",
            "status",
            "type",
        )
