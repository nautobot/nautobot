from django.contrib import admin

from nautobot.apps.admin import NautobotModelAdmin

from example_plugin.models import ExampleModel


@admin.register(ExampleModel)
class ExampleModelAdmin(NautobotModelAdmin):
    list_display = ("name", "number")
