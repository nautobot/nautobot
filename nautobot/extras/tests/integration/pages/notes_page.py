"""Page object for an object's Notes tab (/<app>/<model>/<pk>/notes/) and the note edit form."""

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage


class ObjectNotesPage(BasePage):
    """The Notes tab of any object detail view."""

    _NOTES_TAB = "a.nav-link[href$='/notes/']"
    _NOTE_TEXTAREA = "textarea[name='note']"
    _CREATE_BUTTON = "button#createNote"
    _UPDATE_BUTTON = "button[name='_update']"
    _NOTE_ROWS = "table tbody tr"
    # Opening a table's actions dropdown moves its menu to <body>, out of the row.
    _EDIT_LINK = ".dropdown-menu.show a.dropdown-item[href*='/edit/']"

    def navigate_to_object(self, list_path, pk):
        """Go to the detail view of the object at `<list_path><pk>/`, e.g. `("/dcim/locations/", pk)`."""
        self._goto(f"{list_path}{pk}/")

    def navigate_to_notes(self, list_path, pk):
        """Go to the Notes tab of the object at `<list_path><pk>/`, e.g. `("/dcim/locations/", pk)`."""
        self._goto(f"{list_path}{pk}/notes/")

    def open_notes_tab(self):
        """Click the Notes tab and wait for it to load."""
        self._click_and_wait_for_navigation(self._NOTES_TAB)

    def add_note(self, text):
        """Fill the note form and submit it."""
        self.page.fill(self._NOTE_TEXTAREA, text)
        self._click_and_wait_for_navigation(self._CREATE_BUTTON)

    def edit_note(self, old_text, new_text):
        """Open the edit form for the note showing *old_text*, replace its body with *new_text*, and submit."""
        self._note_row(old_text).get_by_role("button", name="Toggle Dropdown").click()
        self._click_and_wait_for_navigation(self._EDIT_LINK)
        self.page.fill(self._NOTE_TEXTAREA, new_text)
        self._click_and_wait_for_navigation(self._UPDATE_BUTTON)

    def _note_row(self, text):
        """Locator for the notes table row showing *text*."""
        return self.page.locator(self._NOTE_ROWS).filter(has_text=text)

    def expect_note(self, text, present=True):
        """Assert (auto-retrying) that the notes table does or does not show *text*."""
        expect(self._note_row(text)).to_have_count(1 if present else 0)
