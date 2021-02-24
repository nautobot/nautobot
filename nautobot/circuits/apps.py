from django.apps import AppConfig


class CircuitsConfig(AppConfig):
    name = "nautobot.circuits"
    verbose_name = "Circuits"

    def ready(self):
        import nautobot.circuits.signals  # noqa: F401
