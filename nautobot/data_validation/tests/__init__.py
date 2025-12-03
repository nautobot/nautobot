"""Unit tests for data_validation app."""

import contextlib

from django.core.cache import cache
import redis.exceptions

from nautobot.data_validation.models import ValidationRuleModelMixin


class ValidationRuleTestCaseMixin:
    model: type(ValidationRuleModelMixin)

    def tearDown(self):
        """Ensure that validation rule caches are cleared to avoid leakage into other tests."""
        with contextlib.suppress(redis.exceptions.ConnectionError):
            cache.delete_pattern(f"{self.model.objects.get_for_model_cache_key_prefix}(*)")
            cache.delete_pattern(f"{self.model.objects.get_enabled_for_model_cache_key_prefix}(*)")
        if hasattr(super(), "tearDown"):
            super().tearDown()
