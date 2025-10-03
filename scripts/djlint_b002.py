"""rule B002: Ensure active breadcrumb items have aria-current="page"."""

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
    """Ensure active breadcrumb items have aria-current="page"."""
    errors: list[LintError] = []

    # Helper function to check <li> tags for active class and aria-current
    def check_active_breadcrumb_items(start_index: int, content: str):
        for li_match in re.finditer(r"<li([^>]*)>", content, flags=re.IGNORECASE):
            li_start_relative = li_match.start()
            li_end_relative = li_match.end()
            li_start_absolute = start_index + li_start_relative
            li_attributes = li_match.group(1)
            li_tag_full = content[li_start_relative:li_end_relative]

            if re.search(r"\bactive\b", li_attributes, flags=re.IGNORECASE) and not re.search(
                r'aria-current=["\']page["\']', li_attributes, flags=re.IGNORECASE
            ):
                errors.append(
                    {
                        "code": rule["name"],
                        "line": get_line(li_start_absolute, line_ends),
                        "match": html[li_start_absolute : start_index + li_end_relative].strip()[:40],
                        "message": rule["message"],
                    }
                )

    # Check for <ol class="breadcrumb">
    for ol_match in re.finditer(r"<ol\s+class=(['\"])(.*?)\1[^>]*>", html, flags=re.IGNORECASE):
        if "breadcrumb" in ol_match.group(2).lower():
            ol_start = ol_match.start()
            closing_ol_match = re.search(r"</ol>", html[ol_start:], flags=re.IGNORECASE)
            if closing_ol_match:
                ol_end_content = ol_start + closing_ol_match.start()
                ol_content = html[ol_start : ol_end_content]
                check_active_breadcrumb_items(ol_start, ol_content)

    # Check within {% block extra_breadcrumbs %}
    for block_match in re.finditer(
        r"{%\s+block\s+extra_breadcrumbs\s*%}(.*?){%\s+endblock\s+extra_breadcrumbs\s*%}",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        block_content = block_match.group(1)
        block_start = block_match.start()
        if not block_content:
            continue
        block_header_len = len(block_match.group(0).split(block_content)[0])
        content_start_absolute = block_start + block_header_len
        check_active_breadcrumb_items(content_start_absolute, block_content)

    # Check within {% block breadcrumbs %}
    for block_match in re.finditer(
        r"{%\s+block\s+breadcrumbs\s*%}(.*?){%\s+endblock\s+breadcrumbs\s*%}",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        block_content = block_match.group(1)
        block_start = block_match.start()
        if not block_content:
            continue
        block_header_len = len(block_match.group(0).split(block_content)[0])
        content_start_absolute = block_start + block_header_len
        check_active_breadcrumb_items(content_start_absolute, block_content)

    return tuple(
        error
        for error in errors
    )
