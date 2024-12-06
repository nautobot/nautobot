import re

from pymarkdown.general.constants import Constants
from pymarkdown.plugin_manager.plugin_details import PluginDetails
from pymarkdown.plugin_manager.plugin_scan_context import PluginScanContext
from pymarkdown.plugin_manager.rule_plugin import RulePlugin
from pymarkdown.tokens.markdown_token import MarkdownToken


class FileRelativeLinks(RulePlugin):
    """Ensure that all relative links are file-relative, that is `../foo.md` not `../foo/`."""

    def get_details(self) -> PluginDetails:
        return PluginDetails(
            plugin_name="file-relative-links",
            plugin_id="NAU001",
            plugin_enabled_by_default=True,
            plugin_description="Use file-relative links, e.g. ../foo.md, not ../foo/",
            plugin_version="1.0.0",
            plugin_interface_version=1,
            plugin_url="",
        )

    def next_token(self, context: PluginScanContext, token: MarkdownToken) -> None:
        if not token.is_inline_link:
            return
        stripped_link_uri = token.active_link_uri.strip(Constants.ascii_whitespace)
        if re.match(r"^[a-z0-9+.-]+:.*", stripped_link_uri):
            # It's an external link, e.g. http://...
            return
        if stripped_link_uri.startswith("#"):
            # It's a link to an anchor within the same page, e.g. #some-heading
            return
        if re.match(r".*\.md(#.*)?$", stripped_link_uri):
            # It's a proper relative link to another markdown file
            return
        # It's a relative link, but not to a .md file - fail
        self.report_next_token_error(context, token)
