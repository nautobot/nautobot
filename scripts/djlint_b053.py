"""rule B052: Add page-link class to anchor items within pagination items."""

from __future__ import annotations

from typing import TYPE_CHECKING

import regex as re

from djlint.helpers import (
    inside_ignored_linter_block,
    inside_ignored_rule,
    overlaps_ignored_block,
)
from djlint.lint import get_line

if TYPE_CHECKING:
    from typing_extensions import Any
    from djlint.settings import Config
    from djlint.types import LintError


def run(
    rule: dict[str, Any],
    config: Config,
    html: str,
    filepath: str,
    line_ends: list[dict[str, int]],
    *args: Any,
    **kwargs: Any,
) -> tuple[LintError, ...]:
    """
    The `active` and `disabled` classes are now applied to the outer `page-item` element (<li>)
    instead of the inner `page-link` element (<a>).
    """
    errors: list[LintError] = []

    # Check for <ul class="pagination">
    for ul_match in re.finditer(r"<ul\s+class=(['\"])(.*?)\1[^>]*>", html, flags=re.IGNORECASE):
        if "pagination" in ul_match.group(2).lower():
            ul_start = ul_match.start()
            closing_ul_match = re.search(r"</ul>", html[ul_start:], flags=re.IGNORECASE)
            if closing_ul_match:
                ul_end_content = ul_start + closing_ul_match.start()
                ul_content = html[ul_start : ul_end_content]

                for a_match in re.finditer(r"<a[^>]*>", ul_content, flags=re.IGNORECASE):
                    a_start_relative = a_match.start()
                    a_end_relative = a_match.end()
                    a_start_absolute = ul_start + a_start_relative

                    a_tag = ul_content[a_start_relative:a_end_relative]
                    # If disabled or active in a_tag, add error.
                    if re.search(r"\sclass=\"[^\"]*\b(active|disabled)\b[^\"]*\"", a_tag, flags=re.IGNORECASE):
                        errors.append(
                            {
                                "code": rule["name"],
                                "line": get_line(a_start_absolute, line_ends),
                                "match": html[a_start_absolute : ul_start + a_end_relative].strip()[:20],
                                "message": rule["message"],
                            }
                        )

    return tuple(
        error
        for error in errors
    )
