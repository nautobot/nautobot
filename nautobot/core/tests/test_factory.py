import itertools

import factory as factoryboy

from nautobot.core import constants, factory, testing


class FactoryTestCase(testing.TestCase):
    """Test Nautobot factory base classes."""

    class TestDictFactory(factoryboy.DictFactory):
        """Dummy factory to run tests that don't require testing database functionality."""

        attribute1 = factory.NautobotBoolIterator(cycle=False, chance_of_getting_true=80, length=10)
        attribute2 = factory.NautobotBoolIterator()

    def test_nautobot_bool_iterator(self):
        """Test nautobot.core.factory.NautobotBoolIterator `cycle`, `chance_of_getting_true` and `length` arguments"""
        probability = constants.NAUTOBOT_BOOL_ITERATOR_DEFAULT_PROBABILITY
        length = constants.NAUTOBOT_BOOL_ITERATOR_DEFAULT_LENGTH
        batch = FactoryTestCase.TestDictFactory.build_batch(10)
        attribute1_result = [obj["attribute1"] for obj in batch]
        attribute2_result = [obj["attribute2"] for obj in batch]
        with self.subTest(r"NautobotBoolIterator, 25% chance of True, length 10"):
            self.assertCountEqual(attribute1_result, list(itertools.repeat(True, 8)) + list(itertools.repeat(False, 2)))
        with self.subTest(f"NautobotBoolIterator, {probability}% chance of True, length {length}"):
            num_true = int(probability / 100 * length)
            num_false = int((100 - probability) / 100 * length)
            expected = list(itertools.repeat(True, num_true)) + list(itertools.repeat(False, num_false))
            self.assertCountEqual(attribute2_result[:length], expected)
        with self.subTest("factory.NautobotBoolIterator cycle=False raises StopIteration"):
            with self.assertRaises(StopIteration):
                FactoryTestCase.TestDictFactory.build()
