from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from rest_framework import status

from nautobot.dcim.models import Site, Device
from nautobot.extras.models import Status, Tag
from nautobot.utilities.testing import APITestCase


class TaggedItemTest(APITestCase):
    """
    Test the application of Tags to and item (a Site, for example) upon creation (POST) and modification (PATCH).
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.tags = cls.create_tags("Foo", "Bar", "Baz", "New Tag")
        for tag in cls.tags:
            tag.content_types.add(ContentType.objects.get_for_model(Site))

    def test_create_tagged_item(self):
        data = {
            "name": "Test Site",
            "slug": "test-site",
            "status": "active",
            "tags": [str(t.pk) for t in self.tags],
        }
        url = reverse("dcim-api:site-list")
        self.add_permissions("dcim.add_site")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertListEqual(sorted([t["id"] for t in response.data["tags"]]), sorted(data["tags"]))
        site = Site.objects.get(pk=response.data["id"])
        self.assertListEqual(sorted([t.name for t in site.tags.all()]), sorted(["Foo", "Bar", "Baz", "New Tag"]))

    def test_update_tagged_item(self):
        site = Site.objects.create(
            name="Test Site",
            slug="test-site",
            status=Status.objects.get(slug="active"),
        )
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

    def test_create_invalid_tagged_item(self):
        """Test creating a Site with a tag that does not include Site's Content type as its content_type"""
        tag = Tag.objects.create(name="Tag One", slug="tag-one")
        app_label, model = Device._meta.label_lower.split(".")
        tag.content_types.add(ContentType.objects.get(app_label=app_label, model=model))
        data = {
            "name": "Test Site",
            "slug": "test-site",
            "status": "active",
            "tags": [tag.id],
        }
        url = reverse("dcim-api:site-list")
        self.add_permissions("dcim.add_site")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Related object not found", str(response.data["tags"]))
