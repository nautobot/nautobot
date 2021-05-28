from nautobot.core.app import NautobotConfig


class DCIMConfig(NautobotConfig):
    name = "nautobot.dcim"
    verbose_name = "DCIM"

    def ready(self):
        super().ready()
        import nautobot.dcim.signals  # noqa: F401
