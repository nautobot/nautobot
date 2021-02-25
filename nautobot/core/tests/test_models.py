from django.core.exceptions import ValidationError

from nautobot.core.models import BaseModel
from nautobot.utilities.testing import TestCase


class BaseModelTest(TestCase):
    class FakeBaseModel(BaseModel):
        def clean(self):
            raise ValidationError("validation error")

    def test_validated_save_calls_full_clean(self):
        with self.assertRaises(ValidationError):
            self.FakeBaseModel().validated_save()
