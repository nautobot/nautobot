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


class BulkEditNullBooleanSelect(forms.NullBooleanSelect):
    """
    A Select widget for NullBooleanFields
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Override the built-in choice labels
        self.choices = (
            ("1", "---------"),
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

    Top-level fields are draggable/orderable rows; nested paths (e.g. `device_type__manufacturer`, or a
    `cf_<key>` under `custom_fields`) are rendered as indented, collapsible checkboxes inside their parent
    row, so reordering a parent moves its nested columns with it and nested columns are not independently
    orderable. The submitted order is therefore the order of the top-level rows, which is what the export
    lays its columns out in.

    `parent_paths` maps each value to the value it nests under; `ExportFieldsChoiceField` sets it from
    `enumerate_field_paths()`. Without it, nesting falls back to the dunder structure of the path itself.

    The markup is built in Python rather than via a template: the field tree can hold hundreds of nodes,
    and a recursive per-node ``{% include %}`` is instrumented per render by dev tooling (debug-toolbar),
    turning a ~25ms render into many seconds. Building the HTML directly keeps it fast in every environment.
    """

    # The element the picker is rebuilt into. `render_field` emits it around the whole field from the
    # field's `htmx_attrs`, and it persists across swaps -- so it is what a rebuild targets, and it is
    # where the URL to rebuild from is carried. See `ExportFieldsStringVar.as_field()`.
    WRAPPER_ID = "nb-export-fields-picker"

    # The report of what a "match the list view" could not bring over. One per picker, hence an id.
    OMITTED_ID = "nb-export-fields-omitted"

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
        # The content type whose fields are offered, for the sake of saying which one has none.
        self.content_type = None
        # The paths that name a related object rather than a value of the object being exported.
        self.relation_paths = set()
        # Fit the standard modal form column: drop the table-config drawer's negative side margins and
        # flex-grow so the list aligns with the other fields rather than bleeding to the far left.
        # `list-unstyled` removes the <ol> numbering (the drawer only hid it via negative margins).
        self.attrs["class"] = "list-group list-unstyled nb-draggable-container nb-select-multiple-orderable-list py-8"

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
        """The selection being rendered, so that the right boxes come out checked."""
        return self.flatten_paths(value)

    def render(self, name, value, attrs=None, renderer=None):
        context = super().get_context(name, value, attrs)
        widget = context["widget"]
        options = [option for _group, subgroup, _index in widget["optgroups"] for option in subgroup]

        if not options:
            # Say why there is nothing to pick from, rather than rendering an empty list under two
            # buttons that cannot do anything. The script still goes out: without it nothing bridges
            # Select2's pick to the `change` that rebuilds this, and a form opened with no content type
            # chosen -- which is how the Job's own form opens -- would never leave this state.
            return format_html('<div class="form-text">{}</div>{}', self._empty_message(), self._behavior_script())

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
        # around the field from `htmx_attrs` (`WRAPPER_ID`). This is that element's contents.
        return format_html(
            '{}{}<ol id="{}" class="{}">{}</ol>{}',
            self._toolbar(has_selection=bool(widget["value"])),
            self._omitted_hint(),
            widget_id,
            widget["attrs"].get("class") or "",
            rows,
            self._behavior_script(),
        )

    def _toolbar(self, has_selection=False):
        """The picker's controls: seeding the selection from the launching list view, and clearing it.

        "Match the list view" puts what that view is displaying *into* the picker, to be seen, reordered
        and pruned before the export runs. It is a gesture rather than an input to the export: a caller
        with no picker -- the REST API, a scheduled Job -- names the fields it wants instead.

        "Clear" is the way back to exporting every field, that being what an empty selection means. It is
        disabled while there is nothing to clear, so it also reads as whether anything is selected.
        """
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
                <button type="button" class="btn btn-secondary ms-6 export-fields-clear"{disabled}
                        title="Clear the selection, so that every field is exported again"
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
            '"<span aria-hidden="true" class="text-warning mdi mdi-key-link"></span>'
            '<span class="visually-hidden">natural key</span>" marks a related object, which when selected, '
            "exports the related field(s) that identify it.<br>"
            '"<span aria-hidden="true" class="text-info mdi mdi-chevron-down"></span>'
            '<span class="visually-hidden">show/hide related fields</span>" expands a related object row '
            "to select different related fields to export."
            "</span>"
        )
        return format_html("{}{}", buttons, legend)

    def _empty_message(self):
        """Why there is nothing to pick from: no content type chosen, or one an export cannot serialize."""
        if self.content_type is None:
            return format_html("Choose a content type to see the fields you can export.")
        return format_html(
            "This content type has no fields an export can select. It can still be exported using an "
            "Export Template, which renders its own output."
        )

    def _natural_key_marker(self, path):
        """Mark a row that names a related object, selecting which exports what identifies it.

        The checkbox on such a row is the one thing here that does not mean what a tree of checkboxes
        usually means: it asks for the columns that identify the related object -- its natural key --
        rather than for everything listed beneath it, and the two are mutually exclusive. The badge says
        so where the checkbox is, which is where the assumption gets made.

        Which columns those are is deliberately not spelled out: a natural key can span several fields
        and several relations, and `Location`'s is computed from how deeply locations are nested at the
        time, so any list of them would be long, particular to the deployment, and out of date the moment
        someone nests one deeper.
        """
        if path not in self.relation_paths:
            return ""
        # The same icon the import form marks a related object with, so that the two forms say the same
        # thing the same way; its meaning is spelled out in the legend, as it is there.
        return format_html(
            '<span class="text-warning ms-6" title="{}">'
            '<span aria-hidden="true" class="mdi mdi-key-link"></span>'
            '<span class="visually-hidden">natural key</span>'
            "</span>",
            "Exports the columns that identify this related object, rather than the fields listed under it",
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

    def _behavior_script(self):
        """The tree's own client-side behavior, shipped with the markup.

        Delegated from `document` and guarded by a flag, so that it binds once however many times a widget
        renders -- the export form is rendered both as a full page and, repeatedly, into the HTMX modal.
        Kept here rather than in a template or the JS bundle so that every renderer of the widget gets the
        behavior without having to include anything.

        Relationships are read from DOM nesting rather than from the `__` structure of the values, so a
        `cf_<key>` nested under `custom_fields` behaves like any other child despite sharing no prefix
        with it.
        """
        return format_html(
            """<script type="text/javascript">
(function () {{
    if (window.nbExportFieldSelectBound) return;
    window.nbExportFieldSelectBound = true;
    const LIST = ".nb-select-multiple-orderable-list";
    const boxesWithin = (element) => Array.from(element.querySelectorAll('input[type="checkbox"]'));

    document.addEventListener("change", function (event) {{
        const changed = event.target;
        if (!changed.matches(LIST + ' input[type="checkbox"]')) return;
        const list = changed.closest(LIST);
        const row = changed.closest("li");
        if (changed.checked && row) {{
            // A field and any field nested under it are mutually exclusive: selecting the parent asks for
            // its natural key (or, for `custom_fields`, every custom field), while selecting a descendant
            // asks for that column instead. Enforcing it keeps what is shown equal to what will export.
            boxesWithin(row).forEach((box) => {{
                if (box !== changed) box.checked = false;
            }});
            for (let ancestor = row.parentElement; ancestor && list.contains(ancestor); ancestor = ancestor.parentElement) {{
                if (ancestor.tagName !== "LI") continue;
                // A row's own checkbox is the first in its subtree, its header preceding any nested rows.
                const box = ancestor.querySelector('input[type="checkbox"]');
                if (box) box.checked = false;
            }}
        }}
        // A parent with a selected descendant but no selection of its own reads as "customized".
        boxesWithin(list).forEach((box) => {{
            const boxRow = box.closest("li");
            box.indeterminate =
                !box.checked && boxRow !== null && boxesWithin(boxRow).some((inner) => inner !== box && inner.checked);
        }});
        refreshClearButton(list);
    }});

    // Whether there is anything to clear is also whether anything is selected, so the button's state
    // doubles as that: an empty selection is what exports every field.
    function refreshClearButton(list) {{
        const picker = list.closest("#{wrapper}");
        const clear = picker ? picker.querySelector(".export-fields-clear") : null;
        if (clear) clear.disabled = !boxesWithin(list).some((box) => box.checked);
    }}

    document.addEventListener("click", function (event) {{
        const clear = event.target.closest(".export-fields-clear");
        if (!clear) return;
        const picker = clear.closest("#{wrapper}");
        const list = picker ? picker.querySelector(LIST) : null;
        if (!list) return;
        // Unchecking in script raises no "change" event, so the housekeeping the change handler would
        // have done -- the indeterminate marks, and this button's own state -- is done here.
        boxesWithin(list).forEach((box) => {{
            box.checked = false;
            box.indeterminate = false;
        }});
        // The columns a "match the list view" could not bring over are reported against that selection,
        // so the report goes with it. A later match renders its own afresh.
        const omitted = picker.querySelector("#{omitted}");
        if (omitted) omitted.remove();
        clear.disabled = true;
    }});

    // Collapse/expand a parent's nested columns, at any depth.
    document.addEventListener("click", function (event) {{
        const caret = event.target.closest(".export-field-caret");
        if (!caret || !caret.closest(LIST)) return;
        const row = caret.closest("li");
        const nested = row ? row.querySelector(":scope > .export-nested") : null;
        if (!nested) return;
        const collapsed = nested.classList.toggle("d-none");
        caret.setAttribute("aria-expanded", String(!collapsed));
        const icon = caret.querySelector(".mdi");
        if (icon) {{
            icon.classList.toggle("mdi-chevron-down", collapsed);
            icon.classList.toggle("mdi-chevron-up", !collapsed);
        }}
    }});

    // Select2 announces a pick with a jQuery event only, which nothing listening natively -- HTMX
    // included -- ever sees (https://github.com/select2/select2/issues/1908). Re-dispatch it as a real
    // `change` so the picker's own `hx-trigger` can hear it; `objectmetadata_create.html` bridges its
    // own select the same way. Delegated, so it survives the form being swapped into the modal.
    function bindSelect2ChangeBridge() {{
        if (!window.jQuery) return;
        window.jQuery(document).on("select2:select select2:clear", "{content_type_selector}", function () {{
            this.dispatchEvent(new Event("change", {{bubbles: true}}));
        }});
    }}
    // On a full page render this script runs while the document is still parsing, *before* the scripts at
    // the end of the body have defined jQuery -- so binding is deferred to whenever that has happened.
    // A widget swapped in by HTMX renders after page load, where jQuery is there already.
    if (window.jQuery) bindSelect2ChangeBridge();
    else document.addEventListener("DOMContentLoaded", bindSelect2ChangeBridge);
}})();
</script>""",
            content_type_selector=self.content_type_selector,
            wrapper=self.WRAPPER_ID,
            omitted=self.OMITTED_ID,
        )

    def _render_node(self, node, widget_id, name, is_root):
        option = node["option"]
        value = str(option["value"])
        has_children = bool(node["children"])
        checked = format_html(" checked") if option["attrs"].get("selected") else ""
        handle = (
            format_html(
                '<span class="nb-draggable-handle pt-4 px-10"><span class="mdi mdi-drag-vertical text-secondary"></span></span>'
            )
            if is_root
            else ""
        )
        checkbox = format_html(
            '<div class="form-check flex-grow-1 my-0">'
            '<input class="form-check-input my-6{natural_key}" id="{wid}_option_{value}" name="{name}" '
            'type="checkbox" value="{value}"{checked}>'
            '<label class="form-check-label py-6{pe}" for="{wid}_option_{value}">{label}{badge}</label>'
            "</div>",
            wid=widget_id,
            value=value,
            name=name,
            checked=checked,
            pe="" if is_root else " pe-20",
            label=option["label"],
            badge=self._natural_key_marker(value),
            # Checking a relation asks for the columns that identify it, not for everything listed under
            # it, so it is ticked with a key rather than a check -- see `nb-export-natural-key` in the
            # stylesheet. The tree offers no "everything under this" selection for the usual mark to mean.
            natural_key=" nb-export-natural-key" if value in self.relation_paths else "",
        )
        caret = (
            format_html(
                '<button type="button" class="btn btn-link btn-sm p-0 ms-auto pe-10 export-field-caret" '
                'aria-expanded="false" title="Show/hide related fields">'
                '<span class="mdi mdi-chevron-down" aria-hidden="true"></span></button>'
            )
            if has_children
            else ""
        )
        header = format_html('<div class="d-flex align-items-center">{}{}{}</div>', handle, checkbox, caret)

        nested = ""
        if has_children:
            children = format_html_join(
                "", "{}", ((self._render_node(child, widget_id, name, False),) for child in node["children"])
            )
            # First nested level clears the drag handle and parent checkbox; deeper levels compound.
            nested = format_html(
                '<ul class="export-nested list-unstyled mb-0 d-none" style="margin-left: {}">{}</ul>',
                "4.5rem" if is_root else "2rem",
                children,
            )

        if is_root:
            return format_html(
                '<li class="list-group-item-action nb-draggable my-0 export-field-group" '
                'id="{}_option_{}_container" tabindex="0">{}{}</li>',
                widget_id,
                value,
                header,
                nested,
            )
        return format_html('<li class="my-0 export-field-node">{}{}</li>', header, nested)


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
