from django.core.exceptions import ValidationError

from nautobot.core.models import BaseModel
from nautobot.core.models.utils import construct_natural_key_slug, deconstruct_natural_key_slug
from nautobot.core.testing import TestCase


class BaseModelTest(TestCase):
    class FakeBaseModel(BaseModel):
        def clean(self):
            raise ValidationError("validation error")

    def test_validated_save_calls_full_clean(self):
        with self.assertRaises(ValidationError):
            self.FakeBaseModel().validated_save()


class ModelUtilsTestCase(TestCase):
    def test_construct_deconstruct_natural_key_slug(self):
        """Test that construct_natural_key_slug() and deconstruct_natural_key_slug() work and are symmetric."""
        for values, expected_slug in (
            (["alpha"], "alpha"),  # simplest case
            (["alpha", "beta"], "alpha&beta"),  # multiple inputs
            (["10.1.1.1/24", "fe80::1"], "10.1.1.1%2F24&fe80::1"),  # URL-safe ASCII characters, / is *not* path safe
            ([None, "Hello", None], "%00&Hello&%00"),  # Null values
            (["💩", "Everyone's favorite!"], "%F0%9F%92%A9&Everyone%27s+favorite%21"),  # Emojis and unsafe ASCII
        ):
            with self.subTest(values=values):
                slug = construct_natural_key_slug(values)
                self.assertEqual(slug, expected_slug)
                self.assertEqual(deconstruct_natural_key_slug(slug), values)
