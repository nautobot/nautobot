from django.conf import settings
from django.core.checks import Error, Tags, register


E001 = Error(
    "CACHEOPS_DEFAULTS['timeout'] value cannot be 0. To disable caching set CACHEOPS_ENABLED=False.",
    id="nautobot.E001",
)


@register(Tags.caches)
def cache_timeout_check(app_configs, **kwargs):
    if settings.CACHEOPS_DEFAULTS.get("timeout") == 0:
        return [E001]
    return []
