import django_tables2 as tables
from django.utils.html import format_html

from nautobot.core.models.dynamic_groups import DynamicGroup, DynamicGroupMembership
from nautobot.utilities.tables import BaseTable, ButtonsColumn, ToggleColumn


class DynamicGroupTable(BaseTable):
    """Base table for displaying dynamic groups in list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    members = tables.Column(accessor="count", verbose_name="Group Members", orderable=False)
    actions = ButtonsColumn(DynamicGroup, pk_field="slug")

    class Meta(BaseTable.Meta):  # pylint: disable=too-few-public-methods
        model = DynamicGroup
        fields = (
            "pk",
            "name",
            "description",
            "content_type",
            "members",
            "actions",
        )

    def render_members(self, value, record):
        """Provide a filtered URL to the group members (if any)."""
        # Only linkify if there are members.
        if not value:
            return value
        return format_html('<a href="{}">{}</a>', record.get_group_members_url(), value)


class DynamicGroupMembershipTable(DynamicGroupTable):
    """Hybrid table for displaying info for both group and membership."""

    description = tables.Column(accessor="group.description")
    actions = ButtonsColumn(DynamicGroup, pk_field="slug", buttons=("edit",))

    class Meta(BaseTable.Meta):
        model = DynamicGroupMembership
        fields = (
            "pk",
            "operator",
            "name",
            "weight",
            "members",
            "description",
            "actions",
        )
        exclude = ("content_type",)


DESCENDANTS_LINK = """
{% load helpers %}
{% for node, depth in descendants_tree.items %}
    {% if record.pk == node %}
        {% for i in depth|as_range %}
            {% if not forloop.first %}
            <i class="mdi mdi-circle-small"></i>
            {% endif %}
        {% endfor %}
    {% endif %}
{% endfor %}
<a href="{{ record.get_absolute_url }}">{{ record.name }}</a>
"""


OPERATOR_LINK = """
{% load helpers %}
{% for node, depth in descendants_tree.items %}
    {% if record.pk == node %}
        {% for i in depth|as_range %}
            {% if not forloop.first %}
            <i class="mdi mdi-circle-small"></i>
            {% endif %}
        {% endfor %}
    {% endif %}
{% endfor %}
{{ record.get_operator_display }}
"""


class NestedDynamicGroupDescendantsTable(DynamicGroupMembershipTable):
    """
    Subclass of DynamicGroupMembershipTable used in detail views to show parenting hierarchy with dots.
    """

    operator = tables.TemplateColumn(template_code=OPERATOR_LINK)
    name = tables.TemplateColumn(template_code=DESCENDANTS_LINK)

    class Meta(DynamicGroupMembershipTable.Meta):
        pass


ANCESTORS_LINK = """
{% load helpers %}
{% for node in ancestors_tree %}
    {% if node.name == record.name %}
        {% for i in node.depth|as_range %}
            {% if not forloop.first %}
            <i class="mdi mdi-circle-small"></i>
            {% endif %}
        {% endfor %}
    {% endif %}
{% endfor %}
<a href="{{ record.get_absolute_url }}">{{ record.name }}</a>
"""


class NestedDynamicGroupAncestorsTable(DynamicGroupTable):
    """
    Subclass of DynamicGroupTable used in detail views to show parenting hierarchy with dots.
    """

    name = tables.TemplateColumn(template_code=ANCESTORS_LINK)
    actions = ButtonsColumn(DynamicGroup, pk_field="slug", buttons=("edit",))

    class Meta(DynamicGroupTable.Meta):
        fields = ["name", "members", "description", "actions"]
        exclude = ["content_type"]
