import django_tables2 as tables

from nautobot.core.tables import (
    BaseTable,
    BooleanColumn,
    ButtonsColumn,
    ContentTypesColumn,
    LinkedCountColumn,
    ToggleColumn,
)
from nautobot.users.models import AdminGroup, ObjectPermission, User


class GroupTable(BaseTable):
    """Table for Group list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    users_count = LinkedCountColumn(
        viewname="user:user_list",
        url_params={"object_permissions": "pk"},
        verbose_name="Users",
    )
    actions = ButtonsColumn(AdminGroup, buttons=("edit", "delete"))

    class Meta(BaseTable.Meta):
        model = AdminGroup
        fields = ("pk", "name", "users_count", "actions")
        default_columns = ("pk", "name", "users_count", "actions")


class UserTable(BaseTable):
    """Table for User list view."""

    pk = ToggleColumn()
    username = tables.Column(linkify=True)
    is_superuser = BooleanColumn()
    is_staff = BooleanColumn()
    is_active = BooleanColumn()
    actions = ButtonsColumn(User)

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
            "actions",
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
            "actions",
        )


class ObjectPermissionTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    enabled = BooleanColumn()
    object_types = ContentTypesColumn()
    users_count = LinkedCountColumn(
        viewname="user:user_list",
        url_params={"object_permissions": "pk"},
        verbose_name="Users",
    )
    groups_count = LinkedCountColumn(
        viewname="user:group_list",
        url_params={"object_permissions": "pk"},
        verbose_name="Groups",
    )

    permission_actions = tables.Column(accessor="actions", verbose_name="Actions")
    actions = ButtonsColumn(ObjectPermission, buttons=("edit", "delete"))

    class Meta(BaseTable.Meta):
        model = ObjectPermission
        fields = (
            "pk",
            "name",
            "enabled",
            "object_types",
            "users_count",
            "groups_count",
            "permission_actions",
            "description",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "enabled",
            "object_types",
            "users_count",
            "groups_count",
            "permission_actions",
            "constraints",
            "description",
            "actions",
        )
