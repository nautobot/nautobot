"""The controls one condition row is edited with.

A *control* is one editable box in a row.

Which control a parameter gets follows from what the row already names: the kind of the field it
addresses and the operator it compares with. That rule lives here, beside the tables it reads, so the
browser does not have to carry a second copy of it.

Nothing here validates. A row's canonical value is the JSON the `conditions` field holds, and
`validate_conditions` checks that on save.
"""

from dataclasses import dataclass, replace
import json

from django import forms
from django.urls import reverse

from nautobot.core.forms.utils import add_blank_choice
from nautobot.core.forms.widgets import (
    APISelect,
    APISelectMultiple,
    ColorSelect,
    DatePicker,
    MultiValueCharInput,
    StaticSelect2,
)
from nautobot.extras.choices import ConditionTypeChoices
from nautobot.extras.conditions.operators import (
    KIND_BOOLEAN,
    KIND_DATE,
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
from nautobot.extras.conditions.validation import row_problems

# What the type select calls a row holding a raw expression rather than a preset.
EXPRESSION_LABEL = "Raw expression"

# The two words a row can open with. Blank is "when", which is also how an un-negated row is stored.
NEGATION_DEFAULT = "When"
NEGATION_CHOICES = (("", NEGATION_DEFAULT), ("not", "When not"))

# Said by the field select while the rule watches nothing, there being no fields to offer yet.
PROMPT_FOR_OBJECT_TYPES = "Select object type(s) first"

# The controls every row has, as against the ones its chosen type brings.
CONTROLS_EVERY_ROW_HAS = ("type", "negate")

# What a rendered control says about itself. `project-static/js/conditions_editor.js` reads these back
# to rebuild the stored JSON, so the two files are one contract: rename a role on this side only and the
# browser writes rows with a piece missing, saying nothing. `data-condition-index` completes the set,
# written by hand in `extras/inc/conditions_row.html`, which is the one place it appears.
ROLE_ATTR = "data-condition-role"
KEY_ATTR = "data-condition-key"
CAST_ATTR = "data-condition-cast"

# A control's part in the row. `PATH` and `SUBFIELD` are the two halves of a field path, joined by a
# dot when the row is written; `VALUE` is a parameter the preset declares; the rest are the row's own.
ROLE_TYPE = "type"
ROLE_NEGATE = "negate"
ROLE_SOURCE = "source"
ROLE_PATH = "path"
ROLE_SUBFIELD = "subfield"
ROLE_VALUE = "value"

# Asked for where the row must hold a real boolean rather than the string a select carries.
CAST_BOOLEAN = "boolean"


class ColorSelectMultiple(ColorSelect, forms.SelectMultiple):
    """`ColorSelect` for an operator that compares against several colors at once."""


@dataclass(frozen=True)
class Target:
    """The field a row addresses, as far as choosing a control for its value goes.

    `values_url` and `key` are set only for a sub-field of a relation, being where the objects on the
    other side are listed and which of their keys the condition compares.
    """

    kind: str | None = None
    widget: str | None = None
    values_url: str | None = None
    key: str | None = None
    whole: bool = True
    many: bool = False

    def compared_with(self, operator):
        """The same field, with `whole` and `many` settled by the operator that compares it.

        `whole` is why a fragment match offers no list: the values that exist are no help when what is
        matched is a piece of one. `many` is why a set operator offers several at once. A preset with no
        operator of its own keeps the defaults, which are one whole value.
        """
        return replace(
            self,
            whole=operator is None or operator.compares_whole_value,
            many=bool(operator and self.kind and takes_a_set(operator.key, self.kind)),
        )

    @staticmethod
    def for_path(addressable, name, subname):
        """What a field path names among `addressable`, or an empty target when it names nothing."""
        top = next((entry for entry in addressable if entry["name"] == name), None)
        if top is None:
            return Target()
        if not subname:
            return Target(kind=top.get("kind"), widget=top.get("widget"))
        sub = next((entry for entry in top.get("subfields", ()) if entry["name"] == subname), None)
        if sub is None:
            return Target()
        return Target(kind=sub.get("kind"), widget=sub.get("widget"), values_url=top.get("values_url"), key=sub["name"])

    @property
    def values_worth_listing(self):
        """Whether the values this field already holds are worth offering as a list.

        Only a sub-field of a relation has somewhere to read them from, and only one that reads as a
        label is helped by seeing them. A date wants a calendar and a number a number box, however many
        of each the objects on the other side happen to carry.
        """
        return bool(self.values_url and self.key and self.whole and self.kind in (None, KIND_TEXT))


def _subfield_name(name):
    """The second of the two selects a field parameter is edited through.

    Internal to this form. The script pairs a path with its sub-field through `data-condition-key`,
    never through this name.
    """
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


def _condition_type_choices():
    """Every preset the catalog offers, plus the raw expression a row may hold instead of one."""
    return add_blank_choice(
        [
            *((preset.key, preset.label) for preset in get_condition_presets()),
            (ConditionTypeChoices.TYPE_EXPRESSION, EXPRESSION_LABEL),
        ]
    )


def _apply_bootstrap_styling(widget, placeholder=""):
    """Give a widget the Bootstrap class and placeholder `BootstrapMixin` gives every other form here.

    The mixin dresses the fields a form declares, and a row's are built after it has run, so it never
    sees them. A select takes `data-placeholder` rather than the real one, because
    `initializeSelect2Fields` overwrites that with `---------`. The editor reads ours from there.
    """
    classes = widget.attrs.get("class", "").split()
    if "form-control" not in classes:
        classes.append("form-control")
    widget.attrs["class"] = " ".join(classes)
    if placeholder:
        widget.attrs.setdefault("data-placeholder" if isinstance(widget, forms.Select) else "placeholder", placeholder)
    return widget


def _attrs_to_refetch_row(index):
    """What makes a control fetch its row again when it is changed.

    Spelled out on every control that needs them rather than once on the row: `disableInheritance` is
    set in `inc/javascript.html`, so nothing is picked up from an ancestor.
    """
    return {
        "hx-get": reverse("extras:condition_row"),
        "hx-trigger": "change",
        "hx-target": "closest tr",
        "hx-swap": "outerHTML",
        "hx-include": "closest tr, #id_content_types",
        "hx-vals": json.dumps({"index": index}),
    }


def _mark_for_editor_script(widget, role, *, key=None, rebuild=None):
    """Say what a control holds, so the browser can read the row back out of it.

    `role` is what the row does with the value: `path` and `subfield` are the two halves of a field
    path, `value` is a preset parameter, and `type`, `negate` and `source` are the row's own. `rebuild`
    is the row's index, given only for a control whose value decides which controls follow it.
    """
    widget.attrs[ROLE_ATTR] = role
    if key:
        widget.attrs[KEY_ATTR] = key
    if rebuild is not None:
        widget.attrs.update(_attrs_to_refetch_row(rebuild))
    return widget


def _build_control(label, widget, *, help_text="", placeholder=None):
    """Build a form field around `widget`, always a `CharField` because the widget is the point of it.

    Nothing here validates, so no field needs a type of its own. The help text is hung on the control
    as a tooltip as well: a stacked row gives each parameter one line, and a paragraph under every one
    of them would undo that.
    """
    if help_text:
        widget.attrs.setdefault("title", help_text)
    return forms.CharField(
        label=label,
        help_text=help_text,
        required=False,
        widget=_apply_bootstrap_styling(widget, label if placeholder is None else placeholder),
    )


def _build_parameter_control(parameter, widget):
    return _build_control(parameter.label, widget, help_text=parameter.help_text)


def _build_operator_control(parameter, kind):
    """The operator select, narrowed to what the named field's kind can be compared with.

    The parameter declares the choices and the operator table only takes away, so an operator the table
    does not describe stays on offer, as does everything when no kind is known.
    """
    allowed = {operator.key for operator in operators_for_kind(kind)}
    offered = [
        (value, label) for value, label in parameter.choices if value not in OPERATOR_REGISTRY or value in allowed
    ]
    return _build_parameter_control(parameter, StaticSelect2(choices=add_blank_choice(offered)))


def _build_boolean_select():
    """A true or false select that asks the browser for a real boolean.

    `_equals` compares a boolean field only against a real boolean, never against the string a select
    carries, so the cast happens before the row is written.
    """
    return StaticSelect2(
        choices=add_blank_choice((("true", "true"), ("false", "false"))),
        attrs={CAST_ATTR: CAST_BOOLEAN},
    )


# The control a value gets from the kind of the field it is compared with, once nothing more specific
# about that field applies. Mirrors `model_fields.KIND_BY_SERIALIZER_FIELD`, which settles the kind in the first place.
WIDGET_BY_FIELD_KIND = {
    KIND_BOOLEAN: _build_boolean_select,
    KIND_NUMBER: forms.NumberInput,
    KIND_DATE: DatePicker,
}


def _build_api_select(target, value):
    """A select filled from the API. Its options' value is the key the condition compares, not the id."""
    select = (APISelectMultiple if target.many else APISelect)(
        api_url=target.values_url, choices=_options_for_chosen_values(value)
    )
    select.attrs.update({"value-field": target.key, "display-field": target.key})
    return select


def _build_value_control(parameter, target, value):
    """The control for a value compared against `target`, the most specific thing known about it first.

    A field carrying a widget of its own beats one whose values can be listed, which beats an operator
    taking several at once, which beats the kind of field it is on its own.
    """
    if target.widget == "color" and target.whole:
        return _build_parameter_control(parameter, ColorSelectMultiple() if target.many else ColorSelect())
    if target.values_worth_listing:
        return _build_parameter_control(parameter, _build_api_select(target, value))
    if target.many:
        return _build_parameter_control(parameter, MultiValueCharInput(choices=_options_for_chosen_values(value)))
    return _build_parameter_control(parameter, WIDGET_BY_FIELD_KIND.get(target.kind, forms.TextInput)())


def _without_stale_values(data, prefix, triggered_by):
    """The request's data, minus what naming a different field has made meaningless.

    A value compared against `status.name` says nothing once the row names `mtu` instead, so the
    controls holding one are emptied rather than carried over. Naming a different field empties the
    sub-field as well, that one having belonged to the relation just replaced. `triggered_by` is the
    control the browser changed, which HTMX sends as `HX-Trigger-Name`.
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
    negation = "not" if row.get("negate") else ""
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


def faults_by_row_and_control(rows):
    """What a save would refuse about each row, keyed by its position and then by the control to blame.

    A complaint names the parameter or the row key at fault, and a control is named after whichever of
    those it edits, so the two meet without either side guessing. The complaints are the ones
    `validate_conditions` reports, so the editor cannot reach a different verdict than the save will.
    """
    faults = {}
    for index, error in row_problems(rows).items():
        by_control = {}
        for problem in error.error_list:
            params = getattr(problem, "params", None) or {}
            control = params.get("parameter") or params.get("key")
            by_control.setdefault(control, []).extend(problem.messages)
        faults[index] = by_control
    return faults


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
        faults (dict): What a save would refuse about this row, keyed by the control at fault.
        triggered_by (str): The control the browser changed, which decides what is no longer meant.
    """

    def __init__(self, data=None, *, index, addressable=(), row=None, faults=None, triggered_by=None):
        prefix = f"condition-{index}"
        super().__init__(
            data=_without_stale_values(data, prefix, triggered_by), prefix=prefix, initial=_stored_row_as_initial(row)
        )
        self.index = index
        self.addressable = list(addressable)
        self.faults = dict(faults or {})
        self.fields["type"] = _build_control(
            "Condition type",
            _mark_for_editor_script(StaticSelect2(choices=_condition_type_choices()), ROLE_TYPE, rebuild=index),
        )
        # The row reads as a sentence, so negation opens it rather than hiding in a box at the end.
        self.fields["negate"] = _build_control(
            "Negate",
            _mark_for_editor_script(StaticSelect2(choices=NEGATION_CHOICES), ROLE_NEGATE),
            placeholder=NEGATION_DEFAULT,
        )
        self._add_chosen_controls(self._current_value("type"))
        self._flag_faults()

    @property
    def parameter_controls(self):
        """The controls the chosen type brought with it, each with what a save would refuse about it.

        A layout arranges these. Which ones there are is settled above, so a change of layout is a change
        of template alone.
        """
        return [(self[name], self.faults.get(name, ())) for name in self._chosen_control_names]

    @property
    def row_faults(self):
        """The faults no parameter control can carry, so that none goes unsaid.

        A row is refused over its type, or over its values as a whole, as readily as over one parameter,
        and neither of those has a control of its own to sit under.
        """
        placed = set(self._chosen_control_names)
        return [message for name, messages in self.faults.items() if name not in placed for message in messages]

    @property
    def _chosen_control_names(self):
        return [name for name in self.fields if name not in CONTROLS_EVERY_ROW_HAS]

    def _flag_faults(self):
        """Mark every control a fault names, so it is red before its message is read, and announced.

        `aria-describedby` is set here rather than left to Django, which builds it from the field's own
        errors, and a fault is not one of those: it comes from a save that was refused, not from this
        form cleaning itself. Both ids go in, because Django would otherwise have put the help text
        there and an id nothing points at is announced as nothing.
        """
        for name in self.faults:
            if name not in self.fields:
                continue
            field = self.fields[name]
            described = [f"{self.auto_id % self.add_prefix(name)}_error"]
            if field.help_text:
                described.insert(0, f"{self.auto_id % self.add_prefix(name)}_helptext")
            field.widget.attrs["class"] = f"{field.widget.attrs.get('class', '')} is-invalid".strip()
            field.widget.attrs["aria-invalid"] = "true"
            field.widget.attrs["aria-describedby"] = " ".join(described)

    def _current_value(self, name):
        """The value this row already carries for one control.

        Read before any control exists, because which ones exist depends on these values, so Django's
        `BoundField.value()` is not available yet. A rebuild carries them in the request, a first render
        in `initial`. Several come back as a list, `QueryDict.get` keeping only the last of them.
        """
        if not self.is_bound:
            return self.initial.get(name, "")
        key = self.add_prefix(name)
        held = self.data.getlist(key) if hasattr(self.data, "getlist") else [self.data.get(key, "")]
        if len(held) > 1:
            return held
        return held[0] if held else ""

    def _add_chosen_controls(self, chosen):
        """The controls the chosen type brings, beyond the two every row has.

        A raw expression brings one. A preset brings one per parameter it declares, and the field and
        the operator among them are read first, because they settle what the rest of them look like.
        """
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
        target = self._target_this_row_compares(preset)
        for parameter in preset.parameters:
            if parameter.kind == PARAM_KIND_FIELD:
                self._add_field_controls(parameter)
            elif parameter.kind == PARAM_KIND_CHOICE:
                # The operator decides whether the value is typed or picked, so it fetches the row again.
                control = _build_operator_control(parameter, target.kind)
                _mark_for_editor_script(control.widget, ROLE_VALUE, key=parameter.name, rebuild=self.index)
                self.fields[parameter.name] = control
            else:
                control = _build_value_control(parameter, target, self._current_value(parameter.name))
                _mark_for_editor_script(control.widget, ROLE_VALUE, key=parameter.name)
                self.fields[parameter.name] = control

    def _add_field_controls(self, parameter):
        """The field select, and a sub-field select when what it names is a relation.

        Until an object type is chosen there is nothing to name, so the select says so and is closed
        rather than offered empty. Being disabled, it never fires the change that would rebuild the row.
        """
        if not self.addressable:
            closed = StaticSelect2(choices=[("", PROMPT_FOR_OBJECT_TYPES)], attrs={"disabled": True})
            self.fields[parameter.name] = _build_control(
                parameter.label,
                _mark_for_editor_script(closed, ROLE_PATH, key=parameter.name),
                help_text=parameter.help_text,
                placeholder="",
            )
            return

        control = _build_parameter_control(parameter, StaticSelect2(choices=_name_choices(self.addressable)))
        _mark_for_editor_script(control.widget, ROLE_PATH, key=parameter.name, rebuild=self.index)
        self.fields[parameter.name] = control

        subfields = self._subfields_of(self._current_value(parameter.name))
        if subfields:
            self.fields[_subfield_name(parameter.name)] = _build_control(
                "Sub-field",
                _mark_for_editor_script(
                    StaticSelect2(choices=_name_choices(subfields)),
                    ROLE_SUBFIELD,
                    key=parameter.name,
                    rebuild=self.index,
                ),
            )

    def _subfields_of(self, name):
        entry = next((entry for entry in self.addressable if entry["name"] == name), None)
        return entry.get("subfields", ()) if entry else ()

    def _target_this_row_compares(self, preset):
        """The field this row names, as the operator it names sees it.

        Neither half answers anything alone. The field says what kind of value is being compared and
        where its own values can be read, the operator says whole or fragment and one or several, and
        only the two together decide what the value control is.
        """
        named = _parameter_of_kind(preset, PARAM_KIND_FIELD)
        target = (
            Target()
            if named is None
            else Target.for_path(
                self.addressable,
                self._current_value(named.name),
                self._current_value(_subfield_name(named.name)),
            )
        )
        compares_with = _parameter_of_kind(preset, PARAM_KIND_CHOICE)
        operator = OPERATOR_REGISTRY.get(self._current_value(compares_with.name)) if compares_with else None
        return target.compared_with(operator)
