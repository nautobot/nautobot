from nautobot.core.apps import NautobotConfig


class TenancyConfig(NautobotConfig):
    name = "nautobot.tenancy"
    searchable_models = ["tenant"]
