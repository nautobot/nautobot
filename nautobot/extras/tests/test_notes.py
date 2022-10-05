from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models.query import QuerySet

from nautobot.dcim.models import Site
from nautobot.extras.models import Note
from nautobot.utilities.testing import TestCase


User = get_user_model()


class NoteModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):

        site_ct = ContentType.objects.get_for_model(Site)

        user = User.objects.first()

        cls.sites = Site.objects.all()[:2]

        Note.objects.create(
            note="Site has been placed on **maintenance**.",
            user=user,
            assigned_object_type=site_ct,
            assigned_object_id=cls.sites[0].pk,
        )
        Note.objects.create(
            note="Site maintenance has ended.",
            user=user,
            assigned_object_type=site_ct,
            assigned_object_id=cls.sites[0].pk,
        )
        Note.objects.create(
            note="Site is under duress.",
            user=user,
            assigned_object_type=site_ct,
            assigned_object_id=cls.sites[1].pk,
        )

    def test_notes_queryset(self):
        self.assertIsInstance(self.sites[0].notes, QuerySet)
        self.assertEqual(self.sites[0].notes.count(), 2)
        self.assertEqual(self.sites[1].notes.count(), 1)
