from nautobot.core.apps import NautobotConfig


class DCIMConfig(NautobotConfig):
    name = "nautobot.dcim"
    verbose_name = "DCIM"
    searchable_models = [
        "location",
        "rack",
        "rackgroup",
        "devicetype",
        "device",
        "virtualchassis",
        "cable",
        "powerfeed",
    ]

    def ready(self):
        super().ready()
        import nautobot.dcim.signals  # noqa: F401
