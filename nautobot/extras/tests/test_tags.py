from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from rest_framework import status

from nautobot.core.testing import APITestCase, TestCase
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.models import Status, Tag


class TaggedItemORMTest(TestCase):
    """
    Test the application of tags via the Python API (ORM).
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()

    def test_tags_set_taggit_2(self):
        """Test that obj.tags.set() works when invoked like django-taggit 2.x and later."""
        self.location.tags.set(["Tag 1", "Tag 2"])
        self.assertListEqual(sorted([t.name for t in self.location.tags.all()]), ["Tag 1", "Tag 2"])

        self.location.tags.set([Tag.objects.get(name="Tag 1")])
        self.assertListEqual(sorted([t.name for t in self.location.tags.all()]), ["Tag 1"])


class TaggedItemTest(APITestCase):
    """
    Test the application of Tags to and item (a Location, for example) upon creation (POST) and modification (PATCH).
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.tags = Tag.objects.get_for_model(Location)
        cls.location_type = LocationType.objects.get(name="Campus")

    def test_create_tagged_item(self):
        data = {
            "name": "Test Location",
            "status": Status.objects.get_for_model(Location).first().pk,
            "tags": [str(t.pk) for t in self.tags],
            "location_type": self.location_type.pk,
        }
        url = reverse("dcim-api:location-list")
        self.add_permissions("dcim.add_location")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        # response with default depth is a list of tag URLs
        self.assertEqual(
            sorted([rt["url"] for rt in response.data["tags"]]), sorted([self.absolute_api_url(t) for t in self.tags])
        )
        location = Location.objects.get(pk=response.data["id"])
        self.assertListEqual(sorted([t.name for t in location.tags.all()]), sorted([t.name for t in self.tags]))

    def test_update_tagged_item(self):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        location.tags.add(*self.tags[:3])
        data = {
            "tags": [
                {"name": self.tags[0].name},
                {"name": self.tags[1].name},
                {"name": self.tags[3].name},
            ]
        }
        self.add_permissions("dcim.change_location")
        url = reverse("dcim-api:location-detail", kwargs={"pk": location.pk})

        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        # response with default depth is a list of tag URLs
        self.assertListEqual(
            sorted([rt["url"] for rt in response.data["tags"]]),
            sorted([self.absolute_api_url(t) for t in [self.tags[0], self.tags[1], self.tags[3]]]),
        )
        location = Location.objects.get(pk=response.data["id"])
        self.assertListEqual(
            sorted([t.name for t in location.tags.all()]),
            sorted([self.tags[0].name, self.tags[1].name, self.tags[3].name]),
        )

    def test_clear_tagged_item(self):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        location.tags.add(*self.tags[:3])
        data = {"tags": []}
        self.add_permissions("dcim.change_location")
        url = reverse("dcim-api:location-detail", kwargs={"pk": location.pk})

        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(len(response.data["tags"]), 0)
        location = Location.objects.get(pk=response.data["id"])
        self.assertEqual(len(location.tags.all()), 0)

    def test_create_invalid_tagged_item(self):
        """Test creating a Location with a tag that does not include Location's Content type as its content_type"""
        tag = self.tags[0]
        tag.content_types.remove(ContentType.objects.get_for_model(Location))
        data = {
            "name": "Test Location",
            "status": Status.objects.get_for_model(Location).first().pk,
            "tags": [tag.id],
            "location_type": self.location_type.pk,
        }
        url = reverse("dcim-api:location-list")
        self.add_permissions("dcim.add_location")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Related object not found", str(response.data["tags"]))
