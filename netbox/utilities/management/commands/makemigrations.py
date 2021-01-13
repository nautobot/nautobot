# noinspection PyUnresolvedReferences
from django.conf import settings
from django.core.management.base import CommandError
from django.core.management.commands.makemigrations import Command as _Command
from django.db import models

from . import custom_deconstruct

models.Field.deconstruct = custom_deconstruct


class Command(_Command):

    def handle(self, *args, **kwargs):
        """
        This built-in management command enables the creation of new database schema migration files, which should
        never be required by and ordinary user. We prevent this command from executing unless the configuration
        indicates that the user is a developer (i.e. configuration.DEVELOPER == True).
        """
        if not settings.DEVELOPER:
            raise CommandError(
                "This command is only available when running as a developer.\n"
                "This should only be used when developing new functionality with Nautobot,\n"
                "and should not be used on production instances.\n"
                "If you are trying to develop new features, then set the DEVELOPER variable\n"
                "in the configuration.py file to True.\n"
                "If you are having issues with missing or unapplied migrations,\n"
                "please raise an issue on GitHub."  # TODO: Add full URL of project
            )

        super().handle(*args, **kwargs)
