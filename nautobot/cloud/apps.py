from nautobot.core.apps import NautobotConfig


class CloudConfig(NautobotConfig):
    name = "nautobot.cloud"
    verbose_name = "Cloud"
    searchable_models = ["cloudaccount"]
