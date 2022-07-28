from django.urls import reverse

from nautobot.dcim.models import Site
from nautobot.utilities.testing.integration import SeleniumTestCase


class NoteTestCase(SeleniumTestCase):
    """
    Integration test to check nautobot.extras.models.notes view, add and markdown functionality.
    """

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_create_and_update(self):
        """
        Test initial add and then update of a new Note
        """
        Site.objects.create(name="Site 1", slug="site-1")

        # Navigate to the created site.
        self.browser.visit(f'{self.live_server_url}{reverse("dcim:site", kwargs={"slug": "site-1"})}')

        # Verify notes tab shows up and click it.
        self.assertTrue(self.browser.links.find_by_partial_href("/dcim/sites/site-1/notes/"))
        self.browser.links.find_by_partial_href("/dcim/sites/site-1/notes/").click()

        # Fill out the form.
        self.browser.fill("note", "This is a maintenance notice.")

        # Click that "Create" button
        self.browser.find_by_text("Create").click()

        # Verify form redirect and presence of content.
        self.assertTrue(self.browser.is_text_present("Created Note"))
