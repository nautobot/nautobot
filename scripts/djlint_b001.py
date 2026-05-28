"""rule B001: Add breadcrumb-item class to list items within breadcrumb."""

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
    """Add breadcrumb-item class to list items within breadcrumb."""
    errors: list[LintError] = []

    # Check for <ol class="breadcrumb">
    for ol_match in re.finditer(r"<ol\s+class=(['\"])(.*?)\1[^>]*>", html, flags=re.IGNORECASE):
        if "breadcrumb" in ol_match.group(2).lower():
            ol_start = ol_match.start()
            closing_ol_match = re.search(r"</ol>", html[ol_start:], flags=re.IGNORECASE)
            if closing_ol_match:
                ol_end_content = ol_start + closing_ol_match.start()
                ol_content = html[ol_start : ol_end_content]

                for li_match in re.finditer(r"<li[^>]*>", ol_content, flags=re.IGNORECASE):
                    li_start_relative = li_match.start()
                    li_end_relative = li_match.end()
                    li_start_absolute = ol_start + li_start_relative

                    li_tag = ol_content[li_start_relative:li_end_relative]
                    if not re.search(r"\bclass=(['\"])(.*?)\1", li_tag, flags=re.IGNORECASE):
                        errors.append(
                            {
                                "code": rule["name"],
                                "line": get_line(li_start_absolute, line_ends),
                                "match": html[li_start_absolute : ol_start + li_end_relative].strip()[:20],
                                "message": rule["message"],
                            }
                        )
                    elif not re.search(r"\bbreadcrumb-item\b", li_tag, flags=re.IGNORECASE):
                        errors.append(
                            {
                                "code": rule["name"],
                                "line": get_line(li_start_absolute, line_ends),
                                "match": html[li_start_absolute : ol_start + li_end_relative].strip()[:20],
                                "message": rule["message"],
                            }
                        )

    # Check within {% block extra_breadcrumbs %}
    for block_match in re.finditer(
        r"{%\s+block\s+extra_breadcrumbs\s*%}(.*?){%\s+endblock\s+extra_breadcrumbs\s*%}",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        block_content = block_match.group(1)
        block_start = block_match.start()

        for li_match in re.finditer(r"<li[^>]*>", block_content, flags=re.IGNORECASE):
            li_start_relative = li_match.start()
            li_end_relative = li_match.end()
            li_start_absolute = block_start + li_start_relative + len(block_match.group(0).split(block_content)[0])

            li_tag = block_content[li_start_relative:li_end_relative]
            if not re.search(r"\bclass=(['\"])(.*?)\1", li_tag, flags=re.IGNORECASE):
                errors.append(
                    {
                        "code": rule["name"],
                        "line": get_line(li_start_absolute, line_ends),
                        "match": li_tag.strip()[:20],
                        "message": rule["message"],
                    }
                )
            elif not re.search(r"\bbreadcrumb-item\b", li_tag, flags=re.IGNORECASE):
                errors.append(
                    {
                        "code": rule["name"],
                        "line": get_line(li_start_absolute, line_ends),
                        "match": li_tag.strip()[:20],
                        "message": rule["message"],
                    }
                )

    # Check within {% block breadcrumbs %}
    for block_match in re.finditer(
        r"{%\s+block\s+breadcrumbs\s*%}(.*?){%\s+endblock\s+breadcrumbs\s*%}",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        block_content = block_match.group(1)
        block_start = block_match.start()

        for li_match in re.finditer(r"<li[^>]*>", block_content, flags=re.IGNORECASE):
            li_start_relative = li_match.start()
            li_end_relative = li_match.end()
            li_start_absolute = block_start + li_start_relative + len(block_match.group(0).split(block_content)[0])

            li_tag = block_content[li_start_relative:li_end_relative]
            if not re.search(r"\bclass=(['\"])(.*?)\1", li_tag, flags=re.IGNORECASE):
                errors.append(
                    {
                        "code": rule["name"],
                        "line": get_line(li_start_absolute, line_ends),
                        "match": li_tag.strip()[:20],
                        "message": rule["message"],
                    }
                )
            elif not re.search(r"\bbreadcrumb-item\b", li_tag, flags=re.IGNORECASE):
                errors.append(
                    {
                        "code": rule["name"],
                        "line": get_line(li_start_absolute, line_ends),
                        "match": li_tag.strip()[:20],
                        "message": rule["message"],
                    }
                )

    return tuple(
        error
        for error in errors
    )
