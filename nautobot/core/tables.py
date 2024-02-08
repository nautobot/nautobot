import logging

from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import FieldDoesNotExist
from django.db import NotSupportedError
from django.db.models.fields.related import ForeignKey, RelatedField
from django.db.models.fields.reverse_related import ManyToOneRel
from django.urls import reverse
from django.utils.html import escape, format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.text import Truncator
import django_tables2
from django_tables2.data import TableQuerysetData
from django_tables2.utils import Accessor, OrderBy, OrderByTuple
from tree_queries.models import TreeNode

from nautobot.core.templatetags import helpers
from nautobot.core.utils import lookup
from nautobot.extras import choices, models

logger = logging.getLogger(__name__)


class BaseTable(django_tables2.Table):
    """
    Default table for object lists

    :param user: Personalize table display for the given user (optional). Has no effect if AnonymousUser is passed.
    """

    class Meta:
        attrs = {
            "class": "table table-hover table-headings",
        }

    def __init__(self, *args, user=None, **kwargs):
        # Add custom field columns
        model = self._meta.model

        for cf in models.CustomField.objects.get_for_model(model):
            name = cf.add_prefix_to_cf_key()
            self.base_columns[name] = CustomFieldColumn(cf)

        for cpf in models.ComputedField.objects.get_for_model(model):
            self.base_columns[f"cpf_{cpf.key}"] = ComputedFieldColumn(cpf)

        for relationship in models.Relationship.objects.get_for_model_source(model):
            if not relationship.symmetric:
                self.base_columns[f"cr_{relationship.key}_src"] = RelationshipColumn(
                    relationship, side=choices.RelationshipSideChoices.SIDE_SOURCE
                )
            else:
                self.base_columns[f"cr_{relationship.key}_peer"] = RelationshipColumn(
                    relationship, side=choices.RelationshipSideChoices.SIDE_PEER
                )

        for relationship in models.Relationship.objects.get_for_model_destination(model):
            if not relationship.symmetric:
                self.base_columns[f"cr_{relationship.key}_dst"] = RelationshipColumn(
                    relationship, side=choices.RelationshipSideChoices.SIDE_DESTINATION
                )
            # symmetric relationships are already handled above in the source_type case

        # Init table
        super().__init__(*args, **kwargs)

        # Set default empty_text if none was provided
        if self.empty_text is None:
            self.empty_text = f"No {self._meta.model._meta.verbose_name_plural} found"

        # Hide non-default columns
        default_columns = list(getattr(self.Meta, "default_columns", []))
        extra_columns = [c[0] for c in kwargs.get("extra_columns", [])]  # extra_columns is a list of tuples
        if default_columns:
            for column in self.columns:
                if column.name not in default_columns and column.name not in extra_columns:
                    # Hide the column if it is non-default *and* not manually specified as an extra column
                    self.columns.hide(column.name)

        # Apply custom column ordering for user
        if user is not None and not isinstance(user, AnonymousUser):
            columns = user.get_config(f"tables.{self.__class__.__name__}.columns")
            if columns:
                pk = self.base_columns.pop("pk", None)
                actions = self.base_columns.pop("actions", None)

                for name, column in self.base_columns.items():
                    if name in columns:
                        self.columns.show(name)
                    else:
                        self.columns.hide(name)
                self.sequence = [c for c in columns if c in self.base_columns]

                # Always include PK and actions column, if defined on the table
                if pk:
                    self.base_columns["pk"] = pk
                    self.sequence.insert(0, "pk")
                if actions:
                    self.base_columns["actions"] = actions
                    self.sequence.append("actions")

        # Dynamically update the table's QuerySet to ensure related fields are pre-fetched
        if isinstance(self.data, TableQuerysetData):
            queryset = self.data.data
            select_fields = []
            prefetch_fields = []
            for column in self.columns:
                if column.visible:
                    column_model = model
                    accessor = column.accessor
                    select_path = []
                    prefetch_path = []
                    for field_name in accessor.split(accessor.SEPARATOR):
                        try:
                            field = column_model._meta.get_field(field_name)
                        except FieldDoesNotExist:
                            break
                        if isinstance(field, ForeignKey) and not prefetch_path:
                            # Follow ForeignKeys to the related model via select_related
                            select_path.append(field_name)
                            column_model = field.remote_field.model
                        elif isinstance(field, (RelatedField, ManyToOneRel)) and not select_path:
                            # Follow O2M and M2M relations to the related model via prefetch_related
                            prefetch_path.append(field_name)
                            column_model = field.remote_field.model
                        elif isinstance(field, GenericForeignKey) and not select_path:
                            # Can't prefetch beyond a GenericForeignKey
                            prefetch_path.append(field_name)
                            break
                        else:
                            # Need to stop processing once field is not a RelatedField or GFK
                            # Ex: ["_custom_field_data", "tenant_id"] needs to exit
                            # the loop as "tenant_id" would be misidentified as a RelatedField.
                            break
                    if select_path:
                        select_fields.append("__".join(select_path))
                    elif prefetch_path:
                        prefetch_fields.append("__".join(prefetch_path))

            if select_fields:
                # Django doesn't allow .select_related() on a QuerySet that had .values()/.values_list() applied, or
                # one that has had union()/intersection()/difference() applied.
                # We can detect and avoid these cases the same way that Django itself does.
                if queryset._fields is not None:
                    logger.debug(
                        "NOT applying select_related(%s) to %s QuerySet as it includes .values()/.values_list()",
                        select_fields,
                        model.__name__,
                    )
                elif queryset.query.combinator:
                    logger.debug(
                        "NOT applying select_related(%s) to %s QuerySet as it is a combinator query",
                        select_fields,
                        model.__name__,
                    )
                else:
                    logger.debug("Applying .select_related(%s) to %s QuerySet", select_fields, model.__name__)
                    # Belt and suspenders - we should have avoided any error cases above, but be safe anyway:
                    try:
                        queryset = queryset.select_related(*select_fields)
                    except (TypeError, ValueError, NotSupportedError) as exc:
                        logger.warning(
                            "Unexpected error when trying to .select_related() on %s QuerySet: %s",
                            model.__name__,
                            exc,
                        )

            if prefetch_fields:
                if queryset.query.combinator:
                    logger.debug(
                        "NOT applying prefetch_related(%s) to %s QuerySet as it is a combinator query",
                        prefetch_fields,
                        model.__name__,
                    )
                else:
                    logger.debug("Applying .prefetch_related(%s) to %s QuerySet", prefetch_fields, model.__name__)
                    # Belt and suspenders - we should have avoided any error cases above, but be safe anyway:
                    try:
                        queryset = queryset.prefetch_related(*prefetch_fields)
                    except (TypeError, ValueError, NotSupportedError) as exc:
                        logger.warning(
                            "Unexpected error when trying to .prefetch_related() on %s QuerySet: %s",
                            model.__name__,
                            exc,
                        )

            self.data.data = queryset

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

    @property
    def order_by(self):
        return self._order_by

    @order_by.setter
    def order_by(self, value):
        """
        Order the rows of the table based on columns.

        Arguments:
            value: iterable or comma separated string of order by aliases.
        """
        # collapse empty values to ()
        order_by = () if not value else value
        # accept string
        order_by = order_by.split(",") if isinstance(order_by, str) else order_by
        valid = []

        for alias in order_by:
            name = OrderBy(alias).bare
            if name in self.columns and self.columns[name].orderable:
                valid.append(alias)
        self._order_by = OrderByTuple(valid)

        # The above block of code is copied from super().order_by
        # due to limitations in directly calling parent class methods within a property setter.
        # See Python bug report: https://bugs.python.org/issue14965
        model = getattr(self.Meta, "model", None)
        if model and issubclass(model, TreeNode):
            # Use the TreeNode model's approach to sorting
            queryset = self.data.data
            # If the data passed into the Table is a list (as in cases like BulkImport post),
            # convert this list to a queryset.
            # This ensures consistent behavior regardless of the input type.
            if isinstance(self.data.data, list):
                queryset = model.objects.filter(pk__in=[instance.pk for instance in self.data.data])
            self.data.data = queryset.extra(order_by=self._order_by)
        else:
            # Otherwise, use the default sorting method
            self.data.order_by(self._order_by)


#
# Table columns
#


class ToggleColumn(django_tables2.CheckBoxColumn):
    """
    Extend CheckBoxColumn to add a "toggle all" checkbox in the column header.
    """

    def __init__(self, *args, **kwargs):
        default = kwargs.pop("default", "")
        visible = kwargs.pop("visible", False)
        if "attrs" not in kwargs:
            kwargs["attrs"] = {"td": {"class": "min-width"}}
        super().__init__(*args, default=default, visible=visible, **kwargs)

    @property
    def header(self):
        return mark_safe('<input type="checkbox" class="toggle" title="Toggle all" />')  # noqa: S308  # suspicious-mark-safe-usage, but this is a static string so it's safe


class BooleanColumn(django_tables2.Column):
    """
    Custom implementation of BooleanColumn to render a nicely-formatted checkmark or X icon instead of a Unicode
    character.
    """

    def render(self, value):
        return helpers.render_boolean(value)


class ButtonsColumn(django_tables2.TemplateColumn):
    """
    Render edit, delete, and changelog buttons for an object.

    :param model: Model class to use for calculating URL view names
    :param prepend_template: Additional template content to render in the column (optional)
    :param return_url_extra: String to append to the return URL (e.g. for specifying a tab) (optional)
    """

    buttons = ("changelog", "edit", "delete")
    attrs = {"td": {"class": "text-right text-nowrap noprint"}}
    # Note that braces are escaped to allow for string formatting prior to template rendering
    template_code = """
    {{% if "changelog" in buttons %}}
        <a href="{{% url '{changelog_route}' {pk_field}=record.{pk_field} %}}" class="btn btn-default btn-xs" title="Change log">
            <i class="mdi mdi-history"></i>
        </a>
    {{% endif %}}
    {{% if "edit" in buttons and perms.{app_label}.change_{model_name} %}}
        <a href="{{% url '{edit_route}' {pk_field}=record.{pk_field} %}}?return_url={{{{ request.path }}}}{{{{ return_url_extra }}}}" class="btn btn-xs btn-warning" title="Edit">
            <i class="mdi mdi-pencil"></i>
        </a>
    {{% endif %}}
    {{% if "delete" in buttons and perms.{app_label}.delete_{model_name} %}}
        <a href="{{% url '{delete_route}' {pk_field}=record.{pk_field} %}}?return_url={{{{ request.path }}}}{{{{ return_url_extra }}}}" class="btn btn-xs btn-danger" title="Delete">
            <i class="mdi mdi-trash-can-outline"></i>
        </a>
    {{% endif %}}
    """

    def __init__(
        self,
        model,
        *args,
        pk_field="pk",
        buttons=None,
        prepend_template=None,
        return_url_extra="",
        **kwargs,
    ):
        if prepend_template:
            prepend_template = prepend_template.replace("{", "{{")
            prepend_template = prepend_template.replace("}", "}}")
            self.template_code = prepend_template + self.template_code

        app_label = model._meta.app_label
        changelog_route = lookup.get_route_for_model(model, "changelog")
        edit_route = lookup.get_route_for_model(model, "edit")
        delete_route = lookup.get_route_for_model(model, "delete")

        template_code = self.template_code.format(
            app_label=app_label,
            model_name=model._meta.model_name,
            changelog_route=changelog_route,
            edit_route=edit_route,
            delete_route=delete_route,
            pk_field=pk_field,
            buttons=buttons,
        )

        super().__init__(template_code=template_code, *args, **kwargs)

        self.extra_context.update(
            {
                "buttons": buttons or self.buttons,
                "return_url_extra": return_url_extra,
            }
        )

    def header(self):  # pylint: disable=invalid-overridden-method
        return ""


class ChoiceFieldColumn(django_tables2.Column):
    """
    Render a ChoiceField value inside a <span> indicating a particular CSS class. This is useful for displaying colored
    choices. The CSS class is derived by calling .get_FOO_class() on the row record.
    """

    def render(self, record, bound_column, value):  # pylint: disable=arguments-differ
        if value:
            name = bound_column.name
            css_class = getattr(record, f"get_{name}_class")()
            label = getattr(record, f"get_{name}_display")()
            return format_html('<span class="label label-{}">{}</span>', css_class, label)
        return self.default


class ColorColumn(django_tables2.Column):
    """
    Display a color (#RRGGBB).
    """

    def render(self, value):
        return format_html('<span class="label color-block" style="background-color: #{}">&nbsp;</span>', value)


class ColoredLabelColumn(django_tables2.TemplateColumn):
    """
    Render a colored label (e.g. for DeviceRoles).
    """

    template_code = """
    {% load helpers %}
    {% if value %}<label class="label" style="color: {{ value.color|fgcolor }}; background-color: #{{ value.color }}">{{ value }}</label>{% else %}&mdash;{% endif %}
    """

    def __init__(self, *args, **kwargs):
        super().__init__(template_code=self.template_code, *args, **kwargs)


class LinkedCountColumn(django_tables2.Column):
    """
    Render a count of related objects linked to a filtered URL.

    :param viewname: The view name to use for URL resolution
    :param view_kwargs: Additional kwargs to pass for URL resolution (optional)
    :param url_params: A dict of query parameters to append to the URL (e.g. ?foo=bar) (optional)
    """

    def __init__(self, viewname, *args, view_kwargs=None, url_params=None, default=0, **kwargs):
        self.viewname = viewname
        self.view_kwargs = view_kwargs or {}
        self.url_params = url_params
        super().__init__(*args, default=default, **kwargs)

    def render(self, record, value):  # pylint: disable=arguments-differ
        if value:
            url = reverse(self.viewname, kwargs=self.view_kwargs)
            if self.url_params:
                url += "?" + "&".join([f"{k}={getattr(record, v)}" for k, v in self.url_params.items()])
            return format_html('<a href="{}">{}</a>', url, value)
        return value


class TagColumn(django_tables2.TemplateColumn):
    """
    Display a list of tags assigned to the object.
    """

    template_code = """
    {% for tag in value.all %}
        {% include 'utilities/templatetags/tag.html' %}
    {% empty %}
        <span class="text-muted">&mdash;</span>
    {% endfor %}
    """

    def __init__(self, url_name=None):
        super().__init__(template_code=self.template_code, extra_context={"url_name": url_name})


class ContentTypesColumn(django_tables2.ManyToManyColumn):
    """
    Display a list of `content_types` m2m assigned to an object.

    Default sorting of content-types is by pk. This sorting comes at a per-row
    performance hit to querysets for table views. If this becomes an issue,
    set `sort_items=False`.

    :param sort_items: Whether to sort by `(app_label, name)`. (default: True)
    :param truncate_words:
        Number of words at which to truncate, or `None` to disable. (default: None)
    """

    def __init__(self, sort_items=True, truncate_words=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sort_items = sort_items
        self.truncate_words = truncate_words

    def filter(self, qs):
        """Overload filter to optionally sort items."""
        if self.sort_items:
            qs = qs.order_by("app_label", "model")
        return qs.all()

    def render(self, value):
        """Overload render to optionally truncate words."""
        value = super().render(value)
        if self.truncate_words is not None:
            trunc = Truncator(value)
            value = trunc.words(self.truncate_words)
        return value


class ComputedFieldColumn(django_tables2.Column):
    """
    Display computed fields in the appropriate format.
    """

    def __init__(self, computedfield, *args, **kwargs):
        self.computedfield = computedfield
        kwargs["verbose_name"] = computedfield.label
        kwargs["empty_values"] = []
        kwargs["orderable"] = False

        super().__init__(*args, **kwargs)

    def render(self, record):
        return self.computedfield.render({"obj": record})


class CustomFieldColumn(django_tables2.Column):
    """
    Display custom fields in the appropriate format.
    """

    # Add [] to empty_values so when there is no choice populated for multiselect_cf i.e. [], "—" is returned automatically.
    empty_values = (None, "", [])

    def __init__(self, customfield, *args, **kwargs):
        self.customfield = customfield
        kwargs["accessor"] = Accessor(f"_custom_field_data__{customfield.key}")
        kwargs["verbose_name"] = customfield.label

        super().__init__(*args, **kwargs)

    def render(self, record, bound_column, value):  # pylint: disable=arguments-differ
        if self.customfield.type == choices.CustomFieldTypeChoices.TYPE_BOOLEAN:
            template = helpers.render_boolean(value)
        elif self.customfield.type == choices.CustomFieldTypeChoices.TYPE_MULTISELECT:
            template = format_html_join(" ", '<span class="label label-default">{}</span>', ((v,) for v in value))
        elif self.customfield.type == choices.CustomFieldTypeChoices.TYPE_SELECT:
            template = format_html('<span class="label label-default">{}</span>', value)
        elif self.customfield.type == choices.CustomFieldTypeChoices.TYPE_URL:
            template = format_html('<a href="{}">{}</a>', value, value)
        else:
            template = escape(value)

        return template


class RelationshipColumn(django_tables2.Column):
    """
    Display relationship association instances in the appropriate format.
    """

    # Add [] to empty_values so when there is no relationship associations i.e. [], "—" is returned automatically.
    empty_values = (None, "", [])

    def __init__(self, relationship, side, *args, **kwargs):
        self.relationship = relationship
        self.side = side
        self.peer_side = choices.RelationshipSideChoices.OPPOSITE[side]
        kwargs.setdefault("verbose_name", relationship.get_label(side))
        kwargs.setdefault("accessor", Accessor("associations"))
        super().__init__(orderable=False, *args, **kwargs)

    def render(self, record, value):  # pylint: disable=arguments-differ
        # Filter the relationship associations by the relationship instance.
        # Since associations accessor returns all the relationship associations regardless of the relationship.
        value = [v for v in value if v.relationship == self.relationship]
        if not self.relationship.symmetric:
            if self.side == choices.RelationshipSideChoices.SIDE_SOURCE:
                value = [v for v in value if v.source_id == record.id]
            else:
                value = [v for v in value if v.destination_id == record.id]

        # Handle Symmetric Relationships
        # List `value` could be empty here [] after the filtering from above
        if len(value) < 1:
            return "—"

        # Handle Relationships on the many side.
        if self.relationship.has_many(self.peer_side):
            v = value[0]
            meta = type(v.get_peer(record))._meta
            name = meta.verbose_name_plural if len(value) > 1 else meta.verbose_name
            return format_html(
                '<a href="{}?relationship={}&{}_id={}">{} {}</a>',
                reverse("extras:relationshipassociation_list"),
                self.relationship.key,
                self.side,
                record.id,
                len(value),
                name,
            )
        # Handle Relationships on the one side.
        else:
            v = value[0]
            peer = v.get_peer(record)
            return format_html('<a href="{}">{}</a>', peer.get_absolute_url(), peer)
