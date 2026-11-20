"""Page object for the Custom Field add and edit forms (/extras/custom-fields/add/ and <pk>/edit/)."""

from playwright.sync_api import expect

from nautobot.extras.tests.integration.pages.custom_field_choices_formset import CustomFieldChoicesFormset
from nautobot.playwright.object_form_page import ObjectFormPage


class CustomFieldFormPage(ObjectFormPage):
    """Page object for the Custom Field add form, and for the edit form that `click_edit` opens."""

    # customfield_form.js shows only the cards and fields that apply to the selected type, and disables the
    # inputs it hides, so the browser does not submit their values. The `choices` component handles the choice rows.
    ADD_PATH = "/extras/custom-fields/add/"

    _TYPE = "#id_type"
    _VALIDATION_RULES_CARD = "#nb-validation-rules-card"
    # Each validation field is wrapped in a div with its own id, which the script hides and shows.
    _VALIDATION_FIELD = "#nb-validation-{name}-field"
    _VALIDATION_HELP_TEXT = "#nb-validation-{name}-field .form-text"
    # Picking a content type makes HTMX replace the Scope filter card with a card that contains the filter tabs. The
    # form's submit handler reads that card's Advanced tab, so wait for it before submitting.
    _SCOPE_FILTER_TABS = "#nb-scope-filter-form-container #filter-tabs"

    def __init__(self, page, base_url):
        """Bind the page object, and the choice rows component, to *page*."""
        super().__init__(page, base_url)
        self.choices = CustomFieldChoicesFormset(page)

    # -------------------------------------------------------------------------
    # Filling the form
    # -------------------------------------------------------------------------

    def fill_label(self, label):
        """Type *label* into Label, and a key made from it into Key.

        The key must be a valid identifier. The page fills Key from Label only on a keyup or change
        event, and `fill()` sends neither event, so this method types the key itself.
        """
        self.fill_input("label", label)
        self.fill_input("key", label.replace("-", "_").replace(" ", "_").lower())

    def select_type(self, field_type):
        """Choose the custom field type by its value, e.g. "multi-select"."""
        self.page.locator(self._TYPE).select_option(field_type)

    def pick_content_type(self, text):
        """Add the content type whose label is *text*, e.g. "DCIM | device", and wait for the scope filter to load."""
        self.pick_choice("content_types", text)
        expect(self.page.locator(self._SCOPE_FILTER_TABS)).to_be_attached()

    def fill_validation(self, minimum=None, maximum=None, regex=None):
        """Type each validation rule that is not None into its field."""
        for name, value in (("minimum", minimum), ("maximum", maximum), ("regex", regex)):
            if value is not None:
                self.fill_input(f"validation_{name}", str(value))

    # -------------------------------------------------------------------------
    # Type-dependent cards and fields
    # -------------------------------------------------------------------------

    # The Custom Field Choices card has its own pair, `choices.expect_visible()` and `choices.expect_hidden()`.

    def expect_validation_rules_card_visible(self):
        """Assert (auto-retrying) that the Validation Rules card is shown."""
        expect(self.page.locator(self._VALIDATION_RULES_CARD)).to_be_visible()

    def expect_validation_rules_card_hidden(self):
        """Assert (auto-retrying) that the Validation Rules card is hidden."""
        expect(self.page.locator(self._VALIDATION_RULES_CARD)).to_be_hidden()

    def expect_validation_field_visible(self, name):
        """Assert (auto-retrying) that the validation field *name* ("minimum", "maximum" or "regex") is shown."""
        expect(self.page.locator(self._VALIDATION_FIELD.format(name=name))).to_be_visible()

    def expect_validation_field_hidden(self, name):
        """Assert (auto-retrying) that the validation field *name* ("minimum", "maximum" or "regex") is hidden."""
        expect(self.page.locator(self._VALIDATION_FIELD.format(name=name))).to_be_hidden()

    def expect_validation_help_text(self, minimum, maximum):
        """Assert (auto-retrying) the help text under the minimum and maximum fields."""
        expect(self.page.locator(self._VALIDATION_HELP_TEXT.format(name="minimum"))).to_have_text(minimum)
        expect(self.page.locator(self._VALIDATION_HELP_TEXT.format(name="maximum"))).to_have_text(maximum)
