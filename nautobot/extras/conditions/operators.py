"""Comparison operators available to the field condition presets.

Comparison semantics are implemented in Python and exposed to expressions as
`field_matches`. This keeps type-aware conversion and comparison in one place:
a captured value may be a string, number, boolean, or list, while a target
comes from a form and therefore requires explicit conversion before comparison.

Each operator is a frozen object holding a key, a form label, the predicate that
performs the comparison, and `applies_to`, the value kinds for which the
comparison is meaningful.

Value kinds, as classified by whoever maps a model field to one of them:

- `text` - strings, and related objects reduced to their display value
- `number` - ints, floats, Decimals, and numeric strings
- `boolean` - true/false fields
- `date` - dates and datetimes, serialized as ISO 8601 strings and compared as text
- `list` - many-valued fields such as tags

`applies_to` is advisory. Evaluation never reads it: the condition-row form (a later change) uses it
to narrow the operator dropdown to the operators that make sense for the chosen field, but a stored
operator meeting a value it was not designed for still gets a defined answer rather than an error.
That matters because rules outlive the shape of the data they were written against; a custom field
changing type must not turn a saved rule into a dispatch-time exception.

It also matters because the API has no dropdown. Every combination below is reachable by writing a
condition through the REST API, so every combination has a documented answer:

| value type | `=`           | `gt` `gte` `lt` `lte` | `in`        | `contains` | `startswith` `endswith` |
| ---------- | ------------- | --------------------- | ----------- | ---------- | ----------------------- |
| str, date  | exact match   | lexicographic         | any of      | substring  | affix match             |
| number     | numeric       | numeric               | any of      | False      | False                   |
| bool       | parsed target | False                 | any of      | False      | False                   |
| list       | set equality  | False                 | any element | False      | False                   |

Three rules cover the table. Text operators apply to strings only, because substring matching on a
number or a boolean has no meaning. Ordering compares numerically when both sides are numbers and
lexicographically otherwise, which is also what makes ISO 8601 dates order chronologically; booleans
and lists have no ordering. And `in` is "equals any of", so it inherits each kind's own equality
rather than defining a second one.

A missing value (None) compares as the empty string for `=` and `in`, so `= ""` matches both a
blank and an unset field; it has no ordering and is not a string, so every other operator returns
False. A dedicated null toggle on the condition row will supersede that.

There is deliberately no `!=` operator. Negation is the condition row's `negate` flag, which inverts
any operator and raw expressions alike.
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

TEXTUAL_KINDS = frozenset({KIND_TEXT, KIND_DATE})  # contains, startswith, endswith
ORDERABLE_KINDS = frozenset({KIND_TEXT, KIND_NUMBER, KIND_DATE})  # gt, gte, lt, lte
SET_MEMBER_KINDS = frozenset({KIND_TEXT, KIND_NUMBER, KIND_DATE, KIND_LIST})  # in


def _as_number(value):
    """Return `value` as a Decimal, or None if it is not a number.

    `bool` is explicitly not a number here, although Python's bool subclasses int: ordering a boolean
    as if it were an integer would be a surprise, not a feature. NaN is not a number either: Decimal
    parses it happily, then raises on any ordering comparison, which would turn a stored rule into a
    dispatch-time exception.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        number = Decimal(str(value))
    elif isinstance(value, str):
        try:
            number = Decimal(value.strip())
        except (InvalidOperation, ArithmeticError):
            return None
    else:
        return None
    return None if number.is_nan() else number


def _as_text(value):
    """Return `value` as a string for text comparison, with None becoming the empty string.

    Folding None into "" means `= ""` matches both an empty and an unset field.
    """
    if value is None:
        return ""
    return str(value)


def _as_bool(target):
    """Interpret the stored `target` as a boolean, or None if it spells neither.

    The accepted spellings are `is_truthy`'s. Two things are layered on top: the target is stripped
    first, because a form strips its input but a REST API payload does not, and the ValueError is
    swallowed - a saved rule meeting a target it cannot parse must fail its row like any other
    non-match, not raise at dispatch time.
    """
    try:
        return is_truthy(_as_text(target).strip())
    except ValueError:
        return None


def _as_target_list(target):
    """Return a set-valued target as a list of strings.

    The row form's MultiValueCharField already yields a list of non-empty strings; a plain string,
    from the API or a hand-edited rule, is split on commas so it is not iterated character by
    character. Blank entries are dropped either way: since a missing value compares as "", a
    trailing comma would make every unset field match.
    """
    if isinstance(target, (list, tuple, set)):
        items = [_as_text(item).strip() for item in target]
    else:
        items = [item.strip() for item in _as_text(target).split(",")]
    return [item for item in items if item]


def _comparable_pair(value, target):
    """Coerce both sides to one type, or return None when no comparison makes sense.

    Decimal when both sides read as numbers, str when the value is a string. Anything that is not a
    scalar - a boolean, a list, a mapping, bytes - has no comparison and gets None; so does a number
    whose target does not read as one, or NaN, because ordering a number against a word by its
    spelling would be meaningless.

    This is the single home of the conversion rule that `=` and the ordering operators share, so
    the two can never disagree about whether two representations of a number are equal.
    """
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        return None
    left, right = _as_number(value), _as_number(target)
    if left is not None and right is not None:
        return left, right
    if isinstance(value, str):
        return value, _as_text(target)
    return None


def _equals(value, target):
    # A boolean compares against the target read as a boolean, in any spelling `is_truthy` accepts.
    if isinstance(value, bool):
        wanted = _as_bool(target)
        return value is wanted if wanted is not None else False
    # A list equals a set of values: same members, order and repetition disregarded.
    if isinstance(value, (list, tuple, set)):
        return {_as_text(item) for item in value} == set(_as_target_list(target))
    # A missing value compares as the empty string, so `= ""` matches an unset field.
    pair = _comparable_pair("" if value is None else value, target)
    return pair is not None and pair[0] == pair[1]


def _ordering(python_operator):
    def predicate(value, target):
        # `_comparable_pair` returns None for anything without an ordering: booleans, lists, missing
        # values, and numbers set against a non-numeric target.
        pair = _comparable_pair(value, target)
        return pair is not None and python_operator(*pair)

    return predicate


def _in(value, target):
    """Whether `value` equals any of the targets.

    Defined in terms of `_equals` so membership inherits each kind's own equality rather than
    defining a second one. A list field matches when any of its entries equals a target, which is
    the only useful reading for a many-valued field; comparing the whole list against each target
    could never match.
    """
    targets = _as_target_list(target)
    if isinstance(value, (list, tuple, set)):
        return any(_equals(item, target_item) for item in value for target_item in targets)
    return any(_equals(value, item) for item in targets)


def _text_operation(string_method):
    """Build a text predicate that applies to strings only.

    Coercing a number or a boolean to text first would produce substring matches that answer no
    question anyone asked. Returning False keeps the row an ordinary non-match.
    """

    def predicate(value, target):
        if not isinstance(value, str):
            return False
        return string_method(value, _as_text(target))

    return predicate


@dataclass(frozen=True)
class Operator:
    """One comparison strategy: how to compare, what to call it, and where it makes sense.

    `predicate` receives the field's value from the captured change (str, number, bool or list) and
    the target as stored on the condition row (a string, or a list for a set-valued operator), and
    returns whether the comparison holds. That type asymmetry is handled inside the predicates
    rather than being pushed onto whoever writes the condition.

    `applies_to` is advisory metadata for the form and for save-time validation; evaluation never
    consults it.
    """

    key: str
    label: str
    predicate: Callable[[Any, Any], bool]
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
    Operator(key=OPERATOR_EQUALS, label="= (equals)", predicate=_equals, applies_to=ALL_KINDS),
    Operator(
        key=OPERATOR_GT,
        label="> (greater than)",
        predicate=_ordering(py_operator.gt),
        applies_to=ORDERABLE_KINDS,
    ),
    Operator(
        key=OPERATOR_GTE,
        label=">= (greater than or equal)",
        predicate=_ordering(py_operator.ge),
        applies_to=ORDERABLE_KINDS,
    ),
    Operator(
        key=OPERATOR_LT,
        label="< (less than)",
        predicate=_ordering(py_operator.lt),
        applies_to=ORDERABLE_KINDS,
    ),
    Operator(
        key=OPERATOR_LTE,
        label="<= (less than or equal)",
        predicate=_ordering(py_operator.le),
        applies_to=ORDERABLE_KINDS,
    ),
    Operator(key=OPERATOR_IN, label="in (any of)", predicate=_in, applies_to=SET_MEMBER_KINDS),
    Operator(
        key=OPERATOR_CONTAINS,
        label="contains",
        predicate=_text_operation(str.__contains__),
        applies_to=TEXTUAL_KINDS,
    ),
    Operator(
        key=OPERATOR_STARTSWITH,
        label="starts with",
        predicate=_text_operation(str.startswith),
        applies_to=TEXTUAL_KINDS,
    ),
    Operator(
        key=OPERATOR_ENDSWITH,
        label="ends with",
        predicate=_text_operation(str.endswith),
        applies_to=TEXTUAL_KINDS,
    ),
)

OPERATOR_REGISTRY = {operator.key: operator for operator in OPERATORS}

# Operator key to the label shown in the form, in the order they are offered.
# Kept as `(key, label)` pairs because that is the shape Django choices and the preset
# parameter schema both consume.
FIELD_OPERATORS = tuple((operator.key, operator.label) for operator in OPERATORS)
FIELD_OPERATOR_KEYS = tuple(operator.key for operator in OPERATORS)


def operators_for_kind(kind):
    """Return the operators meaningful for a value kind, for the form and save-time validation.

    An unknown kind gets every operator rather than none, so a field type nothing has classified yet
    offers the full list instead of an empty dropdown.
    """
    if kind not in ALL_KINDS:
        return OPERATORS
    return tuple(operator for operator in OPERATORS if kind in operator.applies_to)


def takes_a_set(operator, kind):
    """Whether the form should offer a multi-value widget for this operator on this kind.

    `in` always takes a set. `=` takes one for a list-valued field, where it means set equality, and
    a single value everywhere else.
    """
    if operator == OPERATOR_IN:
        return True
    return operator == OPERATOR_EQUALS and kind == KIND_LIST


def field_matches(value, operator, target):
    """
    Compare a field's value against a target using the named operator.

    This is the single entry point expressions use (exposed to the sandbox as `field_matches`), so the
    operator semantics live here in Python where they can be read and tested directly.

    Args:
        value: The field's value from the captured change.
        operator (str): One of `FIELD_OPERATOR_KEYS`.
        target: The value to compare against, as stored on the condition row: a string, or a list
            for a set-valued operator.

    Returns:
        (bool): Whether the comparison holds. An unknown operator is False rather than an error: the
            row does not match, and since rows are AND-ed the rule does not fire, instead of the
            evaluation raising.
    """
    strategy = OPERATOR_REGISTRY.get(operator)
    if strategy is None:
        return False
    return strategy.matches(value, target)
