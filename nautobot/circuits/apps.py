from nautobot.core.apps import NautobotConfig


class CircuitsConfig(NautobotConfig):
    name = "nautobot.circuits"
    verbose_name = "Circuits"
    searchable_models = [
        "provider",
        "circuit",
        "providernetwork",
    ]

    def ready(self):
        super().ready()
        import nautobot.circuits.signals  # noqa: F401
