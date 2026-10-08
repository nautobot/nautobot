from collections.abc import Iterable
import json
from urllib.parse import urljoin

from django import forms
from django.forms.models import ModelChoiceIterator
from django.urls import get_script_prefix, reverse
from django.utils.html import format_html, format_html_join

from nautobot.core import choices as core_choices
from nautobot.core.forms import utils

__all__ = (
    "APISelect",
    "APISelectMultiple",
    "AutoPopulateWidget",
    "BulkEditNullBooleanSelect",
    "ClearableFileInput",
    "ColorSelect",
    "ColorSelectMultiple",
    "ContentTypeSelect",
    "DatePicker",
    "DateTimePicker",
    "ExportFieldSelect",
    "NumberWithSelect",
    "SelectMultipleOrderable",
    "SelectWithDisabled",
    "SelectWithPK",
    "SlugWidget",
    "SmallTextarea",
    "StaticSelect2",
    "StaticSelect2Multiple",
    "TimePicker",
)


class SmallTextarea(forms.Textarea):
    """
    Subclass used for rendering a smaller textarea element.
    """


class SlugWidget(forms.TextInput):
    """
    Subclass TextInput and add a slug regeneration button next to the form field.
    """

    template_name = "widgets/sluginput.html"

    def get_context(self, name, value, attrs):
        custom_title = self.attrs.pop("title", None)
        context = super().get_context(name, value, attrs)
        context["widget"]["custom_title"] = custom_title
        return context


class AutoPopulateWidget(SlugWidget):
    """
    Subclass SlugWidget and add support for auto-populate JavaScript logic from `form.js`.
    """

    def get_context(self, name, value, attrs):
        attrs["data-autopopulate"] = ""
        context = super().get_context(name, value, attrs)
        return context


class ColorSelect(forms.Select):
    """
    Extends the built-in Select widget to colorize each <option>.
    """

    option_template_name = "widgets/colorselect_option.html"

    def __init__(self, *args, **kwargs):
        kwargs["choices"] = utils.add_blank_choice(core_choices.ColorChoices)
        super().__init__(*args, **kwargs)
        self.attrs["class"] = "nautobot-select2-color-picker"


class ColorSelectMultiple(ColorSelect, forms.SelectMultiple):
    """
    `ColorSelect` for a field that holds several colors at once.
    """


class BulkEditNullBooleanSelect(forms.NullBooleanSelect):
    """
    A Select widget for NullBooleanFields
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Override the built-in choice labels
        self.choices = (
            ("1", "—"),
            ("2", "Yes"),
            ("3", "No"),
        )
        self.attrs["class"] = "nautobot-select2-static"


class SelectMultipleOrderable(forms.SelectMultiple):
    """
    Modified the stock SelectMultiple widget to render a set of controls with draggable list group rows to enable
    ordering and checkboxes to simplify the selection process.
    """

    template_name = "widgets/select_multiple_orderable.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.attrs["class"] = (
            "list-group nb-draggable-container nb-select-multiple-orderable-list flex-grow-1 mx-n20 py-16"
        )


class ExportFieldSelect(SelectMultipleOrderable):
    """
    `SelectMultipleOrderable` variant that nests each field path under the path it belongs to.

    Top-level fields are draggable/orderable rows; nested paths (e.g. `device_type__manufacturer__name`, or a
    `cf_<key>` under `custom_fields`) are rendered as indented, collapsible checkboxes inside their parent
    row, so reordering a parent moves its nested columns with it and nested columns are not independently
    orderable. The submitted order is therefore the order of the top-level rows, which is what the export
    lays its columns out in.

    A row with rows nested under it is a tri-state control over them rather than a field of its own, and
    submits nothing: it is checked when everything under it is, and indeterminate when some of it is. Clicking
    a related object's row steps through its natural key, then everything, then nothing, or straight to
    everything from any other partial selection. Its natural key is the rows that make it up where the tree
    offers them (see `natural_keys`), and otherwise a "Natural key" option of its own, nested first under it,
    which submits the bare path (see `whole_options`; `custom_fields` has such an option too, "All custom
    fields"). Any other row with rows under it selects everything, then nothing.

    `parent_paths` maps each value to the value it nests under; `ExportFieldsChoiceField` sets it from
    `enumerate_field_paths()`. Without it, nesting falls back to the dunder structure of the path itself.

    The markup is built in Python rather than via a template: the field tree can hold hundreds of nodes,
    and a recursive per-node ``{% include %}`` is instrumented per render by dev tooling (debug-toolbar),
    turning a ~25ms render into many seconds. Building the HTML directly keeps it fast in every environment.
    """

    # The ids and the selector below are also used by the UI bundle's `export-fields.js`; keep them in step.

    # The element the picker is rebuilt into. `render_field` emits it around the whole field from the
    # field's `htmx_attrs`, and it persists across swaps -- so it is what a rebuild targets, and it is
    # where the URL to rebuild from is carried. See `ExportFieldsStringVar.as_field()`.
    WRAPPER_ID = "nb-export-fields-picker"

    # The report of what a "match the list view" could not bring over. One per picker, hence an id.
    OMITTED_ID = "nb-export-fields-omitted"

    # What the selection amounts to, above the tree. One per picker, hence an id.
    SUMMARY_ID = "nb-export-fields-summary"

    # The sibling field naming the content type whose fields are offered; changing it rebuilds the picker.
    content_type_selector = "#id_content_type"
    # The fields whose values the "match the list view" button sends along, being what says *which* list
    # view is meant: the content type, and the query string that view was showing.
    context_field_selector = "#id_content_type, #id_query_string"

    def __init__(self, *args, parent_paths=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_paths = parent_paths or {}
        # Columns of the list view that had no exportable equivalent, reported by whoever seeded the
        # selection from a view, so the picker can say what was left out rather than quietly dropping it.
        self.omitted_columns = []
        # Set when a "match the list view" found no list view to match, there being content types with no
        # list view at all (`users.token`, `users.user`). Without it the button appears to do nothing.
        self.no_list_view = False
        # The content type whose fields are offered, for the sake of saying which one has none.
        self.content_type = None
        # For each row that may also be selected as a whole, the label, description and icon of the option that
        # does so; see `ExportFieldPath.whole_label`.
        self.whole_options = {}
        # For each related object whose natural key is made of rows the tree offers, those rows: what the first
        # click on its row selects. See `ExportFieldPath.natural_key`.
        self.natural_keys = {}
        # Paths a selection may name that the tree has no row for, each with the rows it is shown as instead.
        self.substitutions = {}
        # Fit the standard modal form column: drop the table-config drawer's negative side margins and
        # flex-grow so the list aligns with the other fields rather than bleeding to the far left.
        # `list-unstyled` removes the <ol> numbering (the drawer only hid it via negative margins).
        # `nb-export-field-select` is what the UI bundle's `export-fields.js`, the tree's behavior, looks for.
        self.attrs["class"] = (
            "list-group list-unstyled nb-draggable-container nb-select-multiple-orderable-list nb-export-field-select "
            "py-8"
        )

    def parent_of(self, path):
        """The value `path` nests under, or None if it is a top-level row."""
        if path in self.parent_paths:
            return self.parent_paths[path]
        return path.rsplit("__", 1)[0] if "__" in path else None

    @staticmethod
    def flatten_paths(value):
        """A selection as a flat list of paths, however it was spelled.

        A browser posts one value per checked box, but every other way of setting this field sends the
        comma-separated string the export itself takes -- the list view's modal seeds it through `hx-vals`,
        a URL query populates it through `normalize_querydict()`, and the REST API and
        `nautobot-server export_objects` pass it straight through. Those arrive as a *single-element list
        holding the whole string*, so splitting only a bare `str` is not enough: unsplit, the string
        matches no field and the selection silently comes out empty.
        """
        if not value:
            return []
        if isinstance(value, str):
            value = [value]
        return [path.strip() for entry in value for path in str(entry).split(",") if path.strip()]

    def value_from_datadict(self, data, files, name):
        """The submitted selection, in submitted (drag) order."""
        return self.flatten_paths(super().value_from_datadict(data, files, name))

    def format_value(self, value):
        """The selection being rendered, as flat paths with `substitutions` applied, so the right boxes are checked."""
        shown = []
        for path in self.flatten_paths(value):
            shown.extend(entry for entry in self.substitutions.get(path, [path]) if entry not in shown)
        return shown

    def render(self, name, value, attrs=None, renderer=None):
        context = super().get_context(name, value, attrs)
        widget = context["widget"]
        options = [option for _group, subgroup, _index in widget["optgroups"] for option in subgroup]

        if not options:
            # Say why there is nothing to pick from, rather than rendering an empty list under two
            # buttons that cannot do anything.
            return format_html('<div class="form-text">{}</div>', self._empty_message())

        nodes = {str(option["value"]): {"option": option, "children": []} for option in options}
        roots = []
        for path, node in nodes.items():
            parent = nodes.get(self.parent_of(path))
            # A path whose parent is not itself offered is rendered as a top-level row rather than dropped,
            # so a selection seeded with something the enumeration does not reach is still visible.
            (parent["children"] if parent is not None else roots).append(node)

        widget_id = widget["attrs"].get("id") or ""
        rows = format_html_join("", "{}", ((self._render_node(node, widget_id, name, True),) for node in roots))
        # No wrapper of its own: the whole picker is replaced at once when it has to be rebuilt
        # server-side, and the element that persists across those swaps is the one `render_field` puts
        # around the field from `htmx_attrs` (`WRAPPER_ID`). This is that element's contents. Its behavior
        # is the UI bundle's `export-fields.js`, which also works out the parent rows' states whenever a
        # picker is loaded -- "indeterminate" having no markup of its own.
        return format_html(
            '{}{}<ol id="{}" class="{}">{}</ol>',
            self._toolbar(selected_count=len(widget["value"])),
            self._omitted_hint() or self._no_list_view_hint(),
            widget_id,
            widget["attrs"].get("class") or "",
            rows,
        )

    def _toolbar(self, selected_count=0):
        """The picker's controls, what the selection currently amounts to, and how to use the tree.

        "Match the list view" puts what that view is displaying *into* the picker, to be seen, reordered
        and pruned before the export runs. It is a gesture rather than an input to the export: a caller
        with no picker -- the REST API, a scheduled Job -- names the fields it wants instead.

        "Clear" is the way back to the default columns, that being what an empty selection exports. It is
        disabled while there is nothing to clear.
        """
        has_selection = selected_count > 0
        # The `hx-params="not ...."` blocks inheriting the named hx-vals from the enclosing form.
        # This is needed because `hx-vals` inheritance is not affected by `htmx.config.disableInheritance = true` in
        # HTMX 2.0 -- see https://github.com/bigskysoftware/htmx/issues/1119
        buttons = format_html(
            """
            <div class="d-flex justify-content-start mb-6">
                <button type="button" class="btn btn-secondary"
                        hx-get="{url}" hx-target="#{wrapper}" hx-swap="innerHTML" hx-include="{include}"
                        hx-params="not job_modal_button,job_form_modal,job_result_key,run_button_label,refresh_on_close_if_done,advanced_fields,_schedule_type"
                        hx-vals='{{"use_current_view": "1", "content_type": "{content_type}"}}'
                        title="Replace the selection with the columns this type's list view is configured to display"
                ><span class="mdi mdi-table-eye me-4" aria-hidden="true"></span>Match the list view</button>
                <button type="button" class="btn btn-secondary ms-6 nb-export-fields-clear"{disabled}
                        title="Clear the selection, to export the default columns instead"
                ><span class="mdi mdi-close me-4" aria-hidden="true"></span>Clear</button>
            </div>
            """,
            url=reverse("export_fields_picker"),
            wrapper=self.WRAPPER_ID,
            disabled=format_html(" disabled") if not has_selection else "",
            include=self.context_field_selector,
            content_type=self.content_type.pk,
        )
        # Inline text, so joined without a break: a newline here would be a space in the output.
        legend = format_html(
            '<span class="form-text d-block mb-6">'
            "Drag to reorder fields.<br>"
            '"*" marks a field an import requires to create new records.<br>'
            "Checking a related object selects the fields that identify it (its natural key); checking it again "
            "selects all of its fields, and again clears them. "
            '"<span aria-hidden="true" class="text-info mdi mdi-chevron-down"></span>'
            '<span class="visually-hidden">show/hide related fields</span>" shows its fields, to choose '
            "them individually."
            "</span>"
        )
        return format_html("{}{}{}", buttons, self._summary(selected_count), legend)

    def _summary(self, selected_count):
        """What the export will contain: the default columns if nothing is selected, else the selected count.

        Shown above the tree, in place of the field's help text below it (see `ExportFieldsStringVar.as_field()`).
        Both versions are rendered; `export-fields.js` in the UI bundle shows whichever applies. They share one grid
        cell (`.nb-stacked`) and are hidden by `visibility` rather than `display`, so the summary keeps the height of
        the longer of them and the tree below does not move as the selection starts or empties. A screen reader is
        told only the short status as the selection changes, rather than the whole summary on every click.
        """
        model = self.content_type.model_class() if self.content_type is not None else None
        verbose_name = model._meta.verbose_name if model is not None else "object"
        return format_html(
            """
            <div id="{id}" class="form-text mb-6">
                <span class="nb-export-fields-summary-status visually-hidden" aria-live="polite">{status}</span>
                <div class="nb-stacked">
                    <div class="nb-export-fields-summary-default{default_hidden}">
                        <strong>No fields selected</strong><br>
                        The export has the default columns: each field of the {verbose_name} itself, with related
                        objects given as the fields that identify them, and any custom fields. Computed fields,
                        relationships, and similar opt-in data are not exported.
                    </div>
                    <div class="nb-export-fields-summary-selected{selected_hidden}">
                        <strong><span class="nb-export-fields-summary-count">{count}</span> selected</strong><br>
                        They are exported in the order shown. Clear the selection to export the default columns
                        instead.
                    </div>
                </div>
                <div>Export Templates and devicetype-library YAML exports ignore the selection.</div>
            </div>
            """,
            id=self.SUMMARY_ID,
            default_hidden=" invisible" if selected_count else "",
            selected_hidden="" if selected_count else " invisible",
            verbose_name=verbose_name,
            count=selected_count,
            status=f"{selected_count} selected" if selected_count else "No fields selected",
        )

    def _empty_message(self):
        """Why there is nothing to pick from: no content type chosen, or one an export cannot serialize."""
        if self.content_type is None:
            return format_html("Choose a content type to see the fields you can export.")
        return format_html(
            "This content type has no fields an export can select. It can still be exported using an "
            "Export Template, which renders its own output."
        )

    def _omitted_hint(self):
        """What the launching view was showing that an export cannot emit, named rather than dropped."""
        if not self.omitted_columns:
            return ""
        # Addressable so that clearing the selection can take it away with it: what it reports is what a
        # particular "match the list view" could not bring over, which says nothing once that is gone.
        return format_html(
            '<div id="{}" class="form-text text-warning mb-6">Table column{} {} {} no direct equivalent and {} left out.</div>',
            self.OMITTED_ID,
            "" if len(self.omitted_columns) == 1 else "s",
            format_html_join(", ", "<code>{}</code>", ((column,) for column in self.omitted_columns)),
            "has" if len(self.omitted_columns) == 1 else "have",
            "was" if len(self.omitted_columns) == 1 else "were",
        )

    def _no_list_view_hint(self):
        """Said when a "match the list view" had no list view to match, rather than leaving it silent.

        Shares `OMITTED_ID` with `_omitted_hint()` -- the two cannot both apply, and the id is what lets
        clearing the selection take the report away with it.
        """
        if not self.no_list_view:
            return ""
        return format_html(
            '<div id="{}" class="form-text text-info mb-6">'
            "This content type has no list view, so there are no displayed columns to match. "
            "Choose the fields to export below, or leave the selection empty to export the default columns."
            "</div>",
            self.OMITTED_ID,
        )

    @staticmethod
    def _checkbox(control, control_id, label, path, is_root, title=None):
        """A row's checkbox `control` with its label, and the path it selects alongside."""
        return format_html(
            '<div class="form-check flex-grow-1 my-0">{control}'
            '<label class="form-check-label py-6{pe}" for="{control_id}"{title}>{label}'
            '<span class="font-monospace small text-secondary ms-6">{path}</span></label>'
            "</div>",
            control=control,
            control_id=control_id,
            pe="" if is_root else " pe-20",
            title=format_html(' title="{}"', title) if title else "",
            label=label,
            path=path,
        )

    def _whole_option(self, path, widget_id, name, selected):
        """The first row nested under `path`, selecting it as a whole -- "Natural key", say -- by submitting `path`."""
        label, description, icon = self.whole_options[path]
        control_id = f"{widget_id}_whole_{path}"
        control = format_html(
            '<input class="form-check-input my-6 nb-export-field-leaf nb-export-field-whole" id="{}" name="{}" '
            'type="checkbox" value="{}" data-label="{}"{}>',
            control_id,
            name,
            path,
            label,
            format_html(" checked") if selected else "",
        )
        return format_html(
            '<li class="my-0 nb-export-field-node"><div class="d-flex align-items-center">{}</div></li>',
            self._checkbox(
                control,
                control_id,
                # The icon only marks what the label already says, so it is hidden from screen readers.
                format_html('{}<span class="mdi {} text-warning ms-4" aria-hidden="true"></span>', label, icon)
                if icon
                else label,
                path,
                is_root=False,
                title=description,
            ),
        )

    def _render_node(self, node, widget_id, name, is_root):
        """One row, and the rows nested under it."""
        option = node["option"]
        value = str(option["value"])
        has_children = bool(node["children"])
        selected = bool(option["attrs"].get("selected"))
        handle = (
            format_html(
                '<span class="nb-draggable-handle pt-4 px-10"><span class="mdi mdi-drag-vertical text-secondary"></span></span>'
            )
            if is_root
            else ""
        )
        if not has_children:
            control = format_html(
                '<input class="form-check-input my-6 nb-export-field-leaf" id="{}_option_{}" name="{}" '
                'type="checkbox" value="{}"{}>',
                widget_id,
                value,
                name,
                value,
                format_html(" checked") if selected else "",
            )
        else:
            # A control over what is nested under it, with no value of its own to submit.
            control = format_html(
                '<input class="form-check-input my-6 nb-export-field-parent" id="{}_option_{}" type="checkbox"{}>',
                widget_id,
                value,
                format_html(' data-natural-key="{}"', json.dumps(self.natural_keys[value]))
                if value in self.natural_keys
                else "",
            )
        checkbox = self._checkbox(control, f"{widget_id}_option_{value}", option["label"], value, is_root)
        # Filled in by `export-fields.js` in the UI bundle, being a count of what is checked at the moment. It is
        # what says what a collapsed row holds, every row starting collapsed: expanding each that holds part
        # of a selection -- as a "match the list view" can make many -- would bury the tree.
        count = format_html('<span class="nb-export-field-count small text-secondary text-nowrap ms-6"></span>')
        caret = (
            format_html(
                '<button type="button" class="btn btn-link btn-sm p-0 ms-auto pe-10 nb-export-field-caret" '
                'aria-expanded="false" title="Show/hide related fields">'
                '<span class="mdi mdi-chevron-down" aria-hidden="true"></span></button>'
            )
            if has_children
            else ""
        )
        header = format_html(
            '<div class="d-flex align-items-center">{}{}{}{}</div>',
            handle,
            checkbox,
            count if has_children else "",
            caret,
        )

        nested = ""
        if has_children:
            children = format_html_join(
                "", "{}", ((self._render_node(child, widget_id, name, False),) for child in node["children"])
            )
            if value in self.whole_options:
                children = format_html("{}{}", self._whole_option(value, widget_id, name, selected), children)
            # First nested level clears the drag handle and parent checkbox; deeper levels compound. See
            # `.nb-export-nested` in the stylesheet.
            nested = format_html(
                '<ul class="nb-export-nested{} list-unstyled mb-0 d-none">{}</ul>',
                " nb-export-nested-root" if is_root else "",
                children,
            )

        if is_root:
            return format_html(
                '<li class="list-group-item-action nb-draggable my-0 nb-export-field-group" '
                'id="{}_option_{}_container" tabindex="0">{}{}</li>',
                widget_id,
                value,
                header,
                nested,
            )
        return format_html('<li class="my-0 nb-export-field-node">{}{}</li>', header, nested)


class SelectWithDisabled(forms.Select):
    """
    Modified the stock Select widget to accept choices using a dict() for a label. The dict for each option must include
    'label' (string) and 'disabled' (boolean).
    """

    option_template_name = "widgets/selectwithdisabled_option.html"


class StaticSelect2(SelectWithDisabled):
    """
    A static <select> form widget using the Select2 library.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.attrs["class"] = "nautobot-select2-static"


class StaticSelect2Multiple(StaticSelect2, forms.SelectMultiple):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.attrs["data-multiple"] = 1


class SelectWithPK(StaticSelect2):
    """
    Include the primary key of each option in the option label (e.g. "Router7 (4721)").
    """

    option_template_name = "widgets/select_option_with_pk.html"


class ContentTypeSelect(StaticSelect2):
    """
    Appends an `api-value` attribute equal to the slugified model name for each ContentType. For example:
        <option value="37" api-value="console-server-port">console server port</option>
    This attribute can be used to reference the relevant API endpoint for a particular ContentType.
    """

    option_template_name = "widgets/select_contenttype.html"


class MinimalModelChoiceIterator(ModelChoiceIterator):
    """
    Helper class for APISelect and APISelectMultiple.

    Allows the widget to keep a full `queryset` for data validation, but, for performance reasons, returns a minimal
    subset of choices at render time derived from the widget's `data_queryset`.
    """

    @property
    def queryset(self):
        return self.field.data_queryset

    @queryset.setter
    def queryset(self, value):
        return self.field.data_queryset


class APISelect(SelectWithDisabled):
    """
    A select widget populated via an API call

    Args:
        api_url (str): API endpoint URL. Required if not set automatically by the parent field.
        api_version (str): API version.
    """

    def __init__(self, api_url=None, full=False, api_version=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.attrs["class"] = "nautobot-select2-api"

        if api_version:
            # Set Request Accept Header api-version e.g Accept: application/json; version=1.2
            self.attrs["data-api-version"] = api_version

        if api_url:
            # Prefix the URL w/ the script prefix (e.g. `/nautobot`)
            self.attrs["data-url"] = urljoin(get_script_prefix(), api_url.lstrip("/"))

    def add_query_param(self, name, value):
        """
        Add details for an additional query param in the form of a data-* JSON-encoded list attribute.

        Args:
            name (str): The name of the query param
            value (Any): The value of the query param
        """
        key = f"data-query-param-{name}"

        values = json.loads(self.attrs.get(key, "[]"))
        if isinstance(value, (list, tuple)):
            values.extend([str(v) for v in value])
        else:
            values.append(str(value))

        self.attrs[key] = json.dumps(values, ensure_ascii=False)

    def get_context(self, name, value, attrs):
        # This adds null options to DynamicModelMultipleChoiceField selected choices
        # example <select ..>
        #           <option .. selected value="null">None</option>
        #           <option .. selected value="1234-455...">Rack 001</option>
        #           <option .. value="1234-455...">Rack 002</option>
        #          </select>
        # Prepend null choice to self.choices if
        # 1. form field allow null_option e.g. DynamicModelMultipleChoiceField(..., null_option="None"..)
        # 2. if null is part of url query parameter for name(field_name) i.e. http://.../?rack_id=null
        # 3. if both value and choices are iterable
        if (
            self.attrs.get("data-null-option")
            and isinstance(value, (list, tuple))
            and "null" in value
            and isinstance(self.choices, Iterable)
        ):

            class ModelChoiceIteratorWithNullOption(MinimalModelChoiceIterator):
                def __init__(self, *args, **kwargs):
                    self.null_options = kwargs.pop("null_option", None)
                    super().__init__(*args, **kwargs)

                def __iter__(self):
                    # ModelChoiceIterator.__iter__() yields a tuple of (value, label)
                    # using this approach first yield a tuple of (null(value), null_option(label))
                    yield "null", self.null_options
                    yield from super().__iter__()

            null_option = self.attrs.get("data-null-option")
            self.choices = ModelChoiceIteratorWithNullOption(field=self.choices.field, null_option=null_option)

        return super().get_context(name, value, attrs)


class APISelectMultiple(APISelect, forms.SelectMultiple):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.attrs["data-multiple"] = 1


class DatePicker(forms.TextInput):
    """
    Date picker using Flatpickr.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs["class"] = "date-picker"
        self.attrs["placeholder"] = "YYYY-MM-DD"


class DateTimePicker(forms.TextInput):
    """
    DateTime picker using Flatpickr.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs["class"] = "datetime-picker"
        self.attrs["placeholder"] = "YYYY-MM-DD hh:mm:ss"


class TimePicker(forms.TextInput):
    """
    Time picker using Flatpickr.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs["class"] = "time-picker"
        self.attrs["placeholder"] = "hh:mm:ss"


class MultiValueCharInput(StaticSelect2Multiple):
    """
    Manual text input with tagging enabled.
    Press enter to create a new entry.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs["class"] = "nautobot-select2-multi-value-char"


class ClearableFileInput(forms.ClearableFileInput):
    template_name = "widgets/clearable_file.html"


class NumberWithSelect(forms.NumberInput):
    template_name = "widgets/number_input_with_choices.html"

    def __init__(self, choices=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if choices is None:
            self.choices = []
        elif hasattr(choices, "CHOICES"):
            self.choices = core_choices.unpack_grouped_choices(choices.CHOICES)
        else:
            self.choices = core_choices.unpack_grouped_choices(choices)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["choices"] = self.choices
        return context
