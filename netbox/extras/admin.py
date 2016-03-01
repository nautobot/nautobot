from django.contrib import admin

from .models import Graph, ExportTemplate


@admin.register(Graph)
class GraphAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'weight', 'source']


@admin.register(ExportTemplate)
class ExportTemplateAdmin(admin.ModelAdmin):
    list_display = ['content_type', 'name', 'mime_type', 'file_extension']
