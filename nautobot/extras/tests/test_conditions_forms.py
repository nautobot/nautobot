"""Tests for `nautobot.extras.conditions.forms`."""

from pathlib import Path

from django.conf import settings
from django.http import QueryDict
from django.test import SimpleTestCase, tag

from nautobot.core.forms.constants import BOOLEAN_CHOICES
from nautobot.core.forms.widgets import (
    APISelect,
    APISelectMultiple,
    ColorSelect,
    ColorSelectMultiple,
    DatePicker,
    MultiValueCharInput,
    StaticSelect2,
)
from nautobot.dcim.models import Interface
from nautobot.extras.conditions.forms import (
    _stored_row_as_initial,
    _subfield_name,
    _without_stale_values,
    CAST_ATTR,
    CAST_BOOLEAN,
    ComparedField,
    ConditionRowForm,
    errors_by_row_and_control,
    KEY_ATTR,
    PROMPT_FOR_OBJECT_TYPES,
    ROLE_ATTR,
    ROLE_NEGATE,
    ROLE_PATH,
    ROLE_SOURCE,
    ROLE_SUBFIELD,
    ROLE_TYPE,
    ROLE_VALUE,
)
from nautobot.extras.conditions.model_fields import addressable_fields
from nautobot.extras.conditions.operators import OPERATOR_REGISTRY
from nautobot.extras.conditions.presets import register_builtin_condition_presets


def compare(**values):
    """A `field_compare` row, the only preset carrying a field, an operator and a value at once."""
    return {"type": "preset", "preset": "field_compare", "values": values}


class RowFormTestCase(SimpleTestCase):
    """Rows are built against `Interface`, which carries a field of every kind the picker offers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        register_builtin_condition_presets()
        cls.addressable = addressable_fields(Interface)

    def form(self, row=None, **kwargs):
        return ConditionRowForm(index=0, addressable=self.addressable, row=row, **kwargs)

    def control_names(self, row):
        return [control.name for control in self.form(row).parameter_controls]

    def widget_for(self, name, row):
        return type(self.form(row).fields[name].widget)


@tag("unit")
class ControlsARowHoldsTest(RowFormTestCase):
    """The chosen type decides which controls exist, which is the first of the three inputs a row has."""

    def test_a_row_naming_nothing_holds_only_the_two_every_row_has(self):
        form = self.form()
        self.assertEqual(sorted(form.fields), ["negate", "type"])
        self.assertEqual(form.parameter_controls, [])

    def test_the_chosen_type_decides_which_controls_the_row_holds(self):
        for label, row, expected in (
            (
                "a raw expression carries its own source",
                {"type": "expression", "source": "event == 'updated'"},
                ["source"],
            ),
            (
                "`mtu` is a number on the interface itself, so nothing is nested under it",
                {"type": "preset", "preset": "field_changed", "values": {"field": "mtu"}},
                ["field"],
            ),
            (
                "`status` alone addresses a mapping, which no comparison matches, so the row asks further",
                {"type": "preset", "preset": "field_changed", "values": {"field": "status"}},
                ["field", "field_subfield"],
            ),
            (
                "a transition holds both ends of the change",
                {
                    "type": "preset",
                    "preset": "field_transition",
                    "values": {"field": "status.name", "from": "Staged", "to": "Active"},
                },
                ["field", "field_subfield", "from", "to"],
            ),
            (
                "a comparison holds an operator and a value",
                compare(field="status.name", operator="in", value=["Active"]),
                ["field", "field_subfield", "operator", "value"],
            ),
            (
                "a many-valued relation is compared whole, so it names no sub-field",
                compare(field="tags", operator="="),
                ["field", "operator", "value"],
            ),
            (
                "a preset naming no field holds only what it declares",
                {"type": "preset", "preset": "user_is", "values": {"username": "bot"}},
                ["username"],
            ),
            (
                "a preset this installation does not have renders bare rather than raising",
                {"type": "preset", "preset": "no_such_preset"},
                [],
            ),
        ):
            with self.subTest(label):
                self.assertEqual(self.control_names(row), expected)


@tag("unit")
class WidgetForValueTest(RowFormTestCase):
    """The field and the operator together decide the value control, and neither answers alone."""

    def test_the_field_and_the_operator_together_decide_the_value_control(self):
        for label, field, operator, expected in (
            ("a number", "mtu", "=", "NumberInput"),
            ("a date", "created", "=", DatePicker.__name__),
            ("a boolean", "enabled", "=", StaticSelect2.__name__),
            ("text", "description", "=", "TextInput"),
            ("the objects on the other side can be listed", "status.name", "=", APISelect.__name__),
            ("a set operator offers several of them", "status.name", "in", APISelectMultiple.__name__),
            (
                "`contains` matches a fragment, which no list of whole values helps with",
                "status.name",
                "contains",
                "TextInput",
            ),
            ("a colour is picked from the palette", "status.color", "=", ColorSelect.__name__),
            ("several colours at once", "status.color", "in", ColorSelectMultiple.__name__),
            ("a set on a field with nothing to list is typed", "mtu", "in", MultiValueCharInput.__name__),
            ("`=` on a list compares set against set, so it takes several", "tags", "=", APISelectMultiple.__name__),
            ("`contains` on a list takes one member of it", "tags", "contains", APISelect.__name__),
            (
                "a date sub-field wants a calendar, however many objects carry it",
                "role.last_updated",
                "=",
                DatePicker.__name__,
            ),
            ("a number sub-field wants a number box", "role.weight", "=", "NumberInput"),
        ):
            with self.subTest(label):
                widget = self.widget_for("value", compare(field=field, operator=operator))
                self.assertEqual(widget.__name__, expected)

    def test_a_number_takes_a_decimal(self):
        """Without `step` the browser defaults to whole numbers and blocks the save on, say, a latitude."""
        rendered = str(self.form(compare(field="mtu", operator="gt"))["value"])
        self.assertIn('step="any"', rendered)

    def test_a_number_is_offered_ordering_but_not_fragment_matching(self):
        offered = [value for value, _ in self.form(compare(field="mtu")).fields["operator"].widget.choices]
        for fragment_operator in ("contains", "startswith", "endswith"):
            with self.subTest(fragment_operator):
                self.assertNotIn(fragment_operator, offered)
        self.assertIn("gt", offered)

    def test_the_field_picker_is_closed_until_an_object_type_is_chosen(self):
        """Offered empty it would look broken. Disabled it also never fires the change that rebuilds the row."""
        form = ConditionRowForm(
            index=0, addressable=(), row={"type": "preset", "preset": "field_changed", "values": {}}
        )
        widget = form.fields["field"].widget
        self.assertTrue(widget.attrs.get("disabled"))
        self.assertEqual([label for _, label in widget.choices], [PROMPT_FOR_OBJECT_TYPES])
        self.assertNotIn("hx-get", widget.attrs)


@tag("unit")
class ComparedFieldTest(RowFormTestCase):
    """What a field path names, which is the second of the three inputs a row has."""

    def test_a_path_naming_nothing_is_empty(self):
        for path in (("no_such_field", ""), ("status", "no_such_sub_field")):
            with self.subTest(path):
                self.assertEqual(ComparedField.for_path(self.addressable, *path), ComparedField())

    def test_a_relation_alone_offers_no_values(self):
        compared_field = ComparedField.for_path(self.addressable, "status", "")
        self.assertIsNone(compared_field.key)
        self.assertIsNone(compared_field.values_url)

    def test_a_sub_field_carries_where_its_values_live_and_which_key_is_compared(self):
        compared_field = ComparedField.for_path(self.addressable, "status", "name")
        self.assertEqual(compared_field.kind, "text")
        self.assertEqual(compared_field.key, "name")
        self.assertIn("content_types=dcim.interface", compared_field.values_url)

    def test_a_many_valued_relation_is_picked_from_its_objects(self):
        """`tags` is compared whole, so the row names no sub-field and the select takes several tags."""
        compared_field = ComparedField.for_path(self.addressable, "tags", "").compared_with(OPERATOR_REGISTRY["="])
        self.assertEqual(compared_field.kind, "list")
        self.assertEqual(compared_field.key, "display")
        self.assertIn("content_types=dcim.interface", compared_field.values_url)
        self.assertTrue(compared_field.many)
        self.assertTrue(compared_field.values_worth_listing)

    def test_contains_takes_one_whole_member_of_a_list(self):
        """It matches a fragment of a string, but a whole member of a list, so the tags are offered."""
        compared_field = ComparedField.for_path(self.addressable, "tags", "").compared_with(
            OPERATOR_REGISTRY["contains"]
        )
        self.assertTrue(compared_field.whole)
        self.assertFalse(compared_field.many)
        self.assertTrue(compared_field.values_worth_listing)

    def test_a_field_with_no_operator_of_its_own_compares_one_whole_value(self):
        """`field_transition` declares no operator, and both its ends are single whole values."""
        compared_field = ComparedField.for_path(self.addressable, "status", "name").compared_with(None)
        self.assertTrue(compared_field.whole)
        self.assertFalse(compared_field.many)


@tag("unit")
class StoredRowTest(RowFormTestCase):
    """The `update` form, where a rule saved earlier comes back as controls holding its values.

    The JSON tab and the REST API both accept anything, so a stored row may be whatever was typed.
    """

    def test_a_stored_boolean_comes_back_chosen(self):
        """Django renders it as `str(value)`, so the option values have to be `True` and `False`."""
        for stored, option in (
            (True, '<option value="True" selected>Yes</option>'),
            (False, '<option value="False" selected>No</option>'),
        ):
            with self.subTest(stored):
                rendered = str(self.form(compare(field="enabled", operator="=", value=stored))["value"])
                self.assertInHTML(option, rendered)

    def test_a_dotted_path_becomes_the_two_selects_that_edit_it(self):
        initial = _stored_row_as_initial(compare(field="status.name", operator="in", value=["Active"]))
        self.assertEqual(initial["field"], "status")
        self.assertEqual(initial[_subfield_name("field")], "name")

    def test_negation_becomes_the_word_the_row_opens_with(self):
        for stored, word in ((True, "not"), (False, "when")):
            with self.subTest(stored):
                row = {"type": "expression", "source": "x", "negate": stored}
                self.assertEqual(_stored_row_as_initial(row)["negate"], word)

    def test_values_that_are_not_a_mapping_are_ignored_rather_than_fatal(self):
        """Anything can be typed on the JSON tab. The row renders with its controls empty and is refused on save."""
        initial = _stored_row_as_initial({"type": "preset", "preset": "field_changed", "values": "nope"})
        self.assertEqual(initial["type"], "field_changed")
        self.assertIsNone(initial["field"])

    def test_a_preset_no_lookup_can_accept_renders_bare(self):
        """A dict lookup raises on a list or a dict, which would answer the editor with a 500."""
        for preset in (["field_compare"], {"key": "field_compare"}, 7):
            with self.subTest(preset):
                form = self.form({"type": "preset", "preset": preset, "values": {}})
                self.assertEqual(form.parameter_controls, [])

    def test_an_operator_no_lookup_can_accept_leaves_the_other_controls(self):
        self.assertEqual(
            self.control_names(compare(field="mtu", operator=["gt"], value=9000)), ["field", "operator", "value"]
        )

    def test_a_row_survives_the_trip_to_controls_and_back(self):
        form = self.form(compare(field="status.name", operator="in", value=["Active", "Planned"]))
        held = {control.name: control.value() for control in form.parameter_controls}
        self.assertEqual(held["field"], "status")
        self.assertEqual(held["field_subfield"], "name")
        self.assertEqual(held["operator"], "in")
        self.assertEqual(held["value"], ["Active", "Planned"])

    def test_several_values_come_back_as_several(self):
        """`QueryDict.get` keeps only the last, which would quietly drop all but one on every rebuild."""
        data = QueryDict(
            "condition-0-type=field_compare&condition-0-field=status&condition-0-field_subfield=name"
            "&condition-0-operator=in&condition-0-value=Active&condition-0-value=Planned"
        )
        form = ConditionRowForm(data, index=0, addressable=self.addressable)
        self.assertEqual(list(form.fields["value"].widget.choices), [("Active", "Active"), ("Planned", "Planned")])


@tag("unit")
class StaleValuesTest(RowFormTestCase):
    """Naming a different field makes what was being compared meaningless, so it is not carried over."""

    def setUp(self):
        super().setUp()
        self.data = QueryDict(
            "condition-0-type=field_compare&condition-0-field=status&condition-0-field_subfield=name"
            "&condition-0-operator=in&condition-0-value=Active"
        )

    def kept(self, triggered_by):
        return _without_stale_values(self.data, "condition-0", triggered_by)

    def test_nothing_is_cleared_when_nothing_triggered_the_rebuild(self):
        self.assertIs(self.kept(None), self.data)

    def test_a_first_render_carries_no_data_to_clear(self):
        self.assertIsNone(_without_stale_values(None, "condition-0", "condition-0-field"))

    def test_nothing_is_cleared_for_a_preset_the_registry_does_not_hold(self):
        """The JSON tab accepts any preset key, and the row naming one still has to be drawn."""
        typed = QueryDict("condition-0-type=no_such_preset&condition-0-value=Active")
        self.assertIs(_without_stale_values(typed, "condition-0", "condition-0-field"), typed)

    def test_nothing_is_cleared_for_a_preset_that_names_no_field(self):
        """`user_is` compares a username, so no choice of field can make its value meaningless."""
        typed = QueryDict("condition-0-type=user_is&condition-0-username=automation")
        self.assertIs(_without_stale_values(typed, "condition-0", "condition-0-username"), typed)

    def test_choosing_an_operator_keeps_the_value(self):
        """The operator changes how the value is compared, not what it means."""
        self.assertEqual(self.kept("condition-0-operator")["condition-0-value"], "Active")

    def test_choosing_a_sub_field_clears_the_value(self):
        self.assertNotIn("condition-0-value", self.kept("condition-0-field_subfield"))
        self.assertEqual(self.kept("condition-0-field_subfield")["condition-0-field_subfield"], "name")

    def test_choosing_a_field_clears_the_sub_field_as_well(self):
        """That sub-field belonged to the relation just replaced, so it means nothing under the new one."""
        cleared = self.kept("condition-0-field")
        self.assertNotIn("condition-0-value", cleared)
        self.assertNotIn("condition-0-field_subfield", cleared)
        self.assertEqual(cleared["condition-0-field"], "status")


@tag("unit")
class RefusedSaveTest(RowFormTestCase):
    """A save that is refused says so in the row it refused, beside the control to blame."""

    def test_a_complaint_naming_a_parameter_reaches_that_control(self):
        errors = errors_by_row_and_control([compare(field="mtu")])
        self.assertEqual(errors, {0: {"operator": ["Parameter `operator` is required."]}})

    def test_a_complaint_naming_a_row_key_reaches_that_control(self):
        errors = errors_by_row_and_control([{"type": "expression", "source": "data.mtu >"}])
        self.assertIn("source", errors[0])

    def test_rows_that_pass_are_not_in_the_answer_at_all(self):
        errors = errors_by_row_and_control([compare(field="mtu", operator="gt", value=9000), compare(field="mtu")])
        self.assertEqual(list(errors), [1])

    def test_a_complaint_naming_a_control_the_row_does_not_hold_becomes_the_rows_own(self):
        """An App leaves and takes its preset with it. The row then holds nothing the complaint can name."""
        row = {"type": "preset", "preset": "no_such_preset", "values": {"operator": "="}}
        form = self.form(row, errors=errors_by_row_and_control([row])[0])
        self.assertEqual(form.non_field_errors(), ["Unknown condition preset `no_such_preset`."])

    def test_a_complaint_about_the_type_becomes_the_rows_own(self):
        """The two selects that open the sentence show no label, so they have nowhere to show a message."""
        errors = errors_by_row_and_control([{"type": "nope"}])
        form = self.form({"type": "nope"}, errors=errors[0])
        self.assertEqual(form.non_field_errors(), ["Unknown condition row type `nope`."])
        self.assertEqual(form["type"].errors, [])

    def test_a_complaint_naming_a_control_is_carried_by_that_control(self):
        form = self.form(compare(field="mtu"), errors={"operator": ["Required."]})
        self.assertEqual(form.non_field_errors(), [])
        self.assertEqual(form["operator"].errors, ["Required."])

    def test_a_refused_control_says_where_its_message_is(self):
        """Django writes this because the message is one of the form's own errors."""
        form = self.form(compare(field="mtu"), errors={"operator": ["Required."]})
        rendered = str(form["operator"])
        self.assertIn('aria-invalid="true"', rendered)
        self.assertIn("id_condition-0-operator_error", rendered)


@tag("unit")
class EditorContractTest(RowFormTestCase):
    """What the browser reads off a control.

    `ui/src/js/conditions-editor.js` rebuilds the stored JSON from the roles, and HTMX fetches a row
    again from the rest. Neither knows a preset, only these attributes.
    """

    def roles(self, row):
        form = self.form(row)
        return {name: field.widget.attrs.get("data-nb-condition-role") for name, field in form.fields.items()}

    def test_every_control_says_what_part_it_plays(self):
        roles = self.roles(compare(field="status.name", operator="in", value=["Active"]))
        self.assertEqual(
            roles,
            {
                "type": ROLE_TYPE,
                "negate": ROLE_NEGATE,
                "field": ROLE_PATH,
                "field_subfield": ROLE_SUBFIELD,
                "operator": ROLE_VALUE,
                "value": ROLE_VALUE,
            },
        )

    def test_a_raw_expression_says_so_too(self):
        self.assertEqual(self.roles({"type": "expression", "source": "x"})["source"], ROLE_SOURCE)

    def test_the_two_halves_of_a_path_are_paired_by_the_parameter_they_edit(self):
        """Roles alone do not pair them, because a preset may declare more than one field parameter."""
        form = self.form(compare(field="status.name"))
        self.assertEqual(form.fields["field"].widget.attrs["data-nb-condition-key"], "field")
        self.assertEqual(form.fields["field_subfield"].widget.attrs["data-nb-condition-key"], "field")

    def test_a_boolean_asks_the_browser_for_a_real_boolean(self):
        """`_equals` compares a boolean field against a boolean, never against the string a select carries."""
        widget = self.form(compare(field="enabled", operator="=")).fields["value"].widget
        self.assertEqual(widget.attrs["data-nb-condition-cast"], "boolean")

    def test_only_the_controls_that_change_the_row_ask_for_it_again(self):
        form = self.form(compare(field="status.name", operator="in", value=["Active"]))
        refetches = {name for name, field in form.fields.items() if "hx-get" in field.widget.attrs}
        self.assertEqual(refetches, {"type", "field", "field_subfield", "operator"})

    def test_a_rebuild_replaces_the_condition_the_control_sits_in(self):
        """Named by the class the stylesheet lays the condition out by, there being no other handle."""
        attrs = self.form(compare(field="mtu")).fields["field"].widget.attrs
        self.assertEqual(attrs["hx-target"], "closest .nb-condition")
        self.assertEqual(attrs["hx-include"], "closest .nb-condition, #id_content_types")


@tag("unit")
class EditorScriptKnowsTheSameNamesTest(SimpleTestCase):
    """Whether `ui/src/js/conditions-editor.js` still spells the names `conditions/forms.py` writes."""

    SCRIPT = Path(settings.BASE_DIR) / "ui" / "src" / "js" / "conditions-editor.js"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.script = cls.SCRIPT.read_text()

    def test_the_script_spells_every_name_the_form_writes(self):
        literals = [f"'{attribute}'" for attribute in (ROLE_ATTR, KEY_ATTR, CAST_ATTR)]
        literals += [
            f"{role.upper()}: '{role}'"
            for role in (ROLE_TYPE, ROLE_NEGATE, ROLE_SOURCE, ROLE_PATH, ROLE_SUBFIELD, ROLE_VALUE)
        ]
        literals.append(f"CAST_BOOLEAN = '{CAST_BOOLEAN}'")
        # Django renders a stored boolean as `str(True)`, so the script must compare against `True`.
        literals.append(f"=== '{BOOLEAN_CHOICES[0][0]}'")
        for literal in literals:
            with self.subTest(literal):
                # `assertIn` would print the whole script, which tells a reader nothing the name does not.
                self.assertTrue(literal in self.script, f"`{literal}` is nowhere in {self.SCRIPT.name}.")


@tag("unit")
class SubfieldIsAlwaysAnsweredTest(RowFormTestCase):
    """A path that stops at a relation addresses a mapping, which nothing a condition compares can equal."""

    def choices(self, row):
        return list(self.form(row).fields["field_subfield"].widget.choices)

    def test_no_blank_is_offered(self):
        self.assertNotIn("", [value for value, _ in self.choices(compare(field="status"))])

    def test_name_leads_where_the_relation_has_one(self):
        self.assertEqual(self.choices(compare(field="status"))[0], ("name", "name"))

    def test_a_relation_named_with_no_sub_field_is_given_one(self):
        self.assertEqual(self.form(compare(field="status"))["field_subfield"].value(), "name")

    def test_a_stored_sub_field_is_left_alone(self):
        self.assertEqual(self.form(compare(field="status.id"))["field_subfield"].value(), "id")
