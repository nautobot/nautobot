"""Notes tab: create and edit a note on an object."""

import pytest

from nautobot.dcim.tests.integration.pages.location_detail_page import LocationDetailPage
from nautobot.extras.tests.integration.pages.notes_page import ObjectNotesPage
from nautobot.playwright.helpers import unique_name


class NoteTestCase:
    """The Notes tab of an object detail view: adding a note and editing one."""

    @pytest.mark.behavioral
    def test_create_note(self, auth_page, base_url, api, created_location):
        """A note added from the Notes tab is shown in the notes table and saved against the object."""
        text = f"{unique_name()} maintenance notice"
        LocationDetailPage(auth_page, base_url).navigate(created_location["id"])
        notes = ObjectNotesPage(auth_page, base_url)
        notes.open_notes_tab()

        notes.add_note(text)

        notes.expect_flash_message("Created note")
        notes.expect_note(text)
        saved = api.get(f"/api/dcim/locations/{created_location['id']}/notes/").json()["results"]
        assert text in [note["note"] for note in saved]

    @pytest.mark.behavioral
    def test_update_note(self, auth_page, base_url, api, created_location, created_note):
        """Editing a note replaces its body in the notes table."""
        new_text = f"{unique_name()} updated note"
        notes = ObjectNotesPage(auth_page, base_url)
        notes.navigate_to_notes_tab("/dcim/locations/", created_location["id"])

        notes.edit_note(created_note["note"], new_text)

        notes.expect_flash_message("Modified note")
        # The edit link's return_url is the object's main tab, so the update lands there.
        notes.open_notes_tab()
        notes.expect_note(new_text)
        notes.expect_note(created_note["note"], present=False)
        assert api.get(f"/api/extras/notes/{created_note['id']}/").json()["note"] == new_text
