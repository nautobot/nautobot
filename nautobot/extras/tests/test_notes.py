from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models.query import QuerySet

from nautobot.core.testing.models import ModelTestCases
from nautobot.dcim.models import Location
from nautobot.extras.models import Note

User = get_user_model()


class NoteModelTest(ModelTestCases.BaseModelTestCase):
    model = Note

    @classmethod
    def setUpTestData(cls):
        location_ct = ContentType.objects.get_for_model(Location)

        user = User.objects.first()

        cls.locations = Location.objects.all()[:2]

        Note.objects.create(
            note="Location has been placed on **maintenance**.",
            user=user,
            assigned_object_type=location_ct,
            assigned_object_id=cls.locations[0].pk,
        )
        Note.objects.create(
            note="Location maintenance has ended.",
            user=user,
            assigned_object_type=location_ct,
            assigned_object_id=cls.locations[0].pk,
        )
        Note.objects.create(
            note="Location is under duress.",
            user=user,
            assigned_object_type=location_ct,
            assigned_object_id=cls.locations[1].pk,
        )

    def test_notes_queryset(self):
        self.assertIsInstance(self.locations[0].notes, QuerySet)
        self.assertEqual(self.locations[0].notes.count(), 2)
        self.assertEqual(self.locations[1].notes.count(), 1)
