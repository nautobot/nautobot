import django_tables2 as tables

from nautobot.core.tables import (
    BaseTable,
    ButtonsColumn,
    TagColumn,
    ToggleColumn,
)

from .models import CloudAccount


class CloudAccountTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    provider = tables.Column(linkify=True)
    secrets_group = tables.Column(linkify=True)
    tags = TagColumn(url_name="cloud:cloudaccount_list")
    actions = ButtonsColumn(CloudAccount)

    class Meta(BaseTable.Meta):
        model = CloudAccount
        fields = (
            "pk",
            "name",
            "account_number",
            "description",
            "provider",
            "secrets_group",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "account_number",
            "provider",
            "actions",
        )
