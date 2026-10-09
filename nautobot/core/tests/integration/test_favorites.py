"""Favoriting a page from the page title star."""

from playwright.sync_api import expect

from nautobot.core.tests.integration.pages.about_page import AboutPage

FAVORITE_NAME = "About Nautobot"


def favorite_links(api):
    """The links the API currently lists as the user's favorites."""
    return [item["link"] for item in api.get("/api/users/config/").json().get("navbar_favorites", [])]


class FavoritesTestCase:
    """Adding and removing a page favorite from the page title star, including the duplicate-name error."""

    def test_add_page_favorite(self, auth_page, base_url, api, user_favorites):
        """The star opens a prefilled modal, and submitting it favorites the page."""
        # user_favorites is requested for its teardown; the favorite itself is created through the UI.
        page = AboutPage(auth_page, base_url)
        page.navigate()
        page.reveal_favorite_star()
        page.favorite_star("Add to Favorites").click()

        modal = page.favorite_modal()
        expect(modal).to_be_visible()
        expect(page.favorite_modal_field("link")).to_have_value(AboutPage.PATH)
        expect(page.favorite_modal_field("name")).to_have_value(FAVORITE_NAME)

        page.submit_favorite_modal()
        expect(modal).to_be_hidden()
        expect(page.favorite_star("Remove from Favorites")).to_have_count(1)
        expect(page.favorite_entries(AboutPage.PATH)).to_have_count(1)
        assert AboutPage.PATH in favorite_links(api)

    def test_remove_page_favorite(self, auth_page, base_url, api, user_favorites):
        """Clicking the active star removes the page from favorites and the flyout."""
        user_favorites({"link": AboutPage.PATH, "name": FAVORITE_NAME, "tab_name": ""})
        page = AboutPage(auth_page, base_url)
        page.navigate()
        expect(page.favorite_star("Remove from Favorites")).to_have_count(1)

        page.reveal_favorite_star()
        page.favorite_star("Remove from Favorites").click()
        expect(page.favorite_star("Add to Favorites")).to_have_count(1)
        expect(page.favorite_entries(AboutPage.PATH)).to_have_count(0)
        assert AboutPage.PATH not in favorite_links(api)

    def test_duplicate_name_keeps_the_modal_open(self, auth_page, base_url, api, user_favorites):
        """Submitting a name that is already a favorite shows the error in the modal instead of closing it."""
        user_favorites({"link": "/dcim/racks/", "name": FAVORITE_NAME, "tab_name": ""})
        page = AboutPage(auth_page, base_url)
        page.navigate()
        page.reveal_favorite_star()
        page.favorite_star("Add to Favorites").click()

        page.submit_favorite_modal()
        expect(page.favorite_modal()).to_be_visible()
        expect(page.favorite_modal()).to_contain_text("A favorite with this name already exists.")
        expect(page.favorite_entries(AboutPage.PATH)).to_have_count(0)
        assert AboutPage.PATH not in favorite_links(api)

    def test_corrected_name_submits_after_the_error(self, auth_page, base_url, api, user_favorites):
        """After a duplicate-name error, changing the name and submitting again adds the favorite."""
        user_favorites({"link": "/dcim/racks/", "name": FAVORITE_NAME, "tab_name": ""})
        page = AboutPage(auth_page, base_url)
        page.navigate()
        page.reveal_favorite_star()
        page.favorite_star("Add to Favorites").click()
        page.submit_favorite_modal()
        expect(page.favorite_modal()).to_contain_text("A favorite with this name already exists.")

        page.favorite_modal_field("name").fill(f"{FAVORITE_NAME} page")
        page.submit_favorite_modal()
        expect(page.favorite_modal()).to_be_hidden()
        expect(page.favorite_entries(AboutPage.PATH)).to_have_count(1)
        assert AboutPage.PATH in favorite_links(api)
