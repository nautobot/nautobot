"""Checks a list of stored conditions against a payload.

`check()` takes the rows as they are stored on a Webhook or Job Hook and a payload built by
`build_event_payload`, and returns a `Verdict`: a `RowVerdict` per row and `passed`, which is whether
every row passed. Rows are AND-ed.

A row passes when its expression, rendered with the payload and the row's `param_*` variables, is
truthy - `bool(result)` is the one definition of "passes" in this package - inverted by `negate`. A row
that raises anywhere on the way fails and records the error.
"""

from dataclasses import asdict, dataclass

from nautobot.extras.conditions.expressions import compile_condition
from nautobot.extras.conditions.rows import ConditionRow


@dataclass(frozen=True)
class RowVerdict:
    """The outcome for one row, for showing a person which row stopped the rule and why.

    `passed=False` with no `error` is an ordinary non-match: the rule is fine, this change does not fit
    it. `passed=False` with an `error` is a broken row: the rule needs fixing.
    """

    index: int
    row: dict
    passed: bool
    error: str | None = None


@dataclass(frozen=True)
class Verdict:
    """The outcome for a list of rows.

    `passed` is the one value dispatch reads: whether every row passed. `rows` is for a dry-run, one
    `RowVerdict` per stored row.
    """

    rows: tuple[RowVerdict, ...]
    passed: bool

    def as_dict(self):
        return {"passed": self.passed, "rows": [asdict(row) for row in self.rows]}


def check_row(index, row, payload):
    """
    Check one stored row against `payload`.

    Args:
        index (int): The row's position in the stored list, reported back for display.
        row (dict): The row as stored.
        payload (dict): The event payload. Rendered as-is; callers that reuse a payload across rows
            or actions pass a copy.

    Returns:
        (RowVerdict): Never raises; a failure of any kind is a `RowVerdict` with `passed=False` and
            `error` set.
    """
    try:
        condition = ConditionRow.from_dict(row)
        source, context = condition.resolve()
        result = compile_condition(source)(**payload, **context)
        passed = bool(result)
        if condition.negate:
            passed = not passed
        return RowVerdict(index=index, row=row, passed=passed)
    except Exception as exc:  # any failure fails the row and is reported, never raised
        return RowVerdict(index=index, row=row, passed=False, error=f"{type(exc).__name__}: {exc}")


def check(conditions, payload):
    """
    Check every stored row against `payload`.

    All rows are checked even after one fails, so a dry-run can show the whole picture.

    Args:
        conditions (list): The rows as stored on the action. An empty list passes.
        payload (dict): The event payload from `build_event_payload`.

    Returns:
        (Verdict): `passed` is whether every row passed.
    """
    rows = tuple(check_row(index, row, payload) for index, row in enumerate(conditions or []))
    return Verdict(rows=rows, passed=all(row.passed for row in rows))
