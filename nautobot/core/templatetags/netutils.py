from django import template
from netutils.utils import jinja2_convenience_function

register = template.Library()

for name, func in jinja2_convenience_function().items():
    # Register as a simple_tag in Django Template context.
    # We use simple_tag() rather than filter() because many netutils functions take more than one arg.
    register.simple_tag(func, name=name)
