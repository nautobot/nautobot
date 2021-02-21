# noinspection PyUnresolvedReferences
from django.core.management.commands.migrate import Command
from django.db import models

from . import custom_deconstruct

# Overload deconstruct with our own.
models.Field.deconstruct = custom_deconstruct
