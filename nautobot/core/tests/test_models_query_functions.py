from nautobot.core.models.query_functions import JSONRemove, JSONSet
from nautobot.core.testing import TestCase
from nautobot.dcim.models import Manufacturer


class JSONFuncTests(TestCase):
    """Test JSONSet and JSONRemove functionality."""

    def test_json_set(self):
        # Setting a key/value should efficiently work
        with self.assertNumQueries(1):
            Manufacturer.objects.all().update(_custom_field_data=JSONSet("_custom_field_data", "a", 1))
        for mfr in Manufacturer.objects.all():
            self.assertIn("a", mfr._custom_field_data)
            self.assertEqual(1, mfr._custom_field_data["a"])

        # Setting a different key/value shouldn't overwrite other keys
        with self.assertNumQueries(1):
            Manufacturer.objects.all().update(_custom_field_data=JSONSet("_custom_field_data", "b", "text"))
        for mfr in Manufacturer.objects.all():
            self.assertIn("a", mfr._custom_field_data)
            self.assertEqual(1, mfr._custom_field_data["a"])
            self.assertIn("b", mfr._custom_field_data)
            self.assertEqual("text", mfr._custom_field_data["b"])

        # Setting a key/value again should overwrite that value only
        with self.assertNumQueries(1):
            Manufacturer.objects.all().update(_custom_field_data=JSONSet("_custom_field_data", "b", "more text"))
        for mfr in Manufacturer.objects.all():
            self.assertIn("a", mfr._custom_field_data)
            self.assertEqual(1, mfr._custom_field_data["a"])
            self.assertIn("b", mfr._custom_field_data)
            self.assertEqual("more text", mfr._custom_field_data["b"])

        # A filtered query should be updatable
        with self.assertNumQueries(1):
            Manufacturer.objects.filter(name__istartswith="a").update(
                _custom_field_data=JSONSet("_custom_field_data", "a", None)
            )
        for mfr in Manufacturer.objects.filter(name__istartswith="a"):
            self.assertIn("a", mfr._custom_field_data)
            self.assertEqual(None, mfr._custom_field_data["a"])
        for mfr in Manufacturer.objects.exclude(name__istartswith="a"):
            self.assertIn("a", mfr._custom_field_data)
            self.assertEqual(1, mfr._custom_field_data["a"])
        for mfr in Manufacturer.objects.all():
            self.assertIn("b", mfr._custom_field_data)
            self.assertEqual("more text", mfr._custom_field_data["b"])

        # Setting a value doesn't require all existing values to be homogeneous
        with self.assertNumQueries(1):
            Manufacturer.objects.all().update(_custom_field_data=JSONSet("_custom_field_data", "a", "hello"))
        for mfr in Manufacturer.objects.all():
            self.assertIn("a", mfr._custom_field_data)
            self.assertEqual("hello", mfr._custom_field_data["a"])
            self.assertIn("b", mfr._custom_field_data)
            self.assertEqual("more text", mfr._custom_field_data["b"])

    def test_json_remove(self):
        Manufacturer.objects.all().update(_custom_field_data=JSONSet("_custom_field_data", "a", 1))
        Manufacturer.objects.filter(name__istartswith="a").update(
            _custom_field_data=JSONSet("_custom_field_data", "b", "hello")
        )
        Manufacturer.objects.exclude(name__istartswith="a").update(
            _custom_field_data=JSONSet("_custom_field_data", "b", "world")
        )

        # Should be able to clear all values for a key without impacting other keys
        with self.assertNumQueries(1):
            Manufacturer.objects.all().update(_custom_field_data=JSONRemove("_custom_field_data", "a"))
        for mfr in Manufacturer.objects.all():
            self.assertNotIn("a", mfr._custom_field_data)
            self.assertIn("b", mfr._custom_field_data)
        for mfr in Manufacturer.objects.filter(name__istartswith="a"):
            self.assertEqual("hello", mfr._custom_field_data["b"])
        for mfr in Manufacturer.objects.exclude(name__istartswith="a"):
            self.assertEqual("world", mfr._custom_field_data["b"])

        # Clearing a value that doesn't exist should be safe
        with self.assertNumQueries(1):
            Manufacturer.objects.all().update(_custom_field_data=JSONRemove("_custom_field_data", "a"))
        for mfr in Manufacturer.objects.all():
            self.assertNotIn("a", mfr._custom_field_data)
            self.assertIn("b", mfr._custom_field_data)
        for mfr in Manufacturer.objects.filter(name__istartswith="a"):
            self.assertEqual("hello", mfr._custom_field_data["b"])
        for mfr in Manufacturer.objects.exclude(name__istartswith="a"):
            self.assertEqual("world", mfr._custom_field_data["b"])

        # Subsets should be updateable
        with self.assertNumQueries(1):
            Manufacturer.objects.filter(name__istartswith="a").update(
                _custom_field_data=JSONRemove("_custom_field_data", "b")
            )
        for mfr in Manufacturer.objects.all():
            self.assertNotIn("a", mfr._custom_field_data)
        for mfr in Manufacturer.objects.filter(name__istartswith="a"):
            self.assertNotIn("b", mfr._custom_field_data)
        for mfr in Manufacturer.objects.exclude(name__istartswith="a"):
            self.assertIn("b", mfr._custom_field_data)
            self.assertEqual("world", mfr._custom_field_data["b"])

        # Non-homogeneous data should be updatable
        with self.assertNumQueries(1):
            Manufacturer.objects.all().update(_custom_field_data=JSONRemove("_custom_field_data", "b"))
        for mfr in Manufacturer.objects.all():
            self.assertNotIn("a", mfr._custom_field_data)
            self.assertNotIn("b", mfr._custom_field_data)
