"""
Custom plugin for mkdocs, adding support for version-(added,changed,removed) annotations.

Note that this is dependent upon `mkdocs`, which is **not** a core Nautobot dependency;
therefore, it should **not** be imported by core Nautobot code!
"""

import re

from mkdocs.plugins import BasePlugin


class NautobotMkDocsPlugin(BasePlugin):
    def on_page_markdown(self, markdown, page, **kwargs):
        # "+++ 1.2.0" --> '!!! version-added "Added in version 1.2.0"'
        markdown = re.sub(
            r"^\+\+\+\s+([0-9.]+)", r'!!! version-added "Added in version \1"', markdown, flags=re.MULTILINE
        )
        # "+/- 1.3.0" --> '!!! version-changed "Changed in version 1.3.0"'
        markdown = re.sub(
            r"^\+/-\s+([0-9.]+)", r'!!! version-changed "Changed in version \1"', markdown, flags=re.MULTILINE
        )
        # "--- 1.3.0" --> '!!! version-removed "Removed in version 1.3.0"'
        markdown = re.sub(
            r"^---\s+([0-9.]+)", r'!!! version-removed "Removed in version \1"', markdown, flags=re.MULTILINE
        )

        return markdown
