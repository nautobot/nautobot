from unittest import TestCase

from nautobot.core import celery


class CeleryTest(TestCase):
    def test__dumps(self):
        self.assertEqual('"I am UTF-8! 😀"', celery._dumps("I am UTF-8! 😀"))
