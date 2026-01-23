# HTMX and Nautobot

Nautobot makes use of the [HTMX](https://htmx.org/) library to improve the responsiveness, speed, and smoothness of various parts of the UI.

For example, clicking the "☆" next to an item in the navigation menu to mark it as a favorite uses HTMX to update the server-side user preferences, rerender and retrieve (only) the favorites submenu server-side, and seamlessly inject the updated submenu back into the navbar, all without a full-page browser refresh.

As another example, when loading any object-list view in Nautobot, to improve responsiveness, the initial page load renders all of the page *structure* (nav menu, headers, footers, filtering options, etc.) but an empty list of objects (displaying only a "loading" spinner), then uses HTMX to issue a second, asynchronous request to actually retrieve and render the contents of the object list (which may take significantly longer, depending on pagination and number of records), swapping them in seamlessly when retrieved.

The purpose of this document is not to advertise HTMX (though we think it's pretty neat!), nor to document how to use it (HTMX's own [documentation](https://htmx.org/docs/) is quite comprehensive), but simply to provide some guidelines around its use in Nautobot.

## Detecting an HTMX request in a view

For piecemeal page rendering (like the object-list view example above), rather than write a separate Nautobot/Django view for each part of the page, it may be more convenient to implement a single view that behaves differently when requested via HTMX versus otherwise. Conveniently, HTMX requests always set the otherwise unset `HX-Request` header, so your code might do something like this:

```python
def get(request, **kwargs):
    if request.headers.get("HX-Request", False):
        # it's an HTMX request
        # perform partial rendering of expensive components as appropriate
        response = render(request, "components/htmx/my_fragment.html", ...)
    else:
        # not an HTMX request
        # perform full-page render, but with placeholders in the template for expensive components
        response = render(request, "my_page.html", ...)
```

However! If you do this, be aware that you need to also make sure that the web browser cache can recognizes that these are two different requests and responses (despite having the same URL and query parameters). The recommended way to do this is to use Django's `django.utils.cache.patch_vary_headers()` API to mark the response as differing based on that same `HX-Request` header:

```python
def get(request, **kwargs):
    if request.headers.get("HX-Request", False):
        # it's an HTMX request
        # perform partial rendering of expensive components as appropriate
        response = render(request, "components/htmx/my_fragment.html", ...)
    else:
        # not an HTMX request
        # perform full-page render, but with placeholders in the template for expensive components
        response = render(request, "my_page.html", ...)

    # Allow for the browser cache to distinguish between the two responses based on the HX-Request header
    patch_vary_headers(response, ["HX-Request"])
    return response
```
