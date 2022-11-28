# noinspection PyUnresolvedReferences
from django.core.management.commands.makemigrations import Command
from django.db import models

from nautobot.utilities.management import commands


__all__ = ("Command",)

# Overload deconstruct with our own.
models.Field.deconstruct = commands.custom_deconstruct
