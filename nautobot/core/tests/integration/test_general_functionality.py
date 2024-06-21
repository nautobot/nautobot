from django.urls import reverse

from nautobot.core.testing.integration import SeleniumTestCase


class StaticMediaFailureTestCase(SeleniumTestCase):
    """Integration test to make sure no static media failures are encountered."""

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        self.login(self.user.username, self.password)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_for_static_media_failure(self):
        test_urls = [
            reverse("home"),
            reverse("api-root"),
            reverse("graphql"),
            reverse("api_docs"),
            "/admin/",
            "/static/docs/index.html",
        ]
        for url in test_urls:
            with self.subTest(test_url=url):
                self.browser.visit(self.live_server_url + url)
                # Wait for body element to appear
                self.assertTrue(self.browser.is_element_present_by_tag("body", wait_time=10), "Page failed to load")
                # Ensure we weren't redirected to another page
                self.assertEqual(self.browser.url, self.live_server_url + url)
                self.assertTrue(self.browser.is_text_not_present("Static Media Failure"))
