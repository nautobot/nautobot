import django_tables2 as tables

from nautobot.core.tables import BaseTable, BooleanColumn, ButtonsColumn, ToggleColumn
from nautobot.users.models import AdminGroup, ObjectPermission, User


class GroupTable(BaseTable):
    """Table for Group list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    user_count = tables.Column(verbose_name="Users")
    actions = ButtonsColumn(AdminGroup, buttons=("edit", "delete"))

    class Meta(BaseTable.Meta):
        model = AdminGroup
        fields = ("pk", "name", "user_count", "actions")
        default_columns = ("pk", "name", "user_count", "actions")


class ObjectPermissionTable(BaseTable):
    """Read-only table for displaying related object permissions."""

    name = tables.Column()
    enabled = BooleanColumn()
    object_types = tables.ManyToManyColumn(transform=str)
    actions = tables.Column(verbose_name="Actions")
    description = tables.Column()

    class Meta(BaseTable.Meta):
        model = ObjectPermission
        fields = ("name", "enabled", "object_types", "actions", "description")
        default_columns = ("name", "enabled", "object_types", "actions", "description")


class UserTable(BaseTable):
    """Table for User list view."""

    pk = ToggleColumn()
    username = tables.Column(linkify=True)
    is_superuser = BooleanColumn()
    is_staff = BooleanColumn()
    is_active = BooleanColumn()

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = User
        fields = (
            "pk",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_superuser",
            "is_staff",
            "is_active",
        )
        default_columns = (
            "pk",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_superuser",
            "is_staff",
            "is_active",
        )
