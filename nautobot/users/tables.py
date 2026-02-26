from django.contrib.auth.models import Group
import django_tables2 as tables

from nautobot.core.tables import BaseTable, BooleanColumn, ToggleColumn
from nautobot.users.models import User


class GroupTable(BaseTable):
    """Table for Group list view."""

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = Group
        fields = ("name",)
        default_columns = ("name",)


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
