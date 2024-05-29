from nautobot.core.apps import NautobotConfig


class CircuitsConfig(NautobotConfig):
    default = True
    name = "nautobot.circuits"
    verbose_name = "Circuits"
    searchable_models = [
        "circuit",
        "provider",
        "providernetwork",
    ]

    def ready(self):
        super().ready()
        import nautobot.circuits.signals  # noqa: F401  # unused-import -- but this import installs the signals
