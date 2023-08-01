import time

from unittest.mock import patch

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import override_settings

from nautobot.core.models import BaseModel
from nautobot.utilities.testing import TestCase


class BaseModelTest(TestCase):
    class FakeBaseModel(BaseModel):
        def clean(self):
            raise ValidationError("validation error")

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
