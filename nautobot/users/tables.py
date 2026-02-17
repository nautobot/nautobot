import django_tables2 as tables

from nautobot.core.tables import BaseTable, BooleanColumn, ButtonsColumn, ToggleColumn

from .models import Token


class TokenTable(BaseTable):
    pk = ToggleColumn()
    key = tables.Column(linkify=True)
    description = tables.Column()
    write_enabled = BooleanColumn(verbose_name="Write Enabled")
    created = tables.DateTimeColumn()
    last_updated = tables.DateTimeColumn()
    expires = tables.DateTimeColumn()
    actions = ButtonsColumn(Token)

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = Token
        fields = (
            "pk",
            "key",
            "description",
            "write_enabled",
            "created",
            "last_updated",
            "expires",
            "actions",
        )
        default_columns = (
            "pk",
            "key",
            "description",
            "write_enabled",
            "created",
            "last_updated",
            "expires",
            "actions",
        )
