from nautobot.core.apps import NautobotConfig


class CircuitsConfig(NautobotConfig):
    name = "nautobot.circuits"
    verbose_name = "Circuits"

    def ready(self):
        super().ready()
        import nautobot.circuits.signals  # noqa: F401
