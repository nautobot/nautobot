from __future__ import absolute_import

from django.contrib.auth.forms import ReadOnlyPasswordHashWidget
from django.contrib.admin.widgets import (AdminDateWidget, AdminTimeWidget,
                                          AdminSplitDateTime, RelatedFieldWidgetWrapper)
from django.forms import (FileInput, CheckboxInput, RadioSelect, CheckboxSelectMultiple)

from bootstrap3 import renderers
try:
    from bootstrap3.utils import add_css_class
except ImportError:
    from bootstrap3.html import add_css_class
from bootstrap3.text import text_value

class BootstrapFieldRenderer(renderers.FieldRenderer):
    """
    A django-bootstrap3 field renderer that renders just the field
    """
    def render(self):
        # Hidden input requires no special treatment
        if self.field.is_hidden:
            return text_value(self.field)
        # Render the widget
        self.add_widget_attrs()
        html = self.field.as_widget(attrs=self.widget.attrs)
        return html

    def add_class_attrs(self, widget=None):
        if not widget:
            widget = self.widget

        # for multiwidgets we recursively update classes for each sub-widget
        if isinstance(widget, AdminSplitDateTime):
            for w in widget.widgets:
                self.add_class_attrs(w)
            return

        classes = widget.attrs.get('class', '')
        if isinstance(widget, ReadOnlyPasswordHashWidget):
            classes = add_css_class(classes, 'form-control-static', prepend=True)
        elif isinstance(widget, (AdminDateWidget,
                                 AdminTimeWidget,
                                 RelatedFieldWidgetWrapper)):
            # for some admin widgets we don't want the input to take full horizontal space
            classes = add_css_class(classes, 'form-control form-control-inline', prepend=True)
        elif not isinstance(widget, (CheckboxInput,
                                     RadioSelect,
                                     CheckboxSelectMultiple,
                                     FileInput)):
            classes = add_css_class(classes, 'form-control', prepend=True)
            # For these widget types, add the size class here
            classes = add_css_class(classes, self.get_size_class())
        widget.attrs['class'] = classes
