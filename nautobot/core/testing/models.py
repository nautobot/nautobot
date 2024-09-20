from django.db.models import QuerySet
from django.test import tag, TestCase

from nautobot.core.templatetags.helpers import get_docs_url
from nautobot.core.testing.mixins import NautobotTestCaseMixin
from nautobot.extras.models import DynamicGroup, StaticGroupAssociation


@tag("unit")
class ModelTestCases:
    class BaseModelTestCase(NautobotTestCaseMixin, TestCase):
        """Base class for generic model tests."""

        model = None

        def test_natural_key_symmetry(self):
            """Check that `natural_key()` and `get_by_natural_key()` work reciprocally."""
            instance = self.model.objects.first()
            self.assertIsNotNone(instance)
            if not hasattr(instance, "natural_key"):
                self.skipTest("No natural_key on this model.")
            self.assertIsNotNone(instance.natural_key())
            self.assertEqual(self.model.objects.get_by_natural_key(*instance.natural_key()), instance)

        def test_composite_key(self):
            """Check that `composite_key` and filtering by `composite_key` both work."""
            instance = self.model.objects.first()
            self.assertIsNotNone(instance)
            if not hasattr(instance, "composite_key"):
                self.skipTest("No composite_key on this model.")
            self.assertIsNotNone(instance.composite_key)
            # get()
            self.assertEqual(self.model.objects.get(composite_key=instance.composite_key), instance)
            # filter()
            match = self.model.objects.filter(composite_key=instance.composite_key)
            self.assertEqual(1, len(match))
            self.assertEqual(match[0], instance)
            # exclude()
            match = self.model.objects.exclude(composite_key=instance.composite_key)
            self.assertEqual(self.model.objects.count() - 1, match.count())
            self.assertNotIn(instance, match)

        def test_get_docs_url(self):
            """Check that `get_docs_url()` returns a valid static file path for this model."""
            self.assertIsNotNone(get_docs_url(self.model))

        def test_dynamic_group_api(self):
            """For dynamic-group capable models, check that they work as intended."""
            if not getattr(self.model, "is_dynamic_group_associable_model", False):
                self.skipTest("Not a dynamic group associable model.")

            self.assertTrue(hasattr(self.model, "dynamic_groups"))
            self.assertIsInstance(self.model.objects.first().dynamic_groups, QuerySet)
            self.assertEqual(self.model.objects.first().dynamic_groups.model, DynamicGroup)

            if DynamicGroup.objects.get_for_model(self.model).exists():
                dg = DynamicGroup.objects.get_for_model(self.model).first()
                self.assertEqual(dg.members.model, self.model)

            # Models using DynamicGroupMixin w/o DynamicGroupsModelMixin will not have static_group_association_set
            if hasattr(self.model, "static_group_association_set"):
                self.assertIsInstance(self.model.objects.first().static_group_association_set.all(), QuerySet)
                self.assertEqual(
                    self.model.objects.first().static_group_association_set.all().model, StaticGroupAssociation
                )
