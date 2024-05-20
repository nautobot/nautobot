from nautobot.core.apps import NautobotConfig


class UsersConfig(NautobotConfig):
    default = True
    name = "nautobot.users"
    verbose_name = "Users"
