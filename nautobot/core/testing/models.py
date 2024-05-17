from django.db.models import QuerySet
from django.test import tag, TestCase

from nautobot.core.templatetags.helpers import get_docs_url
from nautobot.core.testing.mixins import NautobotTestCaseMixin
from nautobot.extras.models import StaticGroup, StaticGroupAssociation


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

        def test_static_group_api(self):
            """For static-group capable models, check that they work as intended."""
            if getattr(self.model, "is_static_group_associable_model", False):
                self.assertTrue(hasattr(self.model, "associated_static_groups"))
                self.assertIsInstance(self.model.objects.first().associated_static_groups.all(), QuerySet)
                self.assertEqual(
                    self.model.objects.first().associated_static_groups.all().model, StaticGroupAssociation
                )

                self.assertTrue(hasattr(self.model, "static_groups"))
                self.assertIsInstance(self.model.objects.first().static_groups, QuerySet)
                self.assertEqual(self.model.objects.first().static_groups.model, StaticGroup)

                if StaticGroup.objects.get_for_model(self.model).exists():
                    sg = StaticGroup.objects.get_for_model(self.model).first()
                    self.assertEqual(sg.members.model, self.model)
