"""The controls one condition row is edited with.

A control is one form field of a row, with the widget that renders it. Not `field`, which in a
condition already means the model field being compared. Which widget a parameter gets follows from
the field it names and the operator it compares with.

Nothing here validates. The row's value is the JSON the `conditions` field holds, checked on save by
`validate_conditions`. What that refuses is put back on the controls as the form's own errors, so the
editor shows it the way every other Nautobot form shows a refusal.
"""

from dataclasses import dataclass, replace
import json

from django import forms
from django.core.exceptions import NON_FIELD_ERRORS
from django.forms.utils import ErrorDict
from django.urls import reverse

from nautobot.core.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot.core.forms.utils import add_blank_choice
from nautobot.core.forms.widgets import (
    APISelect,
    APISelectMultiple,
    ColorSelect,
    ColorSelectMultiple,
    DatePicker,
    MultiValueCharInput,
    StaticSelect2,
)
from nautobot.extras.choices import ConditionTypeChoices
from nautobot.extras.conditions.operators import (
    DISPLAY_KEY,
    KIND_BOOLEAN,
    KIND_DATE,
    KIND_LIST,
    KIND_NUMBER,
    KIND_TEXT,
    OPERATOR_REGISTRY,
    operators_for_kind,
    takes_a_set,
)
from nautobot.extras.conditions.presets import (
    get_condition_preset,
    get_condition_presets,
    PARAM_KIND_CHOICE,
    PARAM_KIND_FIELD,
)
from nautobot.extras.conditions.validation import row_errors

# What the type select calls a row holding a raw expression rather than a preset.
EXPRESSION_LABEL = "Raw expression"

# Both words carry a value, because Select2 takes a blank-valued option for its placeholder, which
# greys it out and drops it from the list, leaving nothing to choose to go back to.
NEGATION_CHOICES = (("when", "When"), ("not", "not When"))

# Said by the field select while the rule watches nothing, there being no fields to offer yet.
PROMPT_FOR_OBJECT_TYPES = "Select object type(s) first"

# The controls every row has, as against the ones its chosen type brings.
CONTROLS_EVERY_ROW_HAS = ("type", "negate")

# What a rendered control says about itself. `ui/src/js/conditions-editor.js` reads these back, so a
# role renamed on this side alone leaves rows written with a piece missing, and nothing complains.
ROLE_ATTR = "data-nb-condition-role"
KEY_ATTR = "data-nb-condition-key"
CAST_ATTR = "data-nb-condition-cast"

# Where a control's answer lands in the stored row. `PATH`, `SUBFIELD` and `VALUE` go inside `values`,
# a path being the two selects joined by a dot. `TYPE`, `NEGATE` and `SOURCE` are keys of the row itself.
ROLE_TYPE = "type"
ROLE_NEGATE = "negate"
ROLE_SOURCE = "source"
ROLE_PATH = "path"
ROLE_SUBFIELD = "subfield"
ROLE_VALUE = "value"

# Asked for where the row must hold a real boolean rather than the string a select carries.
CAST_BOOLEAN = "boolean"


@dataclass(frozen=True)
class ComparedField:
    """The field a row compares, and how the operator compares it.

    `kind` is one of the value kinds `operators` declares, such as `text` or `date`. `picker` names a
    form control the field asks for whatever its kind. `values_url` is where the related objects can
    be listed and `key` is the sub-field compared against them, both set only for a relation's
    sub-field. `whole` and `many` are settled by `compared_with`.
    """

    kind: str | None = None
    picker: str | None = None
    values_url: str | None = None
    key: str | None = None
    whole: bool = True
    many: bool = False

    def compared_with(self, operator):
        """The same field, with the two flags only the operator decides.

        `whole` is a comparison against a complete value rather than part of one, `many` one against a
        set. `operator` is an `operators.Operator`, or None where the row has not named one yet, which
        counts as one whole value. A list overrides `compares_whole_value`, because every operator it
        offers compares a whole value.
        """
        return replace(
            self,
            whole=operator is None or operator.compares_whole_value or self.kind == KIND_LIST,
            many=bool(operator and self.kind and takes_a_set(operator.key, self.kind)),
        )

    @staticmethod
    def for_path(addressable, name, subname):
        """The field a dotted path such as `status.name` names, or an empty one when it names nothing.

        Args:
            addressable (list): `addressable_fields` for the watched models. Each entry is a dict
                with a `name`, and perhaps `kind`, `widget`, `values_url` and `subfields`.
            name (str): The half of the path before the dot, a field every watched model carries.
            subname (str): The half after the dot, a subfield of that field's relation, or empty.
        """
        top = next((entry for entry in addressable if entry["name"] == name), None)
        if top is None:
            return ComparedField()
        if not subname:
            values_can_be_listed = top.get("kind") == KIND_LIST and top.get("values_url")
            return ComparedField(
                kind=top.get("kind"),
                picker=top.get("picker"),
                values_url=top["values_url"] if values_can_be_listed else None,
                key=DISPLAY_KEY if values_can_be_listed else None,
            )
        sub = next((entry for entry in top.get("subfields", ()) if entry["name"] == subname), None)
        if sub is None:
            return ComparedField()
        return ComparedField(
            kind=sub.get("kind"), picker=sub.get("picker"), values_url=top.get("values_url"), key=sub["name"]
        )

    @property
    def values_worth_listing(self):
        """Whether to offer the values themselves instead of a box to type one into.

        Either a sub-field of a single relation, `status.name`, or a many-valued relation named on
        its own, `tags`. A sub-field that is a date or a number gets the widget its kind asks for,
        and a partial comparison such as `contains` on text wants typing rather than picking.
        """
        return bool(self.values_url and self.key and self.whole and self.kind in (None, KIND_TEXT, KIND_LIST))


def _subfield_name(name):
    """The second of the two selects a field parameter is edited through."""
    return f"{name}_subfield"


def _parameter_of_kind(preset, kind):
    return next((parameter for parameter in preset.parameters if parameter.kind == kind), None)


def _options_for_chosen_values(value):
    """Options for a select filled by script, without which a stored value renders as nothing."""
    if value in (None, "", []):
        return []
    values = value if isinstance(value, (list, tuple)) else [value]
    return [(item, item) for item in values]


def _name_choices(entries):
    """Field names as a select offers them. The name is the path a condition stores, so it is the label."""
    return add_blank_choice((entry["name"], entry["name"]) for entry in entries)


def _subfield_choices(subfields):
    """Sub-field names, with no blank among them.

    A path that stops at a relation addresses a mapping, which nothing a condition compares can equal,
    so there is no such thing as a relation with no sub-field chosen. `name` leads where there is one,
    being what a reader of a change record recognises the related object by.
    """
    names = [entry["name"] for entry in subfields]
    ordered = ["name", *(name for name in names if name != "name")] if "name" in names else names
    return [(name, name) for name in ordered]


def _condition_type_choices():
    """Every preset the catalog offers, plus the raw expression a row may hold instead of one."""
    return add_blank_choice(
        [
            *((preset.key, preset.label) for preset in get_condition_presets()),
            (ConditionTypeChoices.TYPE_EXPRESSION, EXPRESSION_LABEL),
        ]
    )


def _apply_bootstrap_styling(widget, placeholder=""):
    """Give a widget the Bootstrap class and placeholder, which `BootstrapMixin` cannot reach here.

    It dresses the fields a form declares, and a row's are built after it has run.
    """
    classes = widget.attrs.get("class", "").split()
    if "form-control" not in classes:
        classes.append("form-control")
    widget.attrs["class"] = " ".join(classes)
    if placeholder:
        # A select takes `data-placeholder`: `initializeSelect2Fields` overwrites the real one.
        widget.attrs.setdefault("data-placeholder" if isinstance(widget, forms.Select) else "placeholder", placeholder)
    return widget


def _attrs_to_refetch_row(index):
    """What makes a control fetch its row again when it is changed.

    On every control that needs them, because `inc/javascript.html` sets `disableInheritance`.
    """
    return {
        "hx-get": reverse("extras:condition_row"),
        "hx-trigger": "change",
        "hx-target": "closest .nb-condition",
        "hx-swap": "outerHTML",
        "hx-include": "closest .nb-condition, #id_content_types",
        "hx-vals": json.dumps({"index": index}),
    }


def _mark_for_editor_script(widget, role, *, key=None, rebuild_index=None):
    """Say what a control holds, and for one that changes the rest of the row, which row to fetch again."""
    widget.attrs[ROLE_ATTR] = role
    if key:
        widget.attrs[KEY_ATTR] = key
    if rebuild_index is not None:
        widget.attrs.update(_attrs_to_refetch_row(rebuild_index))
    return widget


def _build_control(label, widget, *, placeholder=None):
    """Build a form field around `widget`. A `CharField` throughout, since nothing here validates.

    The `help_text` field for the parameter was intentionally omitted.
    Parameters in the row are stacked vertically,so a sentence placed beneath each one
    would double the row height by repeating the label content.
    """
    return forms.CharField(
        label=label,
        required=False,
        widget=_apply_bootstrap_styling(widget, label if placeholder is None else placeholder),
    )


def _build_operator_control(parameter, kind):
    """The operator select, narrowed to what the named field's kind can be compared with."""
    allowed = {operator.key for operator in operators_for_kind(kind)}
    offered = [
        (value, label) for value, label in parameter.choices if value not in OPERATOR_REGISTRY or value in allowed
    ]
    return _build_control(parameter.label, StaticSelect2(choices=add_blank_choice(offered)))


def _build_boolean_select():
    """The Yes or No select every other Nautobot form uses. The cast tells the browser to write a boolean."""
    return StaticSelect2(
        choices=BOOLEAN_WITH_BLANK_CHOICES,
        attrs={CAST_ATTR: CAST_BOOLEAN},
    )


# The control a value gets from the kind of the field it is compared with, once nothing more specific
# about that field applies. Mirrors `model_fields.KIND_BY_SERIALIZER_FIELD`, which settles the kind in the first place.
WIDGET_BY_FIELD_KIND = {
    KIND_BOOLEAN: _build_boolean_select,
    KIND_NUMBER: lambda: forms.NumberInput(attrs={"step": "any"}),
    KIND_DATE: DatePicker,
}


def _build_api_select(compared_field, value):
    """A select filled from the API. Its options' value is the key the condition compares, not the id."""
    select = (APISelectMultiple if compared_field.many else APISelect)(
        api_url=compared_field.values_url, choices=_options_for_chosen_values(value)
    )
    select.attrs.update({"value-field": compared_field.key, "display-field": compared_field.key})
    return select


def _build_value_control(parameter, compared_field, value):
    """The control for a value compared against `compared_field`, most specific thing known about it first."""
    return _build_control(parameter.label, _widget_for_value(compared_field, value))


def _widget_for_value(compared_field, value):
    if compared_field.picker == "color" and compared_field.whole:
        return ColorSelectMultiple() if compared_field.many else ColorSelect()
    if compared_field.values_worth_listing:
        return _build_api_select(compared_field, value)
    if compared_field.many:
        return MultiValueCharInput(choices=_options_for_chosen_values(value))
    return WIDGET_BY_FIELD_KIND.get(compared_field.kind, forms.TextInput)()


def _without_stale_values(data, prefix, triggered_by):
    """The request's data, minus what naming a different field has made meaningless.

    `triggered_by` is the control the browser changed, which HTMX sends as `HX-Trigger-Name`.
    """
    if data is None or triggered_by is None:
        return data
    preset = get_condition_preset(data.get(f"{prefix}-type"))
    if preset is None:
        return data
    named = _parameter_of_kind(preset, PARAM_KIND_FIELD)
    if named is None:
        return data
    field_control = f"{prefix}-{named.name}"
    subfield_control = f"{prefix}-{_subfield_name(named.name)}"
    if triggered_by not in (field_control, subfield_control):
        return data
    data = data.copy()
    for parameter in preset.parameters:
        if parameter.kind not in (PARAM_KIND_FIELD, PARAM_KIND_CHOICE):
            data.pop(f"{prefix}-{parameter.name}", None)
    if triggered_by == field_control:
        data.pop(subfield_control, None)
    return data


def _stored_row_as_initial(row):
    """A stored row as a form's initial values. A dotted field path becomes the two selects that edit it."""
    if not row:
        return {}
    negation = "not" if row.get("negate") else "when"
    if row.get("type") == ConditionTypeChoices.TYPE_EXPRESSION:
        return {
            "type": ConditionTypeChoices.TYPE_EXPRESSION,
            "negate": negation,
            "source": row.get("source", ""),
        }
    initial = {"type": row.get("preset") or "", "negate": negation}
    preset = get_condition_preset(row.get("preset"))
    if preset is None:
        return initial
    # Whatever the JSON tab holds, down to the values of a single row, is typed by hand and may be
    # anything at all. A row that cannot be spread renders empty and is refused on save.
    values = row.get("values")
    values = values if isinstance(values, dict) else {}
    for parameter in preset.parameters:
        value = values.get(parameter.name)
        if parameter.kind == PARAM_KIND_FIELD and isinstance(value, str) and "." in value:
            initial[parameter.name], _, initial[_subfield_name(parameter.name)] = value.partition(".")
        else:
            initial[parameter.name] = value
    return initial


def errors_by_row_and_control(rows):
    """What a save would refuse about the stored condition rows, keyed by row and then by the control.

    The same complaints `validate_conditions` reports, so the editor cannot reach a different verdict.
    A complaint naming no parameter is the row's own, and is keyed by `NON_FIELD_ERRORS`.

    Args:
        rows (list): The `conditions` field as stored, a list of condition row mappings.
    """
    errors = {}
    for index, error in row_errors(rows).items():
        by_control = {}
        for message in error.error_list:
            params = getattr(message, "params", None) or {}
            control = params.get("parameter") or params.get("key") or NON_FIELD_ERRORS
            by_control.setdefault(control, []).extend(message.messages)
        errors[index] = by_control
    return errors


class ConditionRowForm(forms.Form):
    """The controls for one condition row.

    Which controls exist depends on what the row names, so they are built here rather than declared: a
    row naming nothing holds only the type select, a raw expression adds `source`, and a preset adds one
    control per parameter it declares, a field parameter adding a second when it names a relation.

    Args:
        data: The values a rebuild carries, prefixed as this form renders them.
        index (int): The row's position. It prefixes every control, and it is what a validation error
            names when it reports which row is at fault.
        addressable (list): `addressable_fields` for the object types the rule watches.
        row (dict): The stored row, for the first render, when no `data` has been sent yet.
        errors (dict): What a save would refuse about this row, keyed by the control to blame.
        triggered_by (str): The control the browser changed, which decides what is no longer meant.
    """

    def __init__(self, data=None, *, index, addressable=(), row=None, errors=None, triggered_by=None):
        prefix = f"condition-{index}"
        super().__init__(
            data=_without_stale_values(data, prefix, triggered_by), prefix=prefix, initial=_stored_row_as_initial(row)
        )
        self.index = index
        self.addressable = list(addressable)
        # The form shows what a save would refuse rather than deciding it, so it never cleans itself.
        # Its errors are put in by hand, which needs the two places cleaning would otherwise fill.
        self.cleaned_data = {}
        self._errors = ErrorDict(renderer=self.renderer)
        self.fields["type"] = _build_control(
            "Condition type",
            _mark_for_editor_script(StaticSelect2(choices=_condition_type_choices()), ROLE_TYPE, rebuild_index=index),
        )
        # The row reads as a sentence, so negation opens it rather than hiding in a box at the end.
        self.fields["negate"] = _build_control(
            "Negate",
            _mark_for_editor_script(StaticSelect2(choices=NEGATION_CHOICES), ROLE_NEGATE),
            placeholder="",
        )
        self._add_chosen_controls(self._current_value("type"))
        chosen = set(self._chosen_control_names)
        for name, messages in (errors or {}).items():
            # Only a parameter control carries its own complaint. One about the type, or about a control
            # the row no longer brings, has nowhere to sit, so the row says it on their behalf.
            self.add_error(name if name in chosen else NON_FIELD_ERRORS, messages)

    @property
    def parameter_controls(self):
        """The controls the chosen type brought, as against the two every row has."""
        return [self[name] for name in self._chosen_control_names]

    @property
    def _chosen_control_names(self):
        return [name for name in self.fields if name not in CONTROLS_EVERY_ROW_HAS]

    def _current_value(self, name):
        """The value this row carries for one control, from the request or from `initial`.

        Read before any control exists, so `BoundField.value()` is not available yet.
        """
        if not self.is_bound:
            return self.initial.get(name, "")
        key = self.add_prefix(name)
        held = self.data.getlist(key) if hasattr(self.data, "getlist") else [self.data.get(key, "")]
        if len(held) > 1:
            return held
        return held[0] if held else ""

    def _add_chosen_controls(self, chosen):
        """The controls the chosen type brings, beyond the two every row has."""
        if chosen == ConditionTypeChoices.TYPE_EXPRESSION:
            self.fields["source"] = _build_control(
                "Expression",
                _mark_for_editor_script(forms.TextInput(), ROLE_SOURCE),
                placeholder="Jinja2 expression",
            )
            return
        preset = get_condition_preset(chosen)
        if preset is None:
            return
        compared_field = self._field_this_row_compares(preset)
        for parameter in preset.parameters:
            if parameter.kind == PARAM_KIND_FIELD:
                self._add_field_controls(parameter)
            elif parameter.kind == PARAM_KIND_CHOICE:
                # The operator decides whether the value is typed or picked, so it fetches the row again.
                control = _build_operator_control(parameter, compared_field.kind)
                _mark_for_editor_script(control.widget, ROLE_VALUE, key=parameter.name, rebuild_index=self.index)
                self.fields[parameter.name] = control
            else:
                control = _build_value_control(parameter, compared_field, self._current_value(parameter.name))
                _mark_for_editor_script(control.widget, ROLE_VALUE, key=parameter.name)
                self.fields[parameter.name] = control

    def _add_field_controls(self, parameter):
        """The field select, and a sub-field select when what it names is a relation."""
        if not self.addressable:
            closed = StaticSelect2(choices=[("", PROMPT_FOR_OBJECT_TYPES)], attrs={"disabled": True})
            self.fields[parameter.name] = _build_control(
                parameter.label,
                _mark_for_editor_script(closed, ROLE_PATH, key=parameter.name),
                placeholder="",
            )
            return

        control = _build_control(parameter.label, StaticSelect2(choices=_name_choices(self.addressable)))
        _mark_for_editor_script(control.widget, ROLE_PATH, key=parameter.name, rebuild_index=self.index)
        self.fields[parameter.name] = control

        subfields = self._subfields_of(self._current_value(parameter.name))
        if subfields:
            choices = _subfield_choices(subfields)
            name = _subfield_name(parameter.name)
            self.fields[name] = _build_control(
                "Sub-field",
                _mark_for_editor_script(
                    StaticSelect2(choices=choices),
                    ROLE_SUBFIELD,
                    key=parameter.name,
                    rebuild_index=self.index,
                ),
                placeholder="",
            )
            # So the rendered select marks the one it is sending as chosen, rather than leaving the
            # browser to fall back to the first and the two to disagree about what the row holds.
            if self._current_value(name) not in dict(choices):
                self.initial[name] = choices[0][0]
                if self.is_bound:
                    self.data = self.data.copy()
                    self.data[self.add_prefix(name)] = choices[0][0]

    def _subfields_of(self, name):
        entry = next((entry for entry in self.addressable if entry["name"] == name), None)
        return entry.get("subfields", ()) if entry else ()

    def _field_this_row_compares(self, preset):
        """The field this row names, as the operator it names sees it. Neither decides alone."""
        named = _parameter_of_kind(preset, PARAM_KIND_FIELD)
        compared_field = (
            ComparedField()
            if named is None
            else ComparedField.for_path(
                self.addressable,
                self._current_value(named.name),
                self._current_value(_subfield_name(named.name)),
            )
        )
        compares_with = _parameter_of_kind(preset, PARAM_KIND_CHOICE)
        operator_key = self._current_value(compares_with.name) if compares_with else None
        operator = OPERATOR_REGISTRY.get(operator_key) if isinstance(operator_key, str) else None
        return compared_field.compared_with(operator)
