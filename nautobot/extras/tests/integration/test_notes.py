from django.urls import reverse

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.models import Location, LocationType


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
        location_type, _ = LocationType.objects.get_or_create(name="Campus")
        Location.objects.create(name="Location 1", slug="location-1", location_type=location_type)

        # Navigate to the created location.
        self.browser.visit(f'{self.live_server_url}{reverse("dcim:location", kwargs={"slug": "location-1"})}')

        # Verify notes tab shows up and click it.
        self.assertTrue(self.browser.links.find_by_partial_href("/dcim/locations/location-1/notes/"))
        self.browser.links.find_by_partial_href("/dcim/locations/location-1/notes/").click()

        # Fill out the form.
        self.browser.fill("note", "This is a maintenance notice.")

        # Click that "Create" button
        self.browser.find_by_text("Create").click()

        # Verify form redirect and presence of content.
        self.assertTrue(self.browser.is_text_present("Created Note"))
