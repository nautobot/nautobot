import django_tables2 as tables

from django.utils.safestring import mark_safe


class ToggleColumn(tables.CheckBoxColumn):
    default = ''
    visible = False

    @property
    def header(self):
        return mark_safe('<input type="checkbox" name="_all" title="Select all" />')
