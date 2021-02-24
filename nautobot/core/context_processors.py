from django.conf import settings as django_settings

from nautobot.extras.registry import registry


def settings_and_registry(request):
    """
    Expose Django settings and Nautobot registry stores in the template context. Example: {{ settings.DEBUG }}
    """
    return {
        "settings": django_settings,
        "registry": registry,
    }
