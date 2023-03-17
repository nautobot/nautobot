from django.test import tag, TestCase


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

        def test_natural_key_slug(self):
            """Check that `natural_key_slug` and filtering by `natural_key_slug` both work."""
            instance = self.model.objects.first()
            self.assertIsNotNone(instance)
            if not hasattr(instance, "natural_key"):
                self.skipTest("No natural_key on this model.")
            if not hasattr(instance, "natural_key_slug"):
                self.skipTest("No natural_key_slug on this model.")
            self.assertIsNotNone(instance.natural_key_slug)
            self.assertEqual(self.model.objects.get(natural_key_slug=instance.natural_key_slug), instance)
