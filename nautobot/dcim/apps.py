from django.apps import AppConfig


class DCIMConfig(AppConfig):
    name = "nautobot.dcim"
    verbose_name = "DCIM"

    def ready(self):

        import nautobot.dcim.signals  # noqa: F401
