from nautobot.core.apps import NautobotConfig


class VirtualizationConfig(NautobotConfig):
    name = "nautobot.virtualization"

    def ready(self):
        super().ready()
        import nautobot.virtualization.signals  # noqa: F401
