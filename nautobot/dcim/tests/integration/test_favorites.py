"""Favoriting a page from the page title star, driven through a concrete list view."""

from playwright.sync_api import expect

from nautobot.dcim.tests.integration.pages.locations_page import LocationsPage

FAVORITE_NAME = "Locations"


class FavoritesTestCase:
    """Add a page to favorites through the confirmation modal, then remove it again."""

    def test_add_and_remove_page_favorite(self, auth_page, base_url, user_favorites):
        """The star opens a prefilled modal, submitting it favorites the page, and clicking again undoes it.

        `user_favorites` is requested for its teardown only; this test creates its favorite
        through the UI, which is the behavior under test.
        """
        page = LocationsPage(auth_page, base_url)
        page.navigate()
        page.reveal_favorite_star()
        page.favorite_star("Add to Favorites").click()

        modal = auth_page.locator("#nautobot-generic-modal")
        expect(modal).to_be_visible()
        expect(modal.locator('input[name="link"]')).to_have_value(LocationsPage.LIST_PATH)
        expect(modal.locator('input[name="name"]')).to_have_value(FAVORITE_NAME)

        modal.locator('button[type="submit"]').click()
        expect(modal).to_be_hidden()
        expect(page.favorite_star("Remove from Favorites")).to_have_count(1)
        expect(page.favorite_entries(LocationsPage.LIST_PATH)).to_have_count(1)

        page.reveal_favorite_star()
        page.favorite_star("Remove from Favorites").click()
        expect(page.favorite_star("Add to Favorites")).to_have_count(1)
        expect(page.favorite_entries(LocationsPage.LIST_PATH)).to_have_count(0)
