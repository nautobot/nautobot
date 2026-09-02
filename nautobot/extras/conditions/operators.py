"""Comparison operators available to the field condition presets.

A preset's Jinja2 expression is a fixed string, and Jinja has no way to dispatch on an operator chosen at
runtime. Rather than build one expression out of nested inline conditionals, the comparison is done here
and exposed to expressions as `field_matches`, which keeps the operator semantics in Python where they can
be read and tested directly.

Each operator is a small strategy object: a key, a form label, the predicate that performs the comparison,
and the value kinds the comparison is meaningful for. The predicate is what evaluation uses; `applies_to`
exists for the form and save-time validation, which know the watched model's fields and can narrow the
offered operators accordingly. Evaluation itself stays permissive - a stored operator that makes no sense
for the value it meets simply fails its row, the same as any other non-match - because a rule must not
start erroring when a field's type changes underneath it.

Value-kind vocabulary shared with the form layer:

- `text` - strings, and related objects reduced to their display value
- `number` - ints, floats, Decimals, and numeric strings
- `boolean` - true/false fields
- `date` - dates and datetimes
- `list` - many-valued fields such as tags

There is deliberately no `!=` operator. Negation is the condition row's `negate` flag, which inverts any
operator and raw expressions alike; a second negation path would let the two drift.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import operator as py_operator
from typing import Any, Callable

from nautobot.core.settings_funcs import is_truthy

KIND_TEXT = "text"
KIND_NUMBER = "number"
KIND_BOOLEAN = "boolean"
KIND_DATE = "date"
KIND_LIST = "list"

ALL_KINDS = frozenset({KIND_TEXT, KIND_NUMBER, KIND_BOOLEAN, KIND_DATE, KIND_LIST})


def _as_number(value):
    """Return `value` as a Decimal, or None if it is not a number.

    `bool` is explicitly not a number here, although Python's bool subclasses int: `True gt 0` reading
    as `1 > 0` would be a surprise, not a feature.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value.strip())
        except (InvalidOperation, ArithmeticError):
            return None
    return None


def _as_text(value):
    """Return `value` as a string for text comparison, with None becoming the empty string.

    Folding None into "" means `= ""` matches both an empty and an unset field.
    """
    if value is None:
        return ""
    return str(value)


def _as_bool(target):
    """Interpret the stored `target` as a boolean, or None if it spells neither.

    The accepted spellings are `is_truthy`'s. Two things are layered on
    top: the target is stripped first, because a form strips its input but a REST API payload does
    not, and the ValueError is swallowed - a saved rule meeting a target it cannot parse must fail
    its row like any other non-match, not raise at dispatch time.
    """
    try:
        return is_truthy(_as_text(target).strip())
    except ValueError:
        return None


def _equals(value, target):
    # A real boolean field compares against the target read as a boolean, so a user typing `true`,
    # `True` or `1` matches a True field instead of failing on str(True) == "true" trivia.
    if isinstance(value, bool):
        wanted = _as_bool(target)
        return value is wanted if wanted is not None else False
    left, right = _as_number(value), _as_number(target)
    if left is not None and right is not None:
        return left == right
    return _as_text(value) == _as_text(target)


def _ordering(python_operator):
    """Build an ordering predicate: numeric when both sides look numeric, lexicographic otherwise."""

    def predicate(value, target):
        left, right = _as_number(value), _as_number(target)
        if left is None or right is None:
            left, right = _as_text(value), _as_text(target)
        return python_operator(left, right)

    return predicate


def _in(value, target):
    # The target is a comma-separated list of wanted values. A value that itself contains a comma is
    # therefore not expressible with this operator; use `=` (or several rows) for that.
    wanted = [item.strip() for item in _as_text(target).split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        # A list field is in the wanted set if any of its entries is. `tags in critical,urgent` reads
        # as "tagged with either", which is the only useful reading. Comparing the whole list against
        # each name can never match.
        return any(_as_text(item) in wanted for item in value)
    return _as_text(value) in wanted


def _contains(value, target):
    # A list field contains an element; a text field contains a substring.
    if isinstance(value, (list, tuple, set)):
        return _as_text(target) in [_as_text(item) for item in value]
    return _as_text(target) in _as_text(value)


def _startswith(value, target):
    return _as_text(value).startswith(_as_text(target))


def _endswith(value, target):
    return _as_text(value).endswith(_as_text(target))


@dataclass(frozen=True)
class Operator:
    """One comparison strategy: how to compare, what to call it, and where it makes sense.

    `predicate` receives the field's value from the captured change (str, number, bool or list) and the
    target from the form (always a string), and returns whether the comparison holds. That type asymmetry
    is handled inside the predicates rather than being pushed onto whoever writes the condition.

    `applies_to` is advisory metadata for the form and for save-time validation; evaluation never
    consults it.
    """

    key: str
    label: str
    predicate: Callable[[Any, str], bool]
    applies_to: frozenset

    def matches(self, value, target):
        return bool(self.predicate(value, target))


OPERATOR_EQUALS = "="
OPERATOR_GT = "gt"
OPERATOR_GTE = "gte"
OPERATOR_LT = "lt"
OPERATOR_LTE = "lte"
OPERATOR_IN = "in"
OPERATOR_CONTAINS = "contains"
OPERATOR_STARTSWITH = "startswith"
OPERATOR_ENDSWITH = "endswith"

#: Every operator, in the order the form offers them.
OPERATORS = (
    Operator(OPERATOR_EQUALS, "= (equals)", _equals, ALL_KINDS - {KIND_LIST}),
    Operator(OPERATOR_GT, "> (greater than)", _ordering(py_operator.gt), frozenset({KIND_NUMBER, KIND_DATE})),
    Operator(
        OPERATOR_GTE,
        ">= (greater than or equal)",
        _ordering(py_operator.ge),
        frozenset({KIND_NUMBER, KIND_DATE}),
    ),
    Operator(OPERATOR_LT, "< (less than)", _ordering(py_operator.lt), frozenset({KIND_NUMBER, KIND_DATE})),
    Operator(
        OPERATOR_LTE,
        "<= (less than or equal)",
        _ordering(py_operator.le),
        frozenset({KIND_NUMBER, KIND_DATE}),
    ),
    Operator(OPERATOR_IN, "in (one of a comma-separated list)", _in, ALL_KINDS),
    Operator(OPERATOR_CONTAINS, "contains", _contains, frozenset({KIND_TEXT, KIND_LIST})),
    Operator(OPERATOR_STARTSWITH, "starts with", _startswith, frozenset({KIND_TEXT, KIND_DATE})),
    Operator(OPERATOR_ENDSWITH, "ends with", _endswith, frozenset({KIND_TEXT, KIND_DATE})),
)

OPERATOR_REGISTRY = {operator.key: operator for operator in OPERATORS}

# Operator key to the label shown in the form, in the order they are offered.
# Kept as `(key, label)` pairs because that is the shape Django choices and the preset
# parameter schema both consume.
FIELD_OPERATORS = tuple((operator.key, operator.label) for operator in OPERATORS)

FIELD_OPERATOR_KEYS = tuple(operator.key for operator in OPERATORS)


def operators_for_kind(kind):
    """Return the operators meaningful for a value kind, for the form and save-time validation.

    An unknown kind gets every operator rather than none: the form degrades to today's behaviour
    instead of offering an empty dropdown for a field type this module has not classified.
    """
    if kind not in ALL_KINDS:
        return OPERATORS
    return tuple(operator for operator in OPERATORS if kind in operator.applies_to)


def field_matches(value, operator, target):
    """
    Compare a field's value against a target using the named operator.

    This is the single entry point expressions use (exposed to the sandbox as `field_matches`), so the
    operator semantics live here in Python where they can be read and tested directly.

    Args:
        value: The field's value from the captured change.
        operator (str): One of `FIELD_OPERATOR_KEYS`.
        target (str): The value to compare against, as entered on the form.

    Returns:
        (bool): Whether the comparison holds. An unknown operator is False rather than an error, so a
            malformed condition fails its row like any other rather than breaking the rule.
    """
    strategy = OPERATOR_REGISTRY.get(operator)
    if strategy is None:
        return False
    return strategy.matches(value, target)
