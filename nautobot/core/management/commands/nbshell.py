from django import get_version
from django.apps import apps
from django.conf import settings
from django_extensions.management.commands.shell_plus import Command as _Command

from nautobot import __version__


class Command(_Command):
    """Lightweight extension/wrapper for the django-extensions 'shell_plus' command."""

    def get_imported_objects(self, options):
        """Import all app models and related code."""
        imported_objects = super().get_imported_objects(options)
        if not options.get("quiet_load"):
            # Add some additional info for the user
            # style.SQL_TABLE is an odd choice, but it's consistent with django-extensions...
            self.stdout.write(self.style.SQL_TABLE(f"# Django version {get_version()}"))
            self.stdout.write(self.style.SQL_TABLE(f"# Nautobot version {__version__}"))
            for full_app_name in settings.PLUGINS:
                app_name = full_app_name.rsplit(".", 1)[-1]
                app_config = apps.get_app_config(app_name)
                self.stdout.write(
                    self.style.SQL_TABLE(f"# {app_config.verbose_name} version {app_config.version or '(unknown)'}")
                )
        return imported_objects
