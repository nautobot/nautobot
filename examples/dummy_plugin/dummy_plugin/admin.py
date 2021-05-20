from django.contrib import admin

from nautobot.core.admin import admin_site
from .models import DummyModel


@admin.register(DummyModel, site=admin_site)
class DummyModelAdmin(admin.ModelAdmin):
    list_display = ("name", "number")
