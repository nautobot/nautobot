from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models.query import QuerySet

from nautobot.dcim.models import Site
from nautobot.extras.models import Notes
from nautobot.utilities.testing import TestCase


User = get_user_model()


class NotesModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):

        cls.site_ct = ContentType.objects.get_for_model(Site)
        cls.notes_ct = ContentType.objects.get_for_model(Notes)

        cls.user = User.objects.first()

        cls.sites = [
            Site.objects.create(name="Site 1", slug="site-1"),
            Site.objects.create(name="Site 2", slug="site-2"),
        ]

        cls.notes = [
            Notes.objects.create(
                name="Site Maintenance",
                note="Site has been placed on **maintenance**.",
                user=cls.user,
                assigned_object_type=cls.site_ct,
                assigned_object_id=cls.sites[0].pk,
            ),
            Notes.objects.create(
                name="Site Maintenance End",
                note="Site maintenance has ended.",
                user=cls.user,
                assigned_object_type=cls.site_ct,
                assigned_object_id=cls.sites[0].pk,
            ),
            Notes.objects.create(
                name="Site Trouble",
                note="Site is under duress.",
                user=cls.user,
                assigned_object_type=cls.site_ct,
                assigned_object_id=cls.sites[1].pk,
            ),
        ]

    def test_notes_queryset(self):
        self.assertIsInstance(self.sites[0].notes, QuerySet)
        self.assertEqual(self.sites[0].notes.count(), 2)
        self.assertEqual(self.sites[1].notes.count(), 1)
