import contextlib

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
import redis.exceptions

from nautobot.data_validation.models import (
    MinMaxValidationRule,
    RegularExpressionValidationRule,
    RequiredValidationRule,
    UniqueValidationRule,
    ValidationRuleManager,
)


@receiver(post_save, sender=MinMaxValidationRule)
@receiver(post_delete, sender=MinMaxValidationRule)
@receiver(post_save, sender=RegularExpressionValidationRule)
@receiver(post_delete, sender=RegularExpressionValidationRule)
@receiver(post_save, sender=RequiredValidationRule)
@receiver(post_delete, sender=RequiredValidationRule)
@receiver(post_save, sender=UniqueValidationRule)
@receiver(post_delete, sender=UniqueValidationRule)
def invalidate_validation_rule_caches(sender, **kwargs):
    for method in [
        ValidationRuleManager.get_for_model,
        ValidationRuleManager.get_enabled_for_model,
    ]:
        with contextlib.suppress(redis.exceptions.ConnectionError):
            cache.delete_pattern(f"{method.cache_key_prefix}.{sender._meta.concrete_model._meta.model_name}.*")
