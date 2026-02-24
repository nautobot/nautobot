# tables.py
import django_tables2 as tables

from nautobot.core.tables import (
    BaseTable,
    ToggleColumn,
)
from nautobot.users.models import ObjectPermission


class ObjectPermissionTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    enabled = tables.BooleanColumn(linkify=True)
    description = tables.Column(linkify=True)
    object_types = tables.Column(verbose_name="Models", orderable=False)
    groups = tables.Column(verbose_name="Groups", orderable=False)
    users = tables.Column(verbose_name="Users", orderable=False)
    permission_actions = tables.Column(accessor="actions", linkify=True, verbose_name="Actions")
    constraints = tables.Column(linkify=True)

    def render_object_types(self, value):
        if not value.exists():
            return ""

        # Display as app_label.ModelName
        return ", ".join(f"{ct.app_label} | {ct.model}" for ct in value.all())

    def render_groups(self, value):
        if not value.exists():
            return "—"  # empty column if no groups

        # Show only group names
        return ", ".join(group.name for group in value.all())

    def render_permission_actions(self, value):
        if value:
            return ", ".join(value)
        return "—"

    def render_users(self, value):
        # value is a ManyRelatedManager
        if not value.exists():
            return "—"  # return empty cell

        return ", ".join([user.username for user in value.all()])

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
        )
