from django.urls import reverse
from rest_framework import status

from nautobot.dcim.models import Site
from nautobot.extras.models import Status
from nautobot.utilities.testing import APITestCase


class TaggedItemTest(APITestCase):
    """
    Test the application of Tags to and item (a Site, for example) upon creation (POST) and modification (PATCH).
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # for tag in tags:
        #     tag.content_types.add(ContentType.objects.get_for_model(Site))

    def test_create_tagged_item(self):
        tags = self.create_tags("Foo", "Bar", "Baz")
        data = {
            "name": "Test Site",
            "slug": "test-site",
            "status": "active",
            "tags": [str(t.pk) for t in tags],
        }
        url = reverse("dcim-api:site-list")
        self.add_permissions("dcim.add_site")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertListEqual(sorted([t["id"] for t in response.data["tags"]]), sorted(data["tags"]))
        site = Site.objects.get(pk=response.data["id"])
        self.assertListEqual(sorted([t.name for t in site.tags.all()]), sorted(["Foo", "Bar", "Baz"]))

    def test_update_tagged_item(self):
        site = Site.objects.create(
            name="Test Site",
            slug="test-site",
            status=Status.objects.get(slug="active"),
        )
        self.create_tags("New Tag", "Foo", "Bar", "Baz")
        site.tags.add("Foo", "Bar", "Baz")
        data = {
            "tags": [
                {"name": "Foo"},
                {"name": "Bar"},
                {"name": "New Tag"},
            ]
        }
        self.add_permissions("dcim.change_site")
        url = reverse("dcim-api:site-detail", kwargs={"pk": site.pk})

        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertListEqual(
            sorted([t["name"] for t in response.data["tags"]]),
            sorted([t["name"] for t in data["tags"]]),
        )
        site = Site.objects.get(pk=response.data["id"])
        self.assertListEqual(sorted([t.name for t in site.tags.all()]), sorted(["Foo", "Bar", "New Tag"]))

    def test_clear_tagged_item(self):
        site = Site.objects.create(
            name="Test Site",
            slug="test-site",
            status=Status.objects.get(slug="active"),
        )
        site.tags.add("Foo", "Bar", "Baz")
        data = {"tags": []}
        self.add_permissions("dcim.change_site")
        url = reverse("dcim-api:site-detail", kwargs={"pk": site.pk})

        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(len(response.data["tags"]), 0)
        site = Site.objects.get(pk=response.data["id"])
        self.assertEqual(len(site.tags.all()), 0)
