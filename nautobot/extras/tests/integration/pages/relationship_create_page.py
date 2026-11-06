"""Page object for the Relationship create form (/extras/relationships/add/)."""

from playwright.sync_api import expect

from nautobot.playwright.object_form_page import ObjectFormPage


class RelationshipCreatePage(ObjectFormPage):
    """The Relationship create form, whose script copies the source fields to disabled destination fields for symmetric types."""

    ADD_PATH = "/extras/relationships/add/"

    _TYPE = "#id_type"
    # The four source/destination field pairs that relationship_form.js keeps in sync, named by field suffix.
    _MIRRORED_FIELDS = ("type", "label", "hidden", "filter")

    def _field(self, side, name):
        """Locator for the *side* ("source" or "destination") field *name* ("type", "label", "hidden" or "filter")."""
        return self.page.locator(f"#id_{side}_{name}")

    # -------------------------------------------------------------------------
    # Filling the form
    # -------------------------------------------------------------------------

    def select_type(self, relationship_type):
        """Choose the relationship type by the value of *relationship_type*, e.g. "symmetric-many-to-many"."""
        self.page.locator(self._TYPE).select_option(relationship_type)

    def select_object_type(self, side, type_label):
        """Choose the *side* object type by its option label, e.g. "DCIM | manufacturer"."""
        self._field(side, "type").select_option(label=type_label)

    def fill_side(self, side, label, filter_json, hidden):
        """Fill the *side* label and filter, and set its hidden checkbox to *hidden*."""
        self._field(side, "label").fill(label)
        self._field(side, "filter").fill(filter_json)
        self._field(side, "hidden").set_checked(hidden)

    # -------------------------------------------------------------------------
    # Destination field state
    # -------------------------------------------------------------------------

    def expect_destination(self, type_label, label, filter_json, hidden):
        """Assert (auto-retrying) the destination fields' current values."""
        self.expect_destination_type(type_label)
        expect(self._field("destination", "label")).to_have_value(label)
        expect(self._field("destination", "filter")).to_have_value(filter_json)
        if hidden:
            expect(self._field("destination", "hidden")).to_be_checked()
        else:
            expect(self._field("destination", "hidden")).not_to_be_checked()

    def expect_destination_type(self, type_label):
        """Assert (auto-retrying) that the destination object type shows the option labelled *type_label*."""
        expect(self._field("destination", "type").locator("option:checked")).to_have_text(type_label)

    def expect_destination_disabled(self):
        """Assert (auto-retrying) that every destination field that the script copies from the source is disabled."""
        for name in self._MIRRORED_FIELDS:
            expect(self._field("destination", name)).to_be_disabled()

    def expect_destination_enabled(self):
        """Assert (auto-retrying) that every destination field that the script copies from the source is enabled."""
        for name in self._MIRRORED_FIELDS:
            expect(self._field("destination", name)).to_be_enabled()
