from nautobot.core.apps import NautobotConfig


class IPAMConfig(NautobotConfig):
    name = "nautobot.ipam"
    verbose_name = "IPAM"
