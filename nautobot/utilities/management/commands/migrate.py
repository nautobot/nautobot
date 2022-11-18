# noinspection PyUnresolvedReferences
from django.core.management.commands.migrate import Command  # noqa: F401
from django.db import models

from nautobot.utilities.management import commands


# Overload deconstruct with our own.
models.Field.deconstruct = commands.custom_deconstruct
