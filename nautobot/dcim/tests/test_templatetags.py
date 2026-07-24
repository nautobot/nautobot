from unittest.mock import Mock

from nautobot.core.testing import TestCase
from nautobot.dcim.templatetags.cables import termination_type_icon


class TerminationTypeIconTestCase(TestCase):
    """Direct unit tests for the `termination_type_icon` template tag."""

    def test_returns_help_icon_for_none(self):
        self.assertEqual(termination_type_icon(None), "mdi-help-circle-outline")

    def test_returns_known_icon_per_model_name(self):
        """Each registered model_name maps to its specific MDI icon class."""
        expected = {
            "interface": "mdi-ethernet",
            "frontport": "mdi-arrow-right-bold-box-outline",
            "rearport": "mdi-arrow-left-bold-box-outline",
            "consoleport": "mdi-console",
            "consoleserverport": "mdi-console-network-outline",
            "powerport": "mdi-power-plug-outline",
            "poweroutlet": "mdi-power-socket",
            "powerfeed": "mdi-flash",
            "circuittermination": "mdi-cable-data",
        }
        for model_name, icon in expected.items():
            with self.subTest(model_name=model_name):
                termination = Mock()
                termination._meta.model_name = model_name
                self.assertEqual(termination_type_icon(termination), icon)

    def test_returns_default_icon_for_unknown_model(self):
        """Any model_name not in the icon map falls back to the generic cable-data icon."""
        termination = Mock()
        termination._meta.model_name = "somethingunregistered"
        self.assertEqual(termination_type_icon(termination), "mdi-cable-data")
