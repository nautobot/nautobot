from markdown import markdown

from django import template
from django.utils.safestring import mark_safe


register = template.Library()


#
# Filters
#

@register.filter(name='oneline')
def oneline(value):
    """
    Replace each line break with a single space
    """
    return value.replace('\n', ' ')


@register.filter(name='getlist')
def getlist(value, arg):
    """
    Return all values of a QueryDict key
    """
    return value.getlist(arg)


@register.filter(name='gfm', is_safe=True)
def gfm(value):
    """
    Render text as GitHub-Flavored Markdown
    """
    html = markdown(value, extensions=['mdx_gfm'])
    return mark_safe(html)


#
# Tags
#

@register.simple_tag(name='querystring_toggle')
def querystring_toggle(request, multi=True, page_key='page', **kwargs):
    """
    Add or remove a parameter in the HTTP GET query string
    """
    new_querydict = request.GET.copy()

    # Remove page number from querystring
    try:
        new_querydict.pop(page_key)
    except KeyError:
        pass

    # Add/toggle parameters
    for k, v in kwargs.items():
        values = new_querydict.getlist(k)
        if k in new_querydict and v in values:
            values.remove(v)
            new_querydict.setlist(k, values)
        elif not multi:
            new_querydict[k] = v
        else:
            new_querydict.update({k: v})

    querystring = new_querydict.urlencode()
    if querystring:
        return '?' + querystring
    else:
        return ''
