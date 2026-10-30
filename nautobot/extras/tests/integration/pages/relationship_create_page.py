"""Page object for the Relationship create form (/extras/relationships/add/)."""

import re

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage


class RelationshipCreatePage(BasePage):
    """The Relationship create form, whose script copies the source fields to disabled destination fields for symmetric types."""

    ADD_PATH = "/extras/relationships/add/"

    _LABEL = "#id_label"
    _TYPE = "#id_type"
    _CREATE_BUTTON = "button[name='_create']"
    # The four source/destination field pairs that relationship_form.js keeps in sync, named by field suffix.
    _MIRRORED_FIELDS = ("type", "label", "hidden", "filter")
    # The group is unnamed because expect().to_have_url() passes the pattern to the browser as a
    # JavaScript RegExp, which does not accept Python's (?P<name>...) syntax.
    _DETAIL_URL = re.compile(r"/extras/relationships/([0-9a-f-]{36})/$")

    def navigate(self):
        """Go to the empty create form."""
        self._goto(self.ADD_PATH)

    def _field(self, side, name):
        """Locator for the *side* ("source" or "destination") field *name* ("type", "label", "hidden" or "filter")."""
        return self.page.locator(f"#id_{side}_{name}")

    # -------------------------------------------------------------------------
    # Filling the form
    # -------------------------------------------------------------------------

    def fill_label(self, label):
        """Type *label*. The form's script fills the key from it."""
        self.page.locator(self._LABEL).fill(label)

    def select_type(self, relationship_type):
        """Choose the relationship type by the value of *relationship_type*, e.g. "symmetric-many-to-many"."""
        self.page.locator(self._TYPE).select_option(relationship_type)

    def select_object_type(self, side, content_type_id):
        """Choose the *side* object type by its content type id."""
        self._field(side, "type").select_option(str(content_type_id))

    def fill_side(self, side, label, filter_json, hidden):
        """Fill the *side* label and filter, and set its hidden checkbox to *hidden*."""
        self._field(side, "label").fill(label)
        self._field(side, "filter").fill(filter_json)
        self._field(side, "hidden").set_checked(hidden)

    def submit(self) -> str:
        """Click Create and return the new relationship's id from the detail page it redirects to."""
        self._click_and_wait_for_navigation(self._CREATE_BUTTON)
        expect(self.page).to_have_url(self._DETAIL_URL)
        return self._DETAIL_URL.search(self.page.url).group(1)

    # -------------------------------------------------------------------------
    # Destination field state
    # -------------------------------------------------------------------------

    def expect_destination(self, content_type_id, label, filter_json, hidden):
        """Assert (auto-retrying) the destination fields' current values."""
        expect(self._field("destination", "type")).to_have_value(str(content_type_id))
        expect(self._field("destination", "label")).to_have_value(label)
        expect(self._field("destination", "filter")).to_have_value(filter_json)
        if hidden:
            expect(self._field("destination", "hidden")).to_be_checked()
        else:
            expect(self._field("destination", "hidden")).not_to_be_checked()

    def expect_destination_type(self, content_type_id):
        """Assert (auto-retrying) the destination object type's current value."""
        expect(self._field("destination", "type")).to_have_value(str(content_type_id))

    def expect_destination_disabled(self):
        """Assert (auto-retrying) that every mirrored destination field is disabled."""
        for name in self._MIRRORED_FIELDS:
            expect(self._field("destination", name)).to_be_disabled()

    def expect_destination_enabled(self):
        """Assert (auto-retrying) that every mirrored destination field is enabled."""
        for name in self._MIRRORED_FIELDS:
            expect(self._field("destination", name)).to_be_enabled()
