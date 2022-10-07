from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.utils.html import format_html

import django_tables2 as tables


class InstalledPluginsTable(tables.Table):
    """
    Custom table class based on nautobot.utilities.tables.BaseTable, but without a dependency on QuerySets.
    """

    name = tables.Column(
        linkify=lambda record: reverse("plugins:plugin_detail", kwargs={"plugin": record["package_name"]})
    )
    package_name = tables.Column()
    author = tables.Column()
    author_email = tables.Column()
    description = tables.Column()
    version = tables.Column()
    actions = tables.TemplateColumn(
        template_code="""
            {% if record.actions.home %}
            <a href="{% url record.actions.home %}" class="btn btn-success btn-xs" title="Home">
            {% else %}
            <a href="" class="btn btn-success btn-xs disabled" title="No home link provided">
            {% endif %}
                <i class="mdi mdi-home"></i>
            </a>
            {% if record.actions.configure %}
            <a href="{% url record.actions.configure %}" class="btn btn-warning btn-xs" title="Configure">
            {% else %}
            <a href="" class="btn btn-warning btn-xs disabled" title="No configuration link provided">
            {% endif %}
                <i class="mdi mdi-cog"></i>
            </a>
            {% if record.actions.docs %}
            <a href="{% url record.actions.docs %}" class="btn btn-info btn-xs" title="Docs">
            {% else %}
            <a href="" class="btn btn-info btn-xs disabled" title="No docs provided">
            {% endif %}
                <i class="mdi mdi-book-open-page-variant"></i>
            </a>
        """,
        attrs={"td": {"class": "text-right text-nowrap noprint"}},
        verbose_name="",
    )

    class Meta:
        attrs = {
            "class": "table table-hover table-headings",
        }
        default_columns = ("name", "description", "version", "actions")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if self.empty_text is None:
            self.empty_text = "No installed plugins found"

        # Hide non-default columns
        default_columns = list(self.Meta.default_columns)
        extra_columns = [c[0] for c in kwargs.get("extra_columns", [])]  # extra_columns is a list of tuples
        for column in self.columns:
            if column.name not in default_columns and column.name not in extra_columns:
                self.columns.hide(column.name)

        # Show and/or reorder columns based on user settings
        if user is not None and not isinstance(user, AnonymousUser):
            user_columns = user.get_config(f"tables.{self.__class__.__name__}.columns")
            if user_columns:
                # User can't show/hide the "actions" column
                actions = self.base_columns.pop("actions", None)

                for name, column in self.base_columns.items():
                    if name in user_columns:
                        self.columns.show(name)
                    else:
                        self.columns.hide(name)
                self.sequence = [c for c in user_columns if c in self.base_columns]

                if actions:
                    self.base_columns["actions"] = actions
                    self.sequence.append("actions")

    @property
    def configurable_columns(self):
        selected_columns = [
            (name, self.columns[name].verbose_name) for name in self.sequence if name not in ["pk", "actions"]
        ]
        available_columns = [
            (name, column.verbose_name)
            for name, column in self.columns.items()
            if name not in self.sequence and name not in ["pk", "actions"]
        ]
        return selected_columns + available_columns

    @property
    def visible_columns(self):
        return [name for name in self.sequence if self.columns[name].visible]

    def render_package_name(self, value):
        return format_html(f"<code>{value}</code>")

    def render_author_email(self, value):
        if value:
            return format_html(f'<a href="mailto:{value}">{value}</a>')
        return value
