# noinspection PyUnresolvedReferences
from django.core.management.commands.makemigrations import Command  # noqa: F401  # unused-import
from django.db import models

from nautobot.core.management import commands

# Overload deconstruct with our own.
models.Field.deconstruct = commands.custom_deconstruct
