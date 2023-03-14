from nautobot.core.apps import NautobotConfig


class UtilitiesConfig(NautobotConfig):
    name = "nautobot.utilities"

    def ready(self):
        super().ready()

        # Register netutils jinja2 filters in django_jinja
        from netutils.utils import jinja2_convenience_function
        from django_jinja import library

        for name, func in jinja2_convenience_function().items():
            # Register in django_jinja
            library.filter(name=name, fn=func)
