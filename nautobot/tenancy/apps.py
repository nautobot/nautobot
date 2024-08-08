from nautobot.core.apps import NautobotConfig


class TenancyConfig(NautobotConfig):
    default = True
    name = "nautobot.tenancy"
    searchable_models = ["tenant"]
