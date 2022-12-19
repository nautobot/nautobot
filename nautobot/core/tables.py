import django_tables2 as tables
from django_tables2.utils import Accessor

from nautobot.extras.models import Role
from nautobot.utilities.tables import (
    BaseTable,
    ButtonsColumn,
    ColorColumn,
    ColoredLabelColumn,
    ContentTypesColumn,
    ToggleColumn,
)


#
# Roles
#


class RoleTable(BaseTable):
    """Table for list view of `Role` objects."""

    pk = ToggleColumn()
    name = tables.LinkColumn(viewname="extras:role", args=[Accessor("slug")])
    color = ColorColumn()
    actions = ButtonsColumn(Role, pk_field="slug")
    content_types = ContentTypesColumn(truncate_words=15)

    class Meta(BaseTable.Meta):
        model = Role
        fields = ["pk", "name", "slug", "color", "weight", "content_types", "description"]


class RoleTableMixin(BaseTable):
    """Mixin to add a `role` field to a table."""

    role = ColoredLabelColumn()
