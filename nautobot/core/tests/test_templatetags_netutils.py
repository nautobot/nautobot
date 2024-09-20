import inspect

from django.template import Context, Engine
from django.template.exceptions import TemplateSyntaxError
from django.test import TestCase
from netutils.utils import jinja2_convenience_function


class NautobotTemplateTagsNetutilsTest(TestCase):
    """Test the use of netutils functions as Django template filters."""

    def test_netutils_filters_in_django(self):
        """Verify that each function is at least available as a filter."""
        engine = Engine.get_default()
        context = Context({})
        for filter_name, filter_func in jinja2_convenience_function().items():
            with self.subTest(f'Testing filter "{filter_name}"'):
                template_string = "{% load netutils %}{% " + filter_name
                signature = inspect.signature(filter_func)
                i = 1
                for param_name, param in signature.parameters.items():
                    template_string += f" {param_name}="
                    if param.annotation is str:
                        template_string += f'"{i}"'
                    elif param.annotation is bool:
                        template_string += "True"
                    elif param.annotation in (int, float):
                        template_string += str(i)
                    elif param.annotation in (list, tuple):
                        template_string += "[]"
                    elif param.annotation is dict:
                        template_string += "{}"
                    else:
                        template_string += "None"
                    i += 1
                template_string += " %}"
                template = engine.from_string(template_string)
                try:
                    template.render(context)
                except TemplateSyntaxError as exc:
                    # Django doesn't see this as a valid template-tag, or similar - shouldn't happen
                    self.fail(str(exc))
                except (AttributeError, KeyError, TypeError, ValueError):
                    # We didn't pass "valid" params to the function, but at least Django saw it as a template tag.
                    pass
                except ConnectionError:
                    # Yes, some netutils functions such as tcp_ping actually make network calls when invoked. Eeek.
                    pass
                except Exception:  # noqa: S110  # try-except-pass -- an antipattern in general, but OK here
                    # Catch-all - at least it wasn't a TemplateSyntaxError, so good enough for now.
                    pass
