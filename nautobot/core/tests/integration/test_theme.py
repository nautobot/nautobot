import json

from django.template.loader import render_to_string
import yaml

from nautobot.core.testing.integration import SeleniumTestCase


class ThemeTestCase(SeleniumTestCase):
    """Integration tests for the shared theme and its selection modal."""

    def setUp(self):
        super().setUp()
        self.login(self.user.username, self.password)

    def test_serialized_data_wraps(self):
        """Shared JSON/YAML rendering preserves data and fits cards and auto-layout tables."""
        value = {
            "token": "x" * 400,
            "sentence": "This is a deliberately long message. " * 20,
            "nested": [{"name": "router1", "text": '<script>alert("test")</script> & 😀\nsecond line'}],
        }
        for width in (1440, 768, 375):
            self.browser.driver.set_window_size(width, 900)
            self.browser.driver.add_cookie({"name": "sidenav_collapsed", "value": str(width == 375).lower()})
            self.browser.visit(self.live_server_url)
            for language, parse in (("json", json.loads), ("yaml", yaml.safe_load)):
                content = render_to_string(
                    "components/panel/body_content_text.html", {"render_as": language, "value": value}
                )
                for theme in ("light", "dark"):
                    for table in (False, True):
                        with self.subTest(width=width, language=language, theme=theme, table=table):
                            dimensions = self.browser.driver.execute_script(
                                """
                                document.documentElement.dataset.bsTheme = arguments[1];
                                document.querySelector('#serialized-data-test')?.remove();
                                const card = document.createElement('div');
                                card.id = 'serialized-data-test';
                                card.className = 'card';
                                card.style.width = '100%';
                                const container = document.createElement('div');
                                container.className = 'card-body';
                                container.innerHTML = arguments[2]
                                    ? '<table class="table"><tr><th scope="row">Data</th><td>'
                                        + arguments[0] + '</td></tr></table>'
                                    : arguments[0];
                                card.append(container);
                                document.querySelector('#main-content').append(card);
                                const code = card.querySelector('code');
                                hljs.highlightElement(code);
                                const range = document.createRange();
                                range.selectNodeContents(code);
                                return {
                                    text: code.textContent,
                                    highlighted: code.classList.contains('hljs'),
                                    codeWidth: code.clientWidth,
                                    codeScrollWidth: code.scrollWidth,
                                    cardRight: card.getBoundingClientRect().right,
                                    contentRight: container.firstElementChild.getBoundingClientRect().right,
                                    textRight: Math.max(...Array.from(range.getClientRects(), rect => rect.right)),
                                    unsafeElements: code.querySelectorAll('script').length,
                                };
                                """,
                                content,
                                theme,
                                table,
                            )
                            self.assertEqual(parse(dimensions["text"]), value)
                            self.assertTrue(dimensions["highlighted"])
                            self.assertEqual(dimensions["unsafeElements"], 0)
                            self.assertLessEqual(dimensions["codeScrollWidth"], dimensions["codeWidth"] + 1)
                            self.assertLessEqual(dimensions["contentRight"], dimensions["cardRight"] + 1)
                            self.assertLessEqual(dimensions["textRight"], dimensions["cardRight"] + 1)

    def test_modal_not_rendered(self):
        """As implemented, modal dialog box does not render until activated."""

        self.browser.visit(self.live_server_url)
        # Modal dialog box should not load on page load
        self.assertEqual(len(self.browser.find_by_xpath("//div[@class[contains(., 'modal-backdrop')]]")), 0)

        # Validate only one instance of modal present
        theme_modal = self.browser.find_by_xpath("//div[@id[contains(., 'theme_modal')]]")
        self.assertEqual(len(theme_modal), 1)

        # Validate modal is not visible
        self.assertFalse(theme_modal[0].visible)

    def test_modal_rendered(self):
        """Modal should render when selecting the 'theme' button in the footer."""

        self.browser.visit(self.live_server_url)

        # Validate only one instance of modal present
        self.browser.find_by_xpath(".//a[@id='btn-theme-modal']").click()
        self.assertEqual(len(self.browser.find_by_xpath("//div[@class[contains(., 'modal-backdrop')]]")), 1)

        # Validate modal is visible
        theme_modal = self.browser.find_by_xpath("//div[@id='theme_modal']")
        self.assertTrue(theme_modal[0].is_visible(wait_time=5))

        # Validate 3 themes available to select
        columns = self.browser.find_by_xpath("//div[@class[contains(., 'modal-body')]]//dl/dt")
        self.assertEqual(len(columns), 3)  # 3 columns (light, dark, system)

        # Validate 3 modes in order are light, dark, and system
        self.assertIn("Light", columns[0].html)
        self.assertIn("Dark", columns[1].html)
        self.assertIn("System", columns[2].html)

        # Validate only System theme is selected by default
        light_theme = self.browser.find_by_xpath(".//dd/button[@data-nb-theme='light']")
        self.assertFalse(light_theme[0].has_class("border"))
        self.assertFalse(light_theme[0].has_class("border-primary"))
        dark_theme = self.browser.find_by_xpath(".//dd/button[@data-nb-theme='dark']")
        self.assertFalse(dark_theme[0].has_class("border"))
        self.assertFalse(dark_theme[0].has_class("border-primary"))
        system_theme = self.browser.find_by_xpath(".//dd/button[@data-nb-theme='system']")
        self.assertTrue(system_theme[0].has_class("border"))
        self.assertTrue(system_theme[0].has_class("border-primary"))

        # Why is it required to click the cancel button twice? I honestly don't know, but for some reason Selenium seems
        # to have troubles here. The first press only focuses the cancel button, and only after clicking it for the
        # second time, the modal closes successfully.
        self.browser.find_by_xpath(".//button[@id='dismiss-modal-theme']").click()
        self.browser.find_by_xpath(".//button[@id='dismiss-modal-theme']").click()

        # Validate Modal closes when cancel button clicked
        self.assertTrue(theme_modal[0].is_not_visible(wait_time=5))
