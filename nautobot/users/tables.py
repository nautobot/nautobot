import django_tables2 as tables

from nautobot.core.tables import BaseTable, BooleanColumn, ButtonsColumn, ToggleColumn

from .models import Token

_actions_template = """
<li><a href="{% url 'user:token' pk=record.pk %}" class="dropdown-item"><span class="mdi mdi-information-outline" aria-hidden="true"></span>Details</a></li>
"""


class TokenTable(BaseTable):
    pk = ToggleColumn()
    created = tables.DateTimeColumn(linkify=True)
    user = tables.Column()
    expires = tables.DateTimeColumn()
    write_enabled = BooleanColumn(verbose_name="Write Enabled")
    description = tables.Column()
    actions = ButtonsColumn(Token, prepend_template=_actions_template)

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
            "user",
            "expires",
            "write_enabled",
            "description",
            "actions",
        )
