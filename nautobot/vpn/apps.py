from nautobot.core.apps import NautobotConfig


class VPNConfig(NautobotConfig):
    default = True
    name = "nautobot.vpn"
    verbose_name = "VPNs"
    searchable_models = []
