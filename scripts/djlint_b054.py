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
    Replace icons with the HTML character entities:
    <i class="mdi mdi-chevron-double-left"></i> with <span aria-hidden="true">&laquo;</span>
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

                for li_match in re.finditer(r"<li[^>]*>", ul_content, flags=re.IGNORECASE):
                    closing_li_match = re.search(r"</li>", ul_content, flags=re.IGNORECASE)
                    li_start_relative = li_match.start()
                    li_end_relative = li_match.end()
                    li_start_absolute = ul_start + li_start_relative
                    if closing_li_match:
                        li_end_content = li_start_relative + closing_li_match.start()
                        li_content = html[li_start_absolute : li_end_content]
                        # Check for <i class="mdi mdi-chevron-double-left"></i> exists
                        i_match = re.search(
                            r'<i\s+class=["\"]mdi mdi-chevron-double-left["\"]></i>',
                            li_content,
                            flags=re.IGNORECASE
                        )
                        if i_match:
                            # Find the absolute position of <i> in the whole html
                            i_tag_relative = i_match.start()
                            i_tag_absolute = li_start_absolute + i_tag_relative
                            errors.append(
                                {
                                    "code": rule["name"],
                                    "line": get_line(i_tag_absolute, line_ends),
                                    "match": html[i_tag_absolute : i_tag_absolute + 40].strip(),
                                    "message": rule["message"],
                                }
                            )

    return tuple(
        error
        for error in errors
    )
