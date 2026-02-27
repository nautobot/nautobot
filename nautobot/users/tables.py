from django.contrib.admin.models import DELETION
from django.core.exceptions import ObjectDoesNotExist
from django.urls import NoReverseMatch
from django.utils.html import escape, format_html
import django_tables2 as tables

from nautobot.core.tables import BaseTable, ChoiceFieldColumn

from .models import LogEntry


class LogEntryTable(BaseTable):
    action_time = tables.Column(linkify=True)
    action_flag = ChoiceFieldColumn(verbose_name="Action")
    object_link = tables.Column(empty_values=(), verbose_name="Object")

    class Meta(BaseTable.Meta):
        model = LogEntry
        fields = ("action_time", "user", "content_type", "object_link", "action_flag")
        default_columns = fields

    def render_object_link(self, record):
        if record.action_flag == DELETION:
            return escape(record.object_repr)
        try:
            edited_object = record.get_edited_object()
        except ObjectDoesNotExist:
            edited_object = None
        if edited_object is not None and hasattr(edited_object, "get_absolute_url"):
            try:
                return format_html('<a href="{}">{}</a>', edited_object.get_absolute_url(), record.object_repr)
            except (AttributeError, NoReverseMatch):
                # Some models inherit a default get_absolute_url() that raises when no URL exists.
                pass
        try:
            admin_url = record.get_admin_url()
            if admin_url:
                return format_html('<a href="{}">{}</a>', admin_url, record.object_repr)
        except (AttributeError, NoReverseMatch):
            pass
        return escape(record.object_repr)
