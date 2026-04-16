# tables.py
import django_tables2 as tables

from nautobot.core.tables import (
    BaseTable,
    ButtonsColumn,
    ToggleColumn,
)
from nautobot.users.models import ObjectPermission


class ObjectPermissionTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    permission_actions = tables.Column(accessor="actions", verbose_name="Actions")
    actions = ButtonsColumn(ObjectPermission, buttons=("edit", "delete"))

    class Meta(BaseTable.Meta):
        model = ObjectPermission
        fields = (
            "pk",
            "name",
            "enabled",
            "object_types",
            "users",
            "groups",
            "permission_actions",
            "constraints",
            "description",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "enabled",
            "object_types",
            "users",
            "groups",
            "permission_actions",
            "constraints",
            "description",
            "actions",
        )
