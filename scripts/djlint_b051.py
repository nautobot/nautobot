"""rule B051: Add page-item class to list items within pagination list."""

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
    """Add page-item class to list items within pagination."""
    errors: list[LintError] = []

    # Check for <ul class="pagination">
    for ul_match in re.finditer(r"<ul\s+class=(['\"])(.*?)\1[^>]*>", html, flags=re.IGNORECASE):
        if "pagination" in ul_match.group(2).lower():
            ul_start = ul_match.start()
            closing_ul_match = re.search(r"</ul>", html[ul_start:], flags=re.IGNORECASE)
            if closing_ul_match:
                ul_end_content = ul_start + closing_ul_match.start()
                ul_content = html[ul_start : ul_end_content]

                for li_match in re.finditer(r"<li[^>]*>", ul_content, flags=re.IGNORECASE):
                    li_start_relative = li_match.start()
                    li_end_relative = li_match.end()
                    li_start_absolute = ul_start + li_start_relative

                    li_tag = ul_content[li_start_relative:li_end_relative]
                    if not re.search(r"\sclass=(['\"])(.*?)\1", li_tag, flags=re.IGNORECASE):
                        errors.append(
                            {
                                "code": rule["name"],
                                "line": get_line(li_start_absolute, line_ends),
                                "match": html[li_start_absolute : ul_start + li_end_relative].strip()[:20],
                                "message": rule["message"],
                            }
                        )
                    elif not re.search(r"\bpage-item\b", li_tag, flags=re.IGNORECASE):
                        errors.append(
                            {
                                "code": rule["name"],
                                "line": get_line(li_start_absolute, line_ends),
                                "match": html[li_start_absolute : ul_start + li_end_relative].strip()[:20],
                                "message": rule["message"],
                            }
                        )

    return tuple(
        error
        for error in errors
    )
