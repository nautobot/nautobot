from nautobot.core.apps import NautobotConfig


class UtilitiesConfig(NautobotConfig):
    name = "nautobot.utilities"

    def ready(self):
        super().ready()

        # Register netutils jinja2 filters in django_jinja and Django Template
        from netutils.utils import jinja2_convenience_function
        from django_jinja import library

        from django import template

        register = template.Library()

        for name, func in jinja2_convenience_function().items():
            # Register in django_jinja
            library.filter(name=name, fn=func)

            # Register in Django Template
            register.filter(name, func)
