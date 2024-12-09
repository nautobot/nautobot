import time

from unittest.mock import patch

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.test import override_settings, skipUnlessDBFeature

from nautobot.core.models import BaseModel
from nautobot.utilities.testing import TestCase


class BaseModelTest(TestCase):
    class FakeBaseModel(BaseModel):
        def clean(self):
            raise ValidationError("validation error")

    class JSONFieldModel(BaseModel):
        data = models.JSONField(null=True)

        class Meta:
            required_db_features = {"supports_json_field"}

    def test_validated_save_calls_full_clean(self):
        with self.assertRaises(ValidationError):
            self.FakeBaseModel().validated_save()

    def test__content_type(self):
        """
        Verify that the ContentType of the object is cached.
        """
        self.assertEqual(self.FakeBaseModel._content_type, self.FakeBaseModel._content_type_cached)

    @override_settings(CONTENT_TYPE_CACHE_TIMEOUT=2)
    def test__content_type_caching_enabled(self):
        """
        Verify that the ContentType of the object is cached.
        """

        # Ensure the cache is empty from previous tests
        cache.delete(f"{self.FakeBaseModel._meta.label_lower}._content_type")

        with patch.object(self.FakeBaseModel, "_content_type", return_value=True) as mock__content_type:
            self.FakeBaseModel._content_type_cached
            self.FakeBaseModel._content_type_cached
            self.FakeBaseModel._content_type_cached
            self.assertEqual(mock__content_type.call_count, 1)

            time.sleep(2)  # Let the cache expire

            self.FakeBaseModel._content_type_cached
            self.assertEqual(mock__content_type.call_count, 2)

        # Clean-up after ourselves
        cache.delete(f"{self.FakeBaseModel._meta.label_lower}._content_type")

    @override_settings(CONTENT_TYPE_CACHE_TIMEOUT=0)
    def test__content_type_caching_disabled(self):
        """
        Verify that the ContentType of the object is not cached.
        """

        # Ensure the cache is empty from previous tests
        cache.delete(f"{self.FakeBaseModel._meta.label_lower}._content_type")

        with patch.object(self.FakeBaseModel, "_content_type", return_value=True) as mock__content_type:
            self.FakeBaseModel._content_type_cached
            self.FakeBaseModel._content_type_cached
            self.assertEqual(mock__content_type.call_count, 2)

    @skipUnlessDBFeature("supports_json_field")
    def test_values_expression_alias_sql_injection_json_field(self):
        crafted_alias = """injected_name" from "expressions_company"; --"""
        msg = "Column aliases cannot contain whitespace characters, quotation marks, semicolons, or SQL comments."
        with self.assertRaisesMessage(ValueError, msg):
            self.JSONFieldModel.objects.values(f"data__{crafted_alias}")
        with self.assertRaisesMessage(ValueError, msg):
            self.JSONFieldModel.objects.values_list(f"data__{crafted_alias}")
