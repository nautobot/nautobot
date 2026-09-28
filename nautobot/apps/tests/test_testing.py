import sys
from unittest import mock

from django.test import SimpleTestCase, tag


@tag("unit")
class AppsTestingTestCase(SimpleTestCase):
    """Tests for import behavior of nautobot.apps.testing module."""

    def setUp(self):
        sys.modules.pop("nautobot.apps.testing", None)
        sys.modules.pop("nautobot.core.testing.integration", None)
        for key in list(sys.modules.keys()):
            if key in ["selenium", "splinter"] or key.startswith(("selenium.", "splinter.")):
                sys.modules.pop(key)

    def test_import_module_without_selenium_or_splinter_succeeds(self):
        real_import = __import__

        def mock_import(name, *args, **kwargs):
            if name.startswith(("selenium", "splinter")):
                raise ImportError("no such module")
            return real_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=mock_import):
            with self.assertRaises(ImportError):
                import selenium  # noqa
            with self.assertRaises(ImportError):
                import splinter  # noqa
            with self.assertRaises(ImportError):
                import nautobot.core.testing.integration

            import nautobot.apps.testing  # must succeed despite no selenium or splinter

            self.assertGreater(len(nautobot.apps.testing.__all__), 0)
            self.assertGreater(len(nautobot.apps.testing._INTEGRATION_NAMES), 0)

            for name in nautobot.apps.testing._INTEGRATION_NAMES:
                self.assertIn(name, nautobot.apps.testing.__all__)
                self.assertIn(name, dir(nautobot.apps.testing))
                with self.assertRaises(ImportError):
                    getattr(nautobot.apps.testing, name)

            for name in nautobot.apps.testing.__all__:
                if name not in nautobot.apps.testing._INTEGRATION_NAMES:
                    getattr(nautobot.apps.testing, name)

            for name in dir(nautobot.apps.testing):
                if name not in nautobot.apps.testing._INTEGRATION_NAMES:
                    getattr(nautobot.apps.testing, name)

    def test_import_module_with_selenium_and_splinter_succeeds(self):
        import nautobot.apps.testing

        self.assertGreater(len(nautobot.apps.testing.__all__), 0)
        self.assertGreater(len(nautobot.apps.testing._INTEGRATION_NAMES), 0)

        for name in nautobot.apps.testing._INTEGRATION_NAMES:
            self.assertIn(name, nautobot.apps.testing.__all__)
            self.assertIn(name, dir(nautobot.apps.testing))
            getattr(nautobot.apps.testing, name)

        for name in nautobot.apps.testing.__all__:
            getattr(nautobot.apps.testing, name)

        for name in dir(nautobot.apps.testing):
            getattr(nautobot.apps.testing, name)
