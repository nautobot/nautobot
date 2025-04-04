from nautobot.core.apps import NautobotConfig


class WirelessConfig(NautobotConfig):
    default = True
    name = "nautobot.wireless"
    verbose_name = "Wireless"
    searchable_models = []
