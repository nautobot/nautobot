from unittest import TestCase
from unittest.mock import MagicMock

import astroid

from nautobot.utilities.pylint import ModelExistenceChecker


class TestModelExistenceChecker(TestCase):
    def test_model_existence(self):
        node = astroid.extract_node(
            """
        if instance.pk:
            pass
        """
        )
        linter = MagicMock()
        checker = ModelExistenceChecker(linter=linter)
        checker.visit_if(node)
        linter.add_message.assert_called_with(
            "wrong-presence-check",
            2,
            node,
            None,
            None,
            3,
            None,
            None,
        )
