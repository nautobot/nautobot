"""Example of using a plugin to inject a custom banner across various pages."""

from typing import Optional

from django.utils.html import format_html

from nautobot.apps.ui import Banner, BannerClassChoices


def banner(context, *args, **kwargs) -> Optional[Banner]:
    """
    Construct a custom Banner, if appropriate.

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
        "<div>Example Plugin says “Hello, <strong>{}</strong>!” 👋</div>",
        context.request.user,
    )

    # NautobotUIViewSet list view will pass an `object` context variable with value None
    # We need to account for that too
    if "object" in context and hasattr(context["object"], "_meta"):
        # Object detail view
        content += format_html(
            "<div>You are viewing {} {}</div>",
            context["object"]._meta.verbose_name,
            context["object"],
        )
        if "/changelog/" in context.request.path:
            # Object changelog view
            content += format_html("<div>Specifically, its changelog.</div>")
        return Banner(content=content, banner_class=BannerClassChoices.CLASS_SUCCESS)
    elif "table" in context:
        # Table view
        content += format_html(
            "<div>You are viewing a table of {}</div>",
            context["table"].Meta.model._meta.verbose_name_plural,
        )
        return Banner(content=content, banner_class=BannerClassChoices.CLASS_SUCCESS)

    # Default banner rendering
    return Banner(content=content, banner_class=BannerClassChoices.CLASS_INFO)
