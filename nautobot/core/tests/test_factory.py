import itertools

import factory

from nautobot.core import testing
from nautobot.core.factory import NautobotBoolIterator


class FactoryTestCase(testing.TestCase):
    """Test Nautobot factory base classes."""

    class TestDictFactory(factory.DictFactory):
        """Dummy factory to run tests that don't require testing database functionality."""

        attribute1 = NautobotBoolIterator(cycle=False, chance_of_getting_true=80, length=10)
        attribute2 = NautobotBoolIterator()

    def test_nautobot_bool_iterator(self):
        batch = FactoryTestCase.TestDictFactory.build_batch(10)
        attribute1 = [obj["attribute1"] for obj in batch]
        attribute2 = [obj["attribute2"] for obj in batch]
        with self.subTest(r"NautobotBoolIterator, 25% chance of True, length 10"):
            self.assertCountEqual(attribute1, list(itertools.repeat(True, 8)) + list(itertools.repeat(False, 2)))
        with self.subTest(r"NautobotBoolIterator, 50% chance of True, length 8"):
            self.assertCountEqual(attribute2[:8], list(itertools.repeat(True, 4)) + list(itertools.repeat(False, 4)))
        with self.subTest("NautobotBoolIterator cycle=False raises StopIteration"):
            with self.assertRaises(StopIteration):
                FactoryTestCase.TestDictFactory.build()
