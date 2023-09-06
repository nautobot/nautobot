# Adding a Banner

+++ 1.2.0

An app can provide a function that renders a custom banner on any number of Nautobot views. By default Nautobot looks for a function `banner()` inside of `banner.py`. (This can be overridden by setting `banner_function` to a custom value on the app's `NautobotAppConfig`.)

This function currently receives a single argument, `context`, which is the [Django request context](https://docs.djangoproject.com/en/stable/ref/templates/api/#using-requestcontext) in which the current page is being rendered. The function can return `None` if no banner is needed for a given page view, or can return a `Banner` object describing the banner contents. Here's a simple example `banner.py`:

```python
# banner.py
from django.utils.html import format_html

from nautobot.apps.ui import Banner, BannerClassChoices

def banner(context, *args, **kwargs):
    """Greet the user, if logged in."""
    # Request parameters can be accessed via context.request
    if not context.request.user.is_authenticated:
        # No banner if the user isn't logged in
        return None
    else:
        return Banner(
            content=format_html("Hello, <strong>{}</strong>! 👋", context.request.user),
            banner_class=BannerClassChoices.CLASS_SUCCESS,
        )
```
