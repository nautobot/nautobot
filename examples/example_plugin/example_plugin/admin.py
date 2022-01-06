from django.contrib import admin

from nautobot.core.admin import admin_site

from example_plugin.models import ExampleModel


@admin.register(ExampleModel, site=admin_site)
class ExampleModelAdmin(admin.ModelAdmin):
    list_display = ("name", "number")
