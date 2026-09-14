"""Compiles condition expressions.

A condition source - a preset's constant or a user's raw expression - is one Jinja2 expression, not a
template. It is compiled in a read-only copy of the sandboxed environment that renders webhook body
templates, so the same filters are available, plus `field_value` and `field_matches` from this package.

Compiled expressions are cached by source text. A preset used by many rules compiles once per
process; a user's raw expression compiles once until the process restarts or the cache turns over.
"""

from functools import lru_cache

from django.template import engines
from jinja2 import ChainableUndefined, TemplateSyntaxError
from jinja2.sandbox import modifies_known_mutable

from nautobot.core.templating import NautobotSandboxedEnvironment
from nautobot.extras.conditions.operators import field_matches
from nautobot.extras.conditions.payload import field_value

_MAX_COMPILED_EXPRESSIONS = 1024


class ConditionEnvironment(NautobotSandboxedEnvironment):
    """Nautobot's sandbox, read-only: an expression cannot modify the payload it is checked against."""

    def is_safe_attribute(self, obj, attr, value):
        return super().is_safe_attribute(obj, attr, value) and not modifies_known_mutable(obj, attr)


class ConditionError(Exception):
    """A condition could not be compiled."""


@lru_cache(maxsize=1)
def _environment():
    """The environment conditions compile and run in.

    Filters, tests and globals are Nautobot's, so an expression sees what a webhook template sees.
    `ChainableUndefined` makes a missing value anywhere in a dotted lookup (`snapshots.postchange.status`
    on a delete) falsy rather than an error.
    """
    nautobot_environment = engines["jinja"].env
    environment = ConditionEnvironment(undefined=ChainableUndefined)
    environment.filters.update(nautobot_environment.filters)
    environment.tests.update(nautobot_environment.tests)
    environment.globals.update(nautobot_environment.globals)
    environment.globals["field_value"] = field_value
    environment.globals["field_matches"] = field_matches
    return environment


@lru_cache(maxsize=_MAX_COMPILED_EXPRESSIONS)
def compile_condition(source):
    """
    Compile a condition source into a callable that takes the render context as keyword arguments.

    Args:
        source (str): A bare Jinja2 expression.

    Returns:
        (callable): `compiled(**context)` evaluates the expression and returns its value.

    Raises:
        ConditionError: If the source is not a valid Jinja2 expression. Failed compilations are not
            cached, so a corrected source compiles fresh.
    """
    try:
        return _environment().compile_expression(source, undefined_to_none=False)
    except TemplateSyntaxError as error:
        raise ConditionError(f"Invalid condition expression: {error}") from error
