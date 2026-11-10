from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from nautobot.core.utils.cache import invalidate_cache
from nautobot.data_validation.models import (
    MinMaxValidationRule,
    RegularExpressionValidationRule,
    RequiredValidationRule,
    UniqueValidationRule,
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
    invalidate_cache(
        patterns=[
            f"{prefix}(*)"
            for prefix in (
                sender.objects.get_for_model_cache_key_prefix,
                sender.objects.get_enabled_for_model_cache_key_prefix,
            )
        ]
    )
