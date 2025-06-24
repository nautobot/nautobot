import time
from unittest import skip
from unittest.mock import patch
import uuid

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.test.utils import isolate_apps

from nautobot.core.models import BaseModel
from nautobot.core.models.utils import construct_composite_key, construct_natural_slug, deconstruct_composite_key
from nautobot.core.testing import TestCase
from nautobot.dcim.models import DeviceType, Location, LocationType, Manufacturer
from nautobot.extras.models import Status


@isolate_apps("nautobot.core.tests")
class BaseModelTest(TestCase):
    class FakeBaseModel(BaseModel):
        def clean(self):
            raise ValidationError("validation error")

    def test_validated_save_calls_full_clean(self):
        with self.assertRaises(ValidationError):
            self.FakeBaseModel().validated_save()


class ModelUtilsTestCase(TestCase):
    @skip("Composite keys aren't being supported at this time")
    def test_construct_deconstruct_composite_key(self):
        """Test that construct_composite_key() and deconstruct_composite_key() work and are symmetric."""
        for values, expected_composite_key in (
            (["alpha"], "alpha"),  # simplest case
            (["alpha", "beta"], "alpha;beta"),  # multiple inputs
            (["10.1.1.1/24", "fe80::1"], "10.1.1.1%2F24;fe80::1"),  # URL-safe ASCII characters, / is *not* path safe
            ([None, "Hello", None], "%00;Hello;%00"),  # Null values
            (["💩", "Everyone's favorite!"], "%F0%9F%92%A9;Everyone%27s+favorite%21"),  # Emojis and unsafe ASCII
        ):
            with self.subTest(values=values):
                composite_key = construct_composite_key(values)
                self.assertEqual(composite_key, expected_composite_key)
                self.assertEqual(deconstruct_composite_key(composite_key), values)

    def test_construct_natural_slug(self):
        """Test that `construct_natural_slug()` works as expected."""
        pk = uuid.uuid4()
        pk4 = str(pk)[:4]
        for values, expected_natural_slug in (
            (["Alpha"], "alpha"),  # simplest case
            (["alpha", "beta"], "alpha_beta"),  # multiple inputs
            (["Über Ålpha"], "uber-alpha"),  # accents/ligatures
            (["10.1.1.1/24", "fe80::1"], "10-1-1-1-24_fe80-1"),  # URL-safe ASCII characters, / is *not* path safe
            ([None, "Hello", None], "_hello_"),  # Null values
            (["💩", "Everyone's favorite!"], "pile-of-poo_everyone-s-favorite"),  # Emojis and unsafe ASCII
        ):
            with self.subTest(values=values):
                expected_natural_slug += f"_{pk4}"
                natural_slug = construct_natural_slug(values, pk=pk)
                self.assertEqual(natural_slug, expected_natural_slug)


class NaturalKeyTestCase(BaseModelTest):
    """Test the various natural-key APIs for a few representative models."""

    def test_natural_key(self):
        """Test the natural_key() default implementation with some representative models."""
        # Simple case - single unique field becomes the natural key
        mfr = Manufacturer.objects.first()
        self.assertEqual(mfr.natural_key(), [mfr.name])
        # Derived case - unique_together plus a nested lookup
        dt = DeviceType.objects.first()
        self.assertEqual(dt.natural_key(), [dt.manufacturer.name, dt.model])

    def test_natural_key_with_proxy_model(self):
        """Test that natural_key_field_lookups function returns the same value as its base class."""

        class ProxyManufacturer(Manufacturer):
            class Meta:
                proxy = True

        self.assertEqual(ProxyManufacturer.natural_key_field_lookups, Manufacturer.natural_key_field_lookups)

    @skip("Composite keys aren't being supported at this time")
    def test_composite_key(self):
        """Test the composite_key default implementation with some representative models."""
        mfr = Manufacturer.objects.first()
        self.assertEqual(mfr.composite_key, construct_composite_key(mfr.natural_key()))
        dt = DeviceType.objects.first()
        self.assertEqual(dt.composite_key, construct_composite_key(dt.natural_key()))

    def test_natural_slug(self):
        """Test the natural_slug default implementation with some representative models."""
        mfr = Manufacturer.objects.first()
        self.assertEqual(mfr.natural_slug, construct_natural_slug(mfr.natural_key(), pk=mfr.pk))
        dt = DeviceType.objects.first()
        self.assertEqual(dt.natural_slug, construct_natural_slug(dt.natural_key(), pk=dt.pk))

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

    def test__content_type(self):
        """
        Verify that the ContentType of the object is cached.
        """
        self.assertEqual(self.FakeBaseModel._content_type, self.FakeBaseModel._content_type_cached)

    @override_settings(CONTENT_TYPE_CACHE_TIMEOUT=2)
    def test__content_type_caching_enabled(self):
        """
        Verify that the ContentType of the object is cached.
        """

        # Ensure the cache is empty from previous tests
        cache.delete(self.FakeBaseModel._content_type_cache_key)

        with patch.object(self.FakeBaseModel, "_content_type", return_value=True) as mock__content_type:
            self.FakeBaseModel._content_type_cached
            self.FakeBaseModel._content_type_cached
            self.FakeBaseModel._content_type_cached
            self.assertEqual(mock__content_type.call_count, 1)

            time.sleep(2)  # Let the cache expire

            self.FakeBaseModel._content_type_cached
            self.assertEqual(mock__content_type.call_count, 2)

        # Clean-up after ourselves
        cache.delete(self.FakeBaseModel._content_type_cache_key)

    @override_settings(CONTENT_TYPE_CACHE_TIMEOUT=0)
    def test__content_type_caching_disabled(self):
        """
        Verify that the ContentType of the object is not cached.
        """

        # Ensure the cache is empty from previous tests
        cache.delete(self.FakeBaseModel._content_type_cache_key)

        with patch.object(self.FakeBaseModel, "_content_type", return_value=True) as mock__content_type:
            self.FakeBaseModel._content_type_cached
            self.FakeBaseModel._content_type_cached
            self.assertEqual(mock__content_type.call_count, 2)


class TreeModelTestCase(TestCase):
    """Tests for the behavior of tree models, using Location as a representative model."""

    def test_values(self):
        """Test that `.values()` works properly (https://github.com/nautobot/nautobot/issues/4812)."""
        queryset = Location.objects.filter(name="Campus-01")
        instance = queryset.first()
        values_dict = queryset.values().first()
        model_dict = queryset.first().__dict__
        values_subset_dict = queryset.values("id", "name", "last_updated").first()

        for key, value in values_dict.items():
            with self.subTest(description="values()", key=key):
                self.assertEqual(value, getattr(instance, key))

        for key, value in model_dict.items():
            if key.startswith("_"):
                continue
            with self.subTest(description="__dict__", key=key):
                self.assertEqual(value, getattr(instance, key))

        for key, value in values_subset_dict.items():
            with self.subTest(description="values(key, key, key...)", key=key):
                self.assertEqual(value, getattr(instance, key))

    def test_tree_max_depth(self):
        """Test that tree_max_depth() and the max_depth cached property are calculated correctly."""
        max_tree_depth = max(loc.tree_depth for loc in Location.objects.all().with_tree_fields())
        self.assertEqual(max_tree_depth, Location.objects.all().max_tree_depth())
        self.assertEqual(max_tree_depth, Location.objects.max_depth)

        # Add a new tree so that the max depth increases
        location_type = LocationType.objects.get(name="Campus")  # root type and infinitely nestable
        status = Status.objects.get_for_model(Location).first()
        loc = None
        for i in range(max_tree_depth + 2):
            loc = Location.objects.create(
                name=f"Nested Campus {i}", parent=loc, location_type=location_type, status=status
            )
        self.assertEqual(max_tree_depth + 1, Location.objects.all().max_tree_depth())
        self.assertEqual(max_tree_depth + 1, Location.objects.max_depth)

        # Delete the most-nested location so that the max depth decreases
        loc.delete()
        self.assertEqual(max_tree_depth, Location.objects.all().max_tree_depth())
        self.assertEqual(max_tree_depth, Location.objects.max_depth)
