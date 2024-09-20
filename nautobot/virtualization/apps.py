from nautobot.core.apps import NautobotConfig


class VirtualizationConfig(NautobotConfig):
    default = True
    name = "nautobot.virtualization"
    searchable_models = [
        "cluster",
        "virtualmachine",
    ]

    def ready(self):
        super().ready()
        import nautobot.virtualization.signals  # noqa: F401  # unused-import -- but this import installs the signals
