from django.apps import apps
from django.test import TestCase

from nautobot.core.models.utils import find_models_with_matching_fields
from nautobot.extras.models import RelationshipAssociation
from nautobot.extras.registry import Registry, registry
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

    def test_lookup_by_field(self):
        """Assert lookup_by_field returns the expected values"""

        with self.subTest("Test for model features with field_attributes"):
            relationships_registry = find_models_with_matching_fields(
                app_models=apps.get_models(),
                field_names=["source_for_associations", "destination_for_associations"],
                field_attributes={"related_model": RelationshipAssociation},
            )
            self.assertEqual(relationships_registry, registry["model_features"]["relationships"])

        with self.subTest("Test for model features without field_attributes"):
            custom_fields_registry = find_models_with_matching_fields(
                app_models=apps.get_models(), field_names=["_custom_field_data"]
            )
            self.assertEqual(custom_fields_registry, registry["model_features"]["custom_fields"])
