"""Tests for the two views the conditions editor is drawn by.

Both answer with a fragment of a page rather than a page, and both are reached only by HTMX. Between
them they decide what the editor shows, so a change here is a change to the form.
"""

import json

from django.contrib.contenttypes.models import ContentType
from django.test import tag
from django.urls import reverse

from nautobot.core.testing import TestCase as NautobotTestCase
from nautobot.dcim.models import Interface


@tag("unit")
class ConditionsViewTest(NautobotTestCase):
    HTMX = {"HX-Request": "true"}

    @staticmethod
    def compare(**values):
        """A `field_compare` row, the only preset carrying a field, an operator and a value at once."""
        return {"type": "preset", "preset": "field_compare", "values": values}

    def setUp(self):
        super().setUp()
        self.row_url = reverse("extras:condition_row")
        self.rows_url = reverse("extras:condition_rows")
        self.content_type = ContentType.objects.get_for_model(Interface).pk

    def rows(self, conditions, validate=False, **extra):
        url = self.rows_url + ("?validate=1" if validate else "")
        response = self.client.post(
            url, {"conditions": json.dumps(conditions), "content_types": self.content_type, **extra}, headers=self.HTMX
        )
        self.assertHttpStatus(response, 200)
        return response.content.decode(response.charset)

    def row(self, headers=None, **params):
        response = self.client.get(
            self.row_url, {"content_types": self.content_type, **params}, headers={**self.HTMX, **(headers or {})}
        )
        self.assertHttpStatus(response, 200)
        return response.content.decode(response.charset)

    def test_a_request_the_editor_did_not_make_is_refused(self):
        """Neither view is an address to visit. What they answer with is meaningless on its own."""
        for url, ask in ((self.row_url, self.client.get), (self.rows_url, self.client.post)):
            with self.subTest(url):
                self.assertHttpStatus(ask(url), 400)

    def test_htmx_is_let_through(self):
        for url, ask, data in (
            (self.row_url, self.client.get, {}),
            (self.rows_url, self.client.post, {"conditions": "[]"}),
        ):
            with self.subTest(url):
                self.assertHttpStatus(ask(url, data, headers=self.HTMX), 200)

    def test_signing_in_is_asked_for_before_anything_else(self):
        """Ahead of the 400, so an unknown caller is not told which addresses exist."""
        self.client.logout()
        self.assertHttpStatus(self.client.get(self.row_url), 302)

    def test_an_htmx_caller_is_sent_to_the_login_page_rather_than_shown_it(self):
        """`HtmxLoginRedirectMiddleware` turns the 302 into a 204, or the login form lands in the row."""
        self.client.logout()
        response = self.client.post(self.rows_url, {"conditions": "[]"}, headers=self.HTMX)
        self.assertHttpStatus(response, 204)
        self.assertIn(reverse("login"), response.headers["HX-Redirect"])

    def test_one_row_per_stored_condition_in_order(self):
        body = self.rows([self.compare(field="mtu", operator="gt", value=9000), {"type": "expression", "source": "x"}])
        self.assertEqual(body.count("data-nb-condition-index="), 2)
        self.assertIn('name="condition-0-operator"', body)
        self.assertIn('name="condition-1-source"', body)

    def test_a_field_holding_nothing_still_offers_one_row(self):
        """The way the other repeating forms here do, so there is something to start from."""
        for empty in ("", "[]"):
            with self.subTest(empty):
                response = self.client.post(
                    self.rows_url, {"conditions": empty, "content_types": self.content_type}, headers=self.HTMX
                )
                self.assertEqual(response.content.decode(response.charset).count("data-nb-condition-index="), 1)

    def test_each_row_is_stamped_with_its_position(self):
        """The editor reads these to number a row it adds, rather than counting what is on screen."""
        body = self.rows([self.compare(field="mtu"), self.compare(field="mtu"), self.compare(field="mtu")])
        self.assertIn('data-nb-condition-index="2"', body)

    def test_a_field_that_cannot_be_read_says_so_in_place_of_the_conditions(self):
        for conditions, said in (
            ("{oops", "does not parse"),
            ('{"a": 1}', "not a list of conditions"),
            ("[1, 2]", "not a condition"),
        ):
            with self.subTest(conditions):
                response = self.client.post(
                    self.rows_url, {"conditions": conditions, "content_types": self.content_type}, headers=self.HTMX
                )
                body = response.content.decode(response.charset)
                self.assertIn(said, body)
                self.assertIn("nb-conditions-unreadable", body)

    def test_the_message_names_itself_so_the_editor_stops_writing_the_field(self):
        """Without the class the editor would read that row as nothing and replace what was typed with `[]`."""
        readable = self.rows([self.compare(field="mtu")])
        self.assertNotIn("nb-conditions-unreadable", readable)

    def test_nothing_is_complained_about_unasked(self):
        """A row half filled in is a row being filled in, not a mistake."""
        body = self.rows([self.compare(field="mtu")])
        self.assertNotIn("has-error", body)

    def test_asking_shows_the_complaint_beside_the_control_at_fault(self):
        body = self.rows([self.compare(field="mtu")], validate=True)
        self.assertInHTML("<li class='text-danger'>Parameter `operator` is required.</li>", body)
        self.assertIn("has-error", body)

    def test_a_complaint_with_no_control_to_blame_is_still_said(self):
        body = self.rows([{"type": "nope"}], validate=True)
        self.assertInHTML("<li>Unknown condition row type `nope`.</li>", body)

    def test_the_empty_row_a_bare_form_offers_is_not_complained_about(self):
        """It stands for nothing stored, so there is nothing yet for a save to refuse."""
        body = self.rows([], validate=True)
        self.assertEqual(body.count("data-nb-condition-index="), 1)
        self.assertNotIn("must be a mapping", body)

    def test_the_complaint_does_not_repeat_the_row_it_is_in(self):
        """`Condition 1:` belongs to a reader who has no row in front of them, which this one has."""
        body = self.rows([self.compare(field="mtu")], validate=True)
        self.assertNotIn("Condition 1:", body)

    def test_the_answer_is_one_row(self):
        """A control that decides what the rest of the row should be asks for the row again."""
        body = self.row(index=3, **{"condition-3-type": "field_compare", "condition-3-field": "mtu"})
        self.assertEqual(body.count("data-nb-condition-index="), 1)
        self.assertIn('data-nb-condition-index="3"', body)

    def test_it_is_built_from_the_controls_the_request_carries(self):
        """Not from the stored field, which at the moment a control changes does not yet know about it."""
        body = self.row(
            index=0,
            **{
                "condition-0-type": "field_compare",
                "condition-0-field": "status",
                "condition-0-field_subfield": "name",
                "condition-0-operator": "in",
            },
        )
        self.assertIn("nautobot-select2-api", body)
        self.assertIn("content_types=dcim.interface", body)

    def test_naming_a_different_field_drops_what_was_being_compared(self):
        """A value compared against `status.name` says nothing once the row names something else."""
        sent = {
            "condition-0-type": "field_compare",
            "condition-0-field": "status",
            "condition-0-field_subfield": "name",
            "condition-0-operator": "contains",
            "condition-0-value": "keepme",
        }
        self.assertIn("keepme", self.row(index=0, **sent))
        self.assertNotIn("keepme", self.row(headers={"HX-Trigger-Name": "condition-0-field"}, index=0, **sent))

    def test_choosing_an_operator_keeps_the_value(self):
        sent = {
            "condition-0-type": "field_compare",
            "condition-0-field": "description",
            "condition-0-operator": "contains",
            "condition-0-value": "keepme",
        }
        self.assertIn("keepme", self.row(headers={"HX-Trigger-Name": "condition-0-operator"}, index=0, **sent))

    def test_an_index_that_is_not_a_number_falls_back_to_the_first(self):
        self.assertIn('data-nb-condition-index="0"', self.row(index="boom"))

    def test_the_field_picker_says_to_choose_an_object_type_when_none_resolves(self):
        """The row still has to render. An empty field picker is recoverable, a swap that failed is not."""
        for label, sent in (
            ("none was sent", {}),
            ("what was sent is not a content type", {"content_types": "not-a-number"}),
        ):
            with self.subTest(label):
                response = self.client.post(
                    self.rows_url, {"conditions": json.dumps([self.compare(field="mtu")]), **sent}, headers=self.HTMX
                )
                self.assertHttpStatus(response, 200)
                body = response.content.decode(response.charset)
                self.assertInHTML("<option value=''>Select object type(s) first</option>", body)
                self.assertIn("disabled", body)

    def test_only_the_fields_every_chosen_type_carries_are_offered(self):
        """One condition is checked against every watched type, so a field only one of them has is no use.

        `mtu` is an interface field, so it is gone the moment a location is watched as well.
        """
        location = ContentType.objects.get(app_label="dcim", model="location").pk
        self.assertInHTML("<option value='mtu' selected>mtu</option>", self.rows([self.compare(field="mtu")]))
        response = self.client.post(
            self.rows_url,
            {"conditions": json.dumps([self.compare(field="mtu")]), "content_types": [self.content_type, location]},
            headers=self.HTMX,
        )
        self.assertNotIn('value="mtu"', response.content.decode(response.charset))
