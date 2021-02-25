from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "nautobot.users"
    verbose_name = "Users"

    def ready(self):
        import nautobot.users.signals  # noqa: F401
