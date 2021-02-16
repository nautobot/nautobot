from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "users"
    verbose_name = "Users"

    def ready(self):
        import users.signals
