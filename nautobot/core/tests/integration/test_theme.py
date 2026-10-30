"""Theme modal: opened from the footer to choose Light, Dark or System."""

import pytest

from nautobot.core.tests.integration.pages.home_page import HomePage


class ThemeTestCase:
    """The theme modal opened from the footer theme button."""

    def test_modal_not_rendered(self, auth_page, base_url):
        """The theme modal is on the page but stays closed until it is opened."""
        home = HomePage(auth_page, base_url)
        home.navigate()

        home.expect_theme_modal(is_open=False)

    @pytest.mark.behavioral
    def test_modal_rendered(self, auth_page, base_url):
        """The footer button opens the modal with System selected by default, and Cancel closes it."""
        home = HomePage(auth_page, base_url)
        home.navigate()

        home.open_theme_modal()

        home.expect_theme_modal(is_open=True)
        home.expect_theme_choices(["Light", "Dark", "System"])
        home.expect_selected_theme("system")

        home.cancel_theme_modal()

        home.expect_theme_modal(is_open=False)
