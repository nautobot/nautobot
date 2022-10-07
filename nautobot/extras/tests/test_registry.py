from django.test import TestCase

from nautobot.extras.registry import Registry
from nautobot.extras.secrets import register_secrets_provider
from nautobot.extras.secrets.providers import EnvironmentVariableSecretsProvider


class RegistryTest(TestCase):
    def setUp(self):
        self.reg = Registry()

    def test_add_store(self):
        self.reg["foo"] = 123

        self.assertEqual(self.reg["foo"], 123)

    def test_manipulate_store(self):
        self.reg["foo"] = [1, 2]
        self.reg["foo"].append(3)

        self.assertListEqual(self.reg["foo"], [1, 2, 3])

    def test_overwrite_store(self):
        self.reg["foo"] = 123

        with self.assertRaises(KeyError):
            self.reg["foo"] = 456

    def test_delete_store(self):
        self.reg["foo"] = 123

        with self.assertRaises(TypeError):
            del self.reg["foo"]

    def test_register_secrets_provider_input_validation(self):
        # Wrong data type
        with self.assertRaises(TypeError):
            register_secrets_provider("a string is not a SecretsProvider")
        with self.assertRaises(TypeError):
            # Need to register a class, not a class instance
            # For some reason pylint thinks EnvironmentVariableSecretsProvider is a partially abstract class; it isn't
            instance = EnvironmentVariableSecretsProvider()  # pylint: disable=abstract-class-instantiated
            register_secrets_provider(instance)

        # Duplicate slug
        class DuplicateSecretsProvider(EnvironmentVariableSecretsProvider):
            pass

        with self.assertRaises(KeyError):
            register_secrets_provider(DuplicateSecretsProvider)
