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

        def test_composite_key(self):
            """Check that `composite_key` and filtering by `composite_key` both work."""
            instance = self.model.objects.first()
            self.assertIsNotNone(instance)
            if not hasattr(instance, "composite_key"):
                self.skipTest("No composite_key on this model.")
            self.assertIsNotNone(instance.composite_key)
            self.assertEqual(self.model.objects.get(composite_key=instance.composite_key), instance)
