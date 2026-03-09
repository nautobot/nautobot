import django_tables2 as tables

from nautobot.core.tables import BaseTable, BooleanColumn, ButtonsColumn, ToggleColumn

from .models import Token


class TokenTable(BaseTable):
    pk = ToggleColumn()
    created = tables.DateTimeColumn(linkify=True)
    user = tables.Column()
    expires = tables.DateTimeColumn()
    write_enabled = BooleanColumn(verbose_name="Write Enabled")
    description = tables.Column()
    actions = ButtonsColumn(Token)

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = Token
        fields = (
            "pk",
            "created",
            "user",
            "expires",
            "write_enabled",
            "description",
            "actions",
        )
        default_columns = (
            "pk",
            "created",
            "user",
            "expires",
            "write_enabled",
            "description",
            "actions",
        )
