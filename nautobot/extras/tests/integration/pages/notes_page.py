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
    _MESSAGES = "#header_messages, #toast-messages"

    def navigate_to_object(self, object_path):
        """Go to the object's detail view."""
        self._goto(object_path)

    def open_notes_tab(self):
        """Click the visible Notes tab and wait for it to load."""
        with self.page.expect_event("framenavigated"):
            self.page.locator(self._NOTES_TAB).filter(visible=True).first.click()
        self.wait_for_load()

    def add_note(self, text):
        """Fill the note form and submit it."""
        self.page.fill(self._NOTE_TEXTAREA, text)
        self._click_and_wait_for_navigation(self._CREATE_BUTTON)

    def edit_note(self, old_text, new_text):
        """Open the edit form for the note showing *old_text*, replace its body with *new_text*, and submit."""
        row = self._note_row(old_text)
        row.get_by_role("button", name="Toggle Dropdown").click()
        with self.page.expect_event("framenavigated"):
            self.page.locator(self._EDIT_LINK).click()
        self.wait_for_load()
        self.page.fill(self._NOTE_TEXTAREA, new_text)
        self._click_and_wait_for_navigation(self._UPDATE_BUTTON)

    def _note_row(self, text):
        """Locator for the notes table row showing *text*."""
        return self.page.locator(self._NOTE_ROWS).filter(has_text=text)

    def expect_message(self, text):
        """Assert (auto-retrying) that a flash message contains *text*."""
        expect(self.page.locator(self._MESSAGES).filter(has_text=text)).to_have_count(1)

    def expect_note(self, text, present=True):
        """Assert (auto-retrying) that the notes table does or does not show *text*."""
        expect(self._note_row(text)).to_have_count(1 if present else 0)
