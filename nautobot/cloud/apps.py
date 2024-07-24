from nautobot.core.apps import NautobotConfig


class CloudConfig(NautobotConfig):
    default = True
    name = "nautobot.cloud"
    verbose_name = "Cloud"
    searchable_models = [
        "cloudaccount",
        "cloudnetwork",
        "cloudresourcetype",
        "cloudservice",
    ]
