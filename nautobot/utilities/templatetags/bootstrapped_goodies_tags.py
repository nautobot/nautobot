from importlib import import_module

from django import template
from django.conf import settings
from django.template.loader import render_to_string


register = template.Library()


CUSTOM_FIELD_RENDERER = getattr(settings, 'DAB_FIELD_RENDERER', False)


@register.simple_tag(takes_context=True)
def render_with_template_if_exist(context, template, fallback):
    text = fallback
    try:
        text = render_to_string(template, context)
    except:
        pass
    return text

@register.simple_tag(takes_context=True)
def language_selector(context):
    """ displays a language selector dropdown in the admin, based on Django "LANGUAGES" context.
        requires:
            * USE_I18N = True / settings.py
            * LANGUAGES specified / settings.py (otherwise all Django locales will be displayed)
            * "set_language" url configured (see https://docs.djangoproject.com/en/dev/topics/i18n/translation/#the-set-language-redirect-view)
    """
    output = ""
    i18 = getattr(settings, 'USE_I18N', False)
    if i18:
        template = "admin/language_selector.html"
        context['i18n_is_set'] = True
        try:
            output = render_to_string(template, context)
        except:
            pass
    return output


@register.filter(name='column_width')
def column_width(value):
    try:
        return 12 // len(list(value))
    except ZeroDivisionError:
        return 12


@register.filter(name='form_fieldset_column_width')
def form_fieldset_column_width(form):
    def max_line(fieldset):
        try:
            return max([len(list(line)) for line in fieldset])
        # This ValueError is for case that fieldset has no line.
        except ValueError:
            return 0

    try:
        width = max([max_line(fieldset) for fieldset in form])
        return 12 // width
    except ValueError:
        return 12


@register.filter(name='fieldset_column_width')
def fieldset_column_width(fieldset):
    try:
        width = max([len(list(line)) for line in fieldset])
        return 12 // width
    except ValueError:
        return 12


@register.simple_tag(takes_context=True)
def render_app_name(context, app, template="/admin_app_name.html"):
    """ Render the application name using the default template name. If it cannot find a
        template matching the given path, fallback to the application name.
    """
    try:
        template = app['app_label'] + template
        text = render_to_string(template, context)
    except:
        text = app['name']
    return text


@register.simple_tag(takes_context=True)
def render_app_label(context, app, fallback=""):
    """ Render the application label.
    """
    try:
        text = app['app_label']
    except KeyError:
        text = fallback
    except TypeError:
        text = app
    return text


@register.simple_tag(takes_context=True)
def render_app_description(context, app, fallback="", template="/admin_app_description.html"):
    """ Render the application description using the default template name. If it cannot find a
        template matching the given path, fallback to the fallback argument.
    """
    try:
        template = app['app_label'] + template
        text = render_to_string(template, context)
    except:
        text = fallback
    return text


@register.simple_tag(takes_context=True, name="dab_field_rendering")
def custom_field_rendering(context, field, *args, **kwargs):
    """ Wrapper for rendering the field via an external renderer """
    if CUSTOM_FIELD_RENDERER:
        mod, cls = CUSTOM_FIELD_RENDERER.rsplit(".", 1)
        field_renderer = getattr(import_module(mod), cls)
        if field_renderer:
            return field_renderer(field, **kwargs).render()
    return field
