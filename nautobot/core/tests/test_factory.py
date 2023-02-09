import itertools

import factory

from nautobot.core import testing
from nautobot.core.factory import NautobotBoolIterator


class TestFactory(factory.DictFactory):
    attribute1 = NautobotBoolIterator(cycle=False, chance_of_getting_true=80, length=10)
    attribute2 = NautobotBoolIterator()


class FactoryTestCase(testing.TestCase):
    def test_nautobot_bool_iterator(self):
        batch = TestFactory.build_batch(10)
        attribute1 = [obj["attribute1"] for obj in batch]
        attribute2 = [obj["attribute2"] for obj in batch]
        with self.subTest(r"NautobotBoolIterator, 25% chance of True, length 10"):
            self.assertCountEqual(attribute1, list(itertools.repeat(True, 8)) + list(itertools.repeat(False, 2)))
        with self.subTest(r"NautobotBoolIterator, 50% chance of True, length 8"):
            self.assertCountEqual(attribute2[:8], list(itertools.repeat(True, 4)) + list(itertools.repeat(False, 4)))
        with self.subTest("NautobotBoolIterator cycle=False raises StopIteration"):
            with self.assertRaises(StopIteration):
                TestFactory.build()
