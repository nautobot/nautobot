from nautobot.core.apps import NautobotConfig


class UsersConfig(NautobotConfig):
    default = True
    name = "nautobot.users"
    verbose_name = "Users"

    # Flag for version control app to skip versioning user app models
    is_version_controlled = False
