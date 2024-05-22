from nautobot.core.apps import NautobotConfig


class CircuitsConfig(NautobotConfig):
    name = "nautobot.cloud"
    verbose_name = "Cloud"
    searchable_models = ["cloudaccount"]
