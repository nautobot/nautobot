import time
from unittest import skip
from unittest.mock import patch
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.test.utils import isolate_apps

from nautobot.core.models import BaseModel
from nautobot.core.models.utils import construct_composite_key, construct_natural_slug, deconstruct_composite_key
from nautobot.core.testing import TestCase
from nautobot.dcim.models import DeviceType, Location, LocationType, Manufacturer
from nautobot.extras.models import Status, Tag

User = get_user_model()


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

            time.sleep(3)  # Let the cache expire

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


class RestrictedQuerySetTestCase(TestCase):
    """Tests for RestrictedQuerySet.restrict() and check_perms()."""

    @classmethod
    def setUpTestData(cls):
        cls.location_type = LocationType.objects.get(name="Campus")
        cls.status = Status.objects.get_for_model(Location).first()
        cls.locations = [
            Location.objects.create(
                name=f"restrict-test-{i}",
                location_type=cls.location_type,
                status=cls.status,
            )
            for i in range(3)
        ]

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_restrict_superuser_returns_all(self):
        """Superusers should bypass all permission restrictions."""
        self.user.is_superuser = True
        self.user.save()
        qs = Location.objects.restrict(self.user, "view")
        self.assertTrue(qs.filter(pk=self.locations[0].pk).exists())

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_restrict_unauthenticated_returns_none(self):
        """An unauthenticated/anonymous user should get an empty queryset."""

        anon = AnonymousUser()
        qs = Location.objects.restrict(anon, "view")
        self.assertEqual(qs.count(), 0)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_restrict_no_permission_returns_none(self):
        """A user with no relevant permissions should get an empty queryset."""
        qs = Location.objects.restrict(self.user, "view")
        self.assertEqual(qs.count(), 0)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_restrict_unconstrained_permission(self):
        """An ObjectPermission with null constraints should return all objects of the model."""
        self.add_permissions("dcim.view_location")
        qs = Location.objects.restrict(self.user, "view")
        self.assertEqual(qs.count(), Location.objects.count())

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_restrict_with_simple_constraint(self):
        """An ObjectPermission with a name constraint should filter correctly."""
        self.add_permissions("dcim.view_location", constraints={"name": self.locations[0].name})
        qs = Location.objects.restrict(self.user, "view")
        self.assertEqual(list(qs), [self.locations[0]])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_restrict_with_multiple_constraint_sets(self):
        """An ObjectPermission with a list of constraints (OR'd together) should return the union."""
        self.add_permissions(
            "dcim.view_location",
            constraints=[
                {"name": self.locations[0].name},
                {"name": self.locations[1].name},
            ],
        )
        qs = Location.objects.restrict(self.user, "view")
        self.assertEqual(set(qs), {self.locations[0], self.locations[1]})

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_restrict_with_tag_constraint_single_matching_tag(self):
        """A tag-based constraint should work when an object has a single matching tag."""
        location_ct = ContentType.objects.get_for_model(Location)
        tag = Tag.objects.create(name="PAN_site1")
        tag.content_types.add(location_ct)

        self.locations[0].tags.add(tag)

        self.add_permissions("dcim.view_location", constraints={"tags__name__regex": "^PAN_.+$"})
        qs = Location.objects.restrict(self.user, "view")
        self.assertEqual(list(qs), [self.locations[0]])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_restrict_with_tag_constraint_multiple_matching_tags_no_duplicates(self):
        """
        A tag-based constraint should not return duplicate objects when an object has multiple
        tags that all match the constraint regex.

        Regression test for https://github.com/nautobot/nautobot/issues/8690
        """
        location_ct = ContentType.objects.get_for_model(Location)
        tag1 = Tag.objects.create(name="PAN_XXX")
        tag1.content_types.add(location_ct)
        tag2 = Tag.objects.create(name="OT_PAN_XXX")
        tag2.content_types.add(location_ct)

        # Tag one location with BOTH matching tags
        self.locations[0].tags.add(tag1, tag2)

        self.add_permissions("dcim.view_location", constraints={"tags__name__regex": "^(PAN_|OT_PAN_).+$"})
        qs = Location.objects.restrict(self.user, "view")

        # The queryset should contain the location exactly once, not once per matching tag
        self.assertEqual(qs.count(), 1)
        self.assertEqual(list(qs), [self.locations[0]])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_check_perms_with_tag_constraint_multiple_matching_tags(self):
        """
        check_perms() should return True (not raise MultipleObjectsReturned) when an object
        has multiple tags matching the permission constraint.

        Regression test for https://github.com/nautobot/nautobot/issues/8690
        """
        location_ct = ContentType.objects.get_for_model(Location)
        tag1 = Tag.objects.create(name="PAN_YYY")
        tag1.content_types.add(location_ct)
        tag2 = Tag.objects.create(name="OT_PAN_YYY")
        tag2.content_types.add(location_ct)

        self.locations[0].tags.add(tag1, tag2)

        self.add_permissions(
            "dcim.view_location",
            "dcim.change_location",
            constraints={"tags__name__regex": "^(PAN_|OT_PAN_).+$"},
        )

        # check_perms should work without error for both actions
        self.assertTrue(Location.objects.check_perms(self.user, instance=self.locations[0], action="view"))
        self.assertTrue(Location.objects.check_perms(self.user, instance=self.locations[0], action="change"))
        # An untagged location should not be permitted
        self.assertFalse(Location.objects.check_perms(self.user, instance=self.locations[1], action="view"))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_restrict_with_tag_constraint_mixed_matching_and_nonmatching(self):
        """Only objects whose tags match the constraint should be returned, regardless of other tags."""
        location_ct = ContentType.objects.get_for_model(Location)
        matching_tag = Tag.objects.create(name="PAN_match")
        matching_tag.content_types.add(location_ct)
        nonmatching_tag = Tag.objects.create(name="unrelated_tag")
        nonmatching_tag.content_types.add(location_ct)

        # Location 0: has a matching tag
        self.locations[0].tags.add(matching_tag)
        # Location 1: has only a non-matching tag
        self.locations[1].tags.add(nonmatching_tag)
        # Location 2: no tags

        self.add_permissions("dcim.view_location", constraints={"tags__name__regex": "^PAN_.+$"})
        qs = Location.objects.restrict(self.user, "view")
        self.assertEqual(list(qs), [self.locations[0]])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["dcim.location"])
    def test_restrict_exempt_permission(self):
        """Exempt view permissions should bypass restriction."""
        qs = Location.objects.restrict(self.user, "view")
        self.assertEqual(qs.count(), Location.objects.count())

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_restrict_action_scoping(self):
        """A permission for 'view' should not grant 'change' access."""
        self.add_permissions("dcim.view_location")
        view_qs = Location.objects.restrict(self.user, "view")
        change_qs = Location.objects.restrict(self.user, "change")
        self.assertGreater(view_qs.count(), 0)
        self.assertEqual(change_qs.count(), 0)
