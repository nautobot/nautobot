from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from rest_framework import status

from nautobot.dcim.models import Site
from nautobot.extras.models import Tag
from nautobot.utilities.testing import APITestCase, TestCase


class TaggedItemORMTest(TestCase):
    """
    Test the application of tags via the Python API (ORM).
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.site = Site.objects.first()

    def test_tags_set_taggit_1(self):
        """Test that obj.tags.set() works when invoked like django-taggit 1.x."""
        self.site.tags.set("Tag 1", "Tag 2")
        self.assertListEqual(sorted([t.name for t in self.site.tags.all()]), ["Tag 1", "Tag 2"])

        self.site.tags.set(Tag.objects.get(name="Tag 1"))
        self.assertListEqual(sorted([t.name for t in self.site.tags.all()]), ["Tag 1"])

    def test_tags_set_taggit_2(self):
        """Test that obj.tags.set() works when invoked like django-taggit 2.x and later."""
        self.site.tags.set(["Tag 1", "Tag 2"])
        self.assertListEqual(sorted([t.name for t in self.site.tags.all()]), ["Tag 1", "Tag 2"])

        self.site.tags.set([Tag.objects.get(name="Tag 1")])
        self.assertListEqual(sorted([t.name for t in self.site.tags.all()]), ["Tag 1"])


class TaggedItemTest(APITestCase):
    """
    Test the application of Tags to and item (a Site, for example) upon creation (POST) and modification (PATCH).
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.tags = Tag.objects.get_for_model(Site)

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
        self.assertListEqual(sorted([t.name for t in site.tags.all()]), sorted([t.name for t in self.tags]))

    def test_update_tagged_item(self):
        site = Site.objects.first()
        site.tags.add(*self.tags[:3])
        data = {
            "tags": [
                {"name": self.tags[0].name},
                {"name": self.tags[1].name},
                {"name": self.tags[3].name},
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
        self.assertListEqual(
            sorted([t.name for t in site.tags.all()]),
            sorted([self.tags[0].name, self.tags[1].name, self.tags[3].name]),
        )

    def test_clear_tagged_item(self):
        site = Site.objects.first()
        site.tags.add(*self.tags[:3])
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
        tag = self.tags[0]
        tag.content_types.remove(ContentType.objects.get_for_model(Site))
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
