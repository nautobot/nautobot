from django.apps import AppConfig


class SpectacularConfig(AppConfig):
    name = 'nautobot.third_party.drf_spectacular'
    verbose_name = "drf-spectacular"

    def ready(self):
        import nautobot.third_party.drf_spectacular.checks  # noqa: F401
