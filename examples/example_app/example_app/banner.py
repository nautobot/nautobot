"""Example of using an App to inject a custom banner across various pages."""

from typing import Optional

from django.utils.html import format_html

from nautobot.apps.config import get_app_settings_or_config
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
        "<div>Example App says “Hello, <strong>{}</strong>!” 👋</div>",
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
    elif "table" in context and context["table"] is not None:
        # Table view
        content += format_html(
            "<div>You are viewing a table of {}</div>",
            context["table"].Meta.model._meta.verbose_name_plural,
        )
        base_columns = context["table"].base_columns
        extension_columns = [column for column in base_columns if column.startswith("example_app_")]
        if extension_columns:
            content += format_html(
                "<div><strong>Note: Table columns have been modified by a TableExtension.</strong></div>"
            )
        return Banner(content=content, banner_class=BannerClassChoices.CLASS_SUCCESS)

    content += format_html(
        "<div>SAMPLE_VARIABLE is {}</div>", get_app_settings_or_config("example_app", "SAMPLE_VARIABLE")
    )
    content += format_html(
        "<div>lowercase_example is {}</div>", get_app_settings_or_config("example_app", "lowercase_example")
    )

    # Default banner rendering
    return Banner(content=content, banner_class=BannerClassChoices.CLASS_INFO)
