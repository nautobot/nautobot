# noinspection PyUnresolvedReferences
from django.core.management.commands.makemigrations import Command
from django.db import models

from . import custom_deconstruct

__all__ = ("Command",)

# Overload deconstruct with our own.
models.Field.deconstruct = custom_deconstruct
