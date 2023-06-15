from django.core.exceptions import ValidationError
from django.test.utils import isolate_apps

from nautobot.core.models import BaseModel
from nautobot.core.models.utils import construct_composite_key, deconstruct_composite_key
from nautobot.core.testing import TestCase
from nautobot.dcim.models import DeviceType, Manufacturer


@isolate_apps("nautobot.core.tests")
class BaseModelTest(TestCase):
    class FakeBaseModel(BaseModel):
        def clean(self):
            raise ValidationError("validation error")

    def test_validated_save_calls_full_clean(self):
        with self.assertRaises(ValidationError):
            self.FakeBaseModel().validated_save()


class ModelUtilsTestCase(TestCase):
    def test_construct_deconstruct_composite_key(self):
        """Test that construct_composite_key() and deconstruct_composite_key() work and are symmetric."""
        for values, expected_slug in (
            (["alpha"], "alpha"),  # simplest case
            (["alpha", "beta"], "alpha;beta"),  # multiple inputs
            (["10.1.1.1/24", "fe80::1"], "10.1.1.1%2F24;fe80::1"),  # URL-safe ASCII characters, / is *not* path safe
            ([None, "Hello", None], "%00;Hello;%00"),  # Null values
            (["💩", "Everyone's favorite!"], "%F0%9F%92%A9;Everyone%27s+favorite%21"),  # Emojis and unsafe ASCII
        ):
            with self.subTest(values=values):
                slug = construct_composite_key(values)
                self.assertEqual(slug, expected_slug)
                self.assertEqual(deconstruct_composite_key(slug), values)


class NaturalKeyTestCase(TestCase):
    """Test the various natural-key APIs for a few representative models."""

    def test_natural_key(self):
        """Test the natural_key() default implementation with some representative models."""
        # Simple case - single unique field becomes the natural key
        mfr = Manufacturer.objects.first()
        self.assertEqual(mfr.natural_key(), [mfr.name])
        # Derived case - unique_together plus a nested lookup
        dt = DeviceType.objects.first()
        self.assertEqual(dt.natural_key(), [dt.manufacturer.name, dt.model])

    def test_composite_key(self):
        """Test the composite_key default implementation with some representative models."""
        mfr = Manufacturer.objects.first()
        self.assertEqual(mfr.composite_key, construct_composite_key(mfr.natural_key()))
        dt = DeviceType.objects.first()
        self.assertEqual(dt.composite_key, construct_composite_key(dt.natural_key()))

    def test_natural_key_field_lookups(self):
        """Test the natural_key_field_lookups default implementation with some representative models."""
        self.assertEqual(Manufacturer.natural_key_field_lookups, ["name"])
        self.assertEqual(DeviceType.natural_key_field_lookups, ["manufacturer__name", "model"])

    def test_natural_key_args_to_kwargs(self):
        """Test the natural_key_args_to_kwargs() default implementation with some representative models."""
        self.assertEqual(Manufacturer.natural_key_args_to_kwargs(["myname"]), {"name": "myname"})
        self.assertEqual(
            DeviceType.natural_key_args_to_kwargs(["mymanufacturer", "mymodel"]),
            {"manufacturer__name": "mymanufacturer", "model": "mymodel"},
        )
