"""rule B042: Add nav-link class to anchor items within navigation tabs."""

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
    """Add nav-link class to anchor items within navigation tabs."""
    errors: list[LintError] = []

    # Check for <ul class="nav nav-tabs">
    for ul_match in re.finditer(r"<ul\s+class=(['\"])(.*?)\1[^>]*>", html, flags=re.IGNORECASE):
        if "nav-tabs" in ul_match.group(2).lower() or "nav-pills" in ul_match.group(2).lower():
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
                    if not re.search(r"\sclass=(['\"])(.*?)\1", a_tag, flags=re.IGNORECASE):
                        errors.append(
                            {
                                "code": rule["name"],
                                "line": get_line(a_start_absolute, line_ends),
                                "match": html[a_start_absolute : ul_start + a_end_relative].strip()[:20],
                                "message": rule["message"],
                            }
                        )
                    elif not re.search(r"\bnav-link\b", a_tag, flags=re.IGNORECASE):
                        errors.append(
                            {
                                "code": rule["name"],
                                "line": get_line(a_start_absolute, line_ends),
                                "match": html[a_start_absolute : ul_start + a_end_relative].strip()[:20],
                                "message": rule["message"],
                            }
                        )

    # Check within {% block extra_nav_tabs %}
    for block_match in re.finditer(
        r"{%\s+block\s+extra_nav_tabs\s*%}(.*?){%\s+endblock\s+extra_nav_tabs\s*%}",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        block_content = block_match.group(1)
        block_start = block_match.start()

        for a_match in re.finditer(r"<a[^>]*>", block_content, flags=re.IGNORECASE):
            a_start_relative = a_match.start()
            a_end_relative = a_match.end()
            a_start_absolute = block_start + a_start_relative + len(block_match.group(0).split(block_content)[0])

            a_tag = block_content[a_start_relative:a_end_relative]
            if not re.search(r"\sclass=(['\"])(.*?)\1", a_tag, flags=re.IGNORECASE):
                errors.append(
                    {
                        "code": rule["name"],
                        "line": get_line(a_start_absolute, line_ends),
                        "match": a_tag.strip()[:20],
                        "message": rule["message"],
                    }
                )
            elif not re.search(r"\bnav-link\b", a_tag, flags=re.IGNORECASE):
                errors.append(
                    {
                        "code": rule["name"],
                        "line": get_line(a_start_absolute, line_ends),
                        "match": a_tag.strip()[:20],
                        "message": rule["message"],
                    }
                )

    return tuple(
        error
        for error in errors
    )
