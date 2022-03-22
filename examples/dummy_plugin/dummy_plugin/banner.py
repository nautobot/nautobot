"""Example of using a plugin to inject a custom banner across various pages."""

from typing import Optional

from django.utils.html import format_html

from nautobot.extras.choices import BannerClassChoices
from nautobot.extras.plugins import PluginBanner


def banner(context, *args, **kwargs) -> Optional[PluginBanner]:
    """
    Construct a custom PluginBanner, if appropriate.

    - If not authenticated, no banner is displayed.
    - On all authenticated UI views, the banner includes a greeting to the logged-in user.
    - On object table views, the banner also reports on the model being listed in the table.
    - On object detail views, the banner also reports on the object being viewed, and whether it's the changelog view.
    """
    if not context.request.user.is_authenticated:
        # No banner if the user isn't logged in
        return None

    # Banner content greeting the user
    content = format_html(
        "<div>Dummy Plugin says “Hello, <strong>{}</strong>!” 👋</div>",
        context.request.user,
    )

    if "object" in context:
        # Object detail view
        content += format_html(
            "<div>You are viewing {} {}</div>",
            context["object"]._meta.verbose_name,
            context["object"],
        )
        if "/changelog/" in context.request.path:
            # Object changelog view
            content += format_html("<div>Specifically, its changelog.</div>")
        return PluginBanner(content=content, banner_class=BannerClassChoices.CLASS_SUCCESS)
    elif "table" in context:
        # Table view
        content += format_html(
            "<div>You are viewing a table of {}</div>",
            context["table"].Meta.model._meta.verbose_name_plural,
        )
        return PluginBanner(content=content, banner_class=BannerClassChoices.CLASS_SUCCESS)

    # Default banner rendering
    return PluginBanner(content=content, banner_class=BannerClassChoices.CLASS_INFO)
