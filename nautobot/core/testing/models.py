from django.test import tag, TestCase

from nautobot.core.templatetags.helpers import get_docs_url


@tag("unit")
class ModelTestCases:
    class BaseModelTestCase(TestCase):
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
