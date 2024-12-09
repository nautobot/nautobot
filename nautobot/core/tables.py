import contextlib
import logging

from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import FieldDoesNotExist, FieldError
from django.db import NotSupportedError
from django.db.models import Prefetch
from django.db.models.fields.related import ForeignKey, RelatedField
from django.db.models.fields.reverse_related import ManyToOneRel
from django.urls import reverse
from django.utils.html import escape, format_html, format_html_join
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.utils.text import Truncator
import django_tables2
from django_tables2.data import TableData, TableQuerysetData
from django_tables2.rows import BoundRows
from django_tables2.utils import Accessor, OrderBy, OrderByTuple
from tree_queries.models import TreeNode

from nautobot.core.models.querysets import count_related
from nautobot.core.templatetags import helpers
from nautobot.core.utils.lookup import get_model_for_view_name, get_related_field_for_models, get_route_for_model
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

    def __init__(
        self,
        *args,
        table_changes_pending=False,
        saved_view=None,
        user=None,
        hide_hierarchy_ui=False,
        order_by=None,
        data_transform_callback=None,
        **kwargs,
    ):
        """
        Instantiate a BaseTable.

        Args:
            *args (list, optional): Passed through to django_tables2.Table
            table_changes_pending (bool): TODO
            saved_view (SavedView, optional): TODO
            user (User, optional): TODO
            hide_hierarchy_ui (bool): Whether to display or hide hierarchy indentation of nested objects.
            order_by (list, optional): Field(s) to sort by
            data_transform_callback (function, optional): A function that takes the given `data` as an input and
                returns new data. Runs after all of the queryset auto-optimization performed by this class.
                Used for example in IPAM views to inject "fake" records for "available" Prefixes, IPAddresses, or VLANs.
            **kwargs (dict, optional): Passed through to django_tables2.Table
        """
        # Add custom field columns
        model = self._meta.model

        if getattr(model, "is_dynamic_group_associable_model", False):
            self.base_columns["dynamic_group_count"] = LinkedCountColumn(
                viewname="extras:dynamicgroup_list",
                url_params={"member_id": "pk"},
                verbose_name="Dynamic Groups",
                reverse_lookup="static_group_associations__associated_object_id",
            )

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

        if order_by is None and saved_view is not None:
            order_by = saved_view.config.get("sort_order", None)

        # Init table
        super().__init__(*args, order_by=order_by, **kwargs)

        if not isinstance(self.data, TableQuerysetData):
            # LinkedCountColumns don't work properly if the data is a list of dicts instead of a queryset,
            # as they rely on a `queryset.annotate()` call to gather the data.
            self.exclude = [
                *self.exclude,
                *[column.name for column in self.columns if isinstance(column.column, LinkedCountColumn)],
            ]

        # Don't show hierarchy if we're sorted
        if order_by is not None and hide_hierarchy_ui is None:
            hide_hierarchy_ui = True

        self.hide_hierarchy_ui = hide_hierarchy_ui

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

        # Apply custom column ordering for SavedView if it is available
        # Takes precedence before user config
        columns = []
        pk = self.base_columns.pop("pk", None)
        actions = self.base_columns.pop("actions", None)
        if saved_view is not None and not table_changes_pending:
            view_table_config = saved_view.config.get("table_config", {}).get(f"{self.__class__.__name__}", None)
            if view_table_config is not None:
                columns = view_table_config.get("columns", [])
        else:
            if user is not None and not isinstance(user, AnonymousUser):
                columns = user.get_config(f"tables.{self.__class__.__name__}.columns")
        if columns:
            for name, column in self.base_columns.items():
                if name in columns and name not in self.exclude:
                    self.columns.show(name)
                else:
                    self.columns.hide(name)
            self.sequence = [c for c in columns if c in self.base_columns]

        # Always include PK and actions columns, if defined on the table, as first and last columns respectively
        if pk:
            with contextlib.suppress(ValueError):
                self.sequence.remove("pk")
            self.base_columns["pk"] = pk
            self.sequence.insert(0, "pk")
        if actions:
            with contextlib.suppress(ValueError):
                self.sequence.remove("actions")
            self.base_columns["actions"] = actions
            self.sequence.append("actions")

        # Dynamically update the table's QuerySet to ensure related fields are pre-fetched
        if isinstance(self.data, TableQuerysetData):
            queryset = self.data.data

            if hasattr(queryset, "with_tree_fields") and not self.hide_hierarchy_ui:
                queryset = queryset.with_tree_fields()
            elif hasattr(queryset, "without_tree_fields") and self.hide_hierarchy_ui:
                queryset = queryset.without_tree_fields()

            select_fields = []
            prefetch_fields = []
            count_fields = []
            for column in self.columns:
                if not column.visible:
                    continue
                if isinstance(column.column, LinkedCountColumn):
                    column_model = get_model_for_view_name(column.column.viewname)
                    if column_model is None:
                        logger.error("Couldn't find model for %s", column.column.viewname)
                        continue
                    reverse_lookup = column.column.reverse_lookup or next(iter(column.column.url_params.keys()))
                    distinct = column.column.distinct
                    count_fields.append((column.name, column_model, reverse_lookup, distinct))
                    try:
                        lookup = column.column.lookup or get_related_field_for_models(model, column_model).name
                        # For some reason get_related_field_for_models(Tag, DynamicGroup) gives a M2M with the name
                        # `dynamicgroup`, which isn't actually a field on Tag. May be a django-taggit issue?
                        # Workaround for now: make sure the field actually exists on the model under this name:
                        getattr(model, lookup)
                    except AttributeError:
                        lookup = None
                    if lookup is not None:
                        # Also attempt to prefetch the first matching record for display - see LinkedCountColumn
                        prefetch_fields.append(
                            # Use order_by() because we don't care about ordering here and it's potentially expensive
                            Prefetch(lookup, column_model.objects.order_by()[:1], to_attr=f"{lookup}_list")
                        )
                    continue

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
                    except (AttributeError, TypeError, ValueError, NotSupportedError) as exc:
                        logger.warning(
                            "Unexpected error when trying to .prefetch_related() on %s QuerySet: %s",
                            model.__name__,
                            exc,
                        )

            if count_fields:
                for column_name, column_model, lookup_name, distinct in count_fields:
                    if hasattr(queryset.first(), column_name):
                        continue
                    try:
                        logger.debug(
                            "Applying .annotate(%s=count_related(%s, %r, distinct=%s) to %s QuerySet",
                            column_name,
                            column_model.__name__,
                            lookup_name,
                            distinct,
                            model.__name__,
                        )
                        queryset = queryset.annotate(
                            **{column_name: count_related(column_model, lookup_name, distinct=distinct)}
                        )
                    except FieldError:
                        # No error message logged here as the above is *very much* best-effort
                        pass

            self.data.data = queryset

        # TODO: it would be better if we could apply this transformation and the above queryset optimizations
        #       **before** calling super().__init__(), but the current implementation works for now, though inelegant.
        if data_transform_callback is not None:
            self.data = TableData.from_data(data_transform_callback(self.data.data))
            self.data.set_table(self)
            self.rows = BoundRows(data=self.data, table=self, pinned_data=self.pinned_data)

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
        return [name for name in self.sequence if self.columns[name].visible and name not in self.exclude]

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
        changelog_route = get_route_for_model(model, "changelog")
        edit_route = get_route_for_model(model, "edit")
        delete_route = get_route_for_model(model, "delete")

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
    Render a count of related objects linked to a filtered URL, or if a single related object is present, the object.

    Args:
        viewname (str): The list view name to use for URL resolution, for example `"dcim:location_list"`
        url_params (dict, optional): Query parameters to apply to filter the list URL (e.g. `{"vlans": "pk"}` will add
            `?vlans=<record.pk>` to the linked list URL)
        view_kwargs (dict, optional): Additional kwargs to pass to `reverse()` for list URL resolution. Rarely used.
        lookup (str, optional): The field name on the base record that can be used to query the related objects.
            If not specified, `nautobot.core.utils.lookup.get_related_field_for_models()` will be called at render time
            to attempt to intelligently find the appropriate field.
            TODO: this currently does *not* support nested lookups via `__`. That may be solvable in the future.
        reverse_lookup (str, optional): The reverse lookup parameter to use to derive the count.
            If not specified, the first key in `url_params` will be implicitly used as the `reverse_lookup` value.
        distinct (bool, optional): Parameter passed through to `count_related()`.
        **kwargs (dict, optional): As the parent Column class.

    Examples:
        ```py
        class VLANTable(..., BaseTable):
            ...
            location_count = LinkedCountColumn(
                # Link for N related locations will be reverse("dcim:location_list") + "?vlans=<record.pk>"
                viewname="dcim:location_list",
                url_params={"vlans": "pk"},
                verbose_name="Locations",
            )
        ```

        ```py
        class CloudNetworkTable(BaseTable):
            ...
            circuit_count = LinkedCountColumn(
                # Link for N related circuits will be reverse("circuits:circuit_list") + "?cloud_network=<record.name>"
                viewname="circuits:circuit_list",
                url_params={"cloud_network": "name"},
                # We'd like to do the below but this module isn't currently smart enough to build the right Prefetch()
                # for a nested lookup:
                # lookup="circuit_terminations__circuit",
                # For the count,
                # .annotate(circuit_count=count_related(Circuit, "circuit_terminations__cloud_network", distinct=True))
                reverse_lookup="circuit_terminations__cloud_network",
                distinct=True,
                verbose_name="Circuits",
            )
        ```
    """

    def __init__(
        self,
        viewname,
        *args,
        view_kwargs=None,
        url_params=None,
        lookup=None,
        reverse_lookup=None,
        distinct=False,
        default=None,
        **kwargs,
    ):
        self.viewname = viewname
        self.lookup = lookup
        self.view_kwargs = view_kwargs or {}
        self.url_params = url_params
        self.reverse_lookup = reverse_lookup or next(iter(url_params.keys()))
        self.distinct = distinct
        self.model = get_model_for_view_name(self.viewname)
        super().__init__(*args, default=default, **kwargs)

    def render(self, bound_column, record, value):  # pylint: disable=arguments-differ
        related_record = None
        try:
            lookup = self.lookup or get_related_field_for_models(bound_column._table._meta.model, self.model).name
        except AttributeError:
            lookup = None
        if lookup:
            if related_records := getattr(record, f"{lookup}_list", None):
                related_record = related_records[0]
        url = reverse(self.viewname, kwargs=self.view_kwargs)
        if self.url_params:
            url += "?" + urlencode({k: getattr(record, v) for k, v in self.url_params.items()})
        if value > 1:
            return format_html('<a href="{}" class="badge">{}</a>', url, value)
        if related_record is not None:
            return helpers.hyperlinked_object(related_record)
        if value == 1:
            return format_html('<a href="{}" class="badge">{}</a>', url, value)
        return helpers.placeholder(value)


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
