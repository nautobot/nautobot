# HTMX and Nautobot

Nautobot makes use of the [HTMX](https://htmx.org/) library to improve the responsiveness, speed, and smoothness of various parts of the UI.

For example, clicking the "☆" next to an item in the navigation menu to mark it as a favorite uses HTMX to update the server-side user preferences, rerender and retrieve (only) the favorites submenu server-side, and seamlessly inject the updated submenu back into the navbar, all without a full-page browser refresh.

As another example, when loading any object-list view in Nautobot, to improve responsiveness, the initial page load renders all of the page *structure* (nav menu, headers, footers, filtering options, etc.) but an empty list of objects (displaying only a "loading" spinner), then uses HTMX to issue a second, asynchronous request to actually retrieve and render the contents of the object list (which may take significantly longer, depending on pagination and number of records), swapping them in seamlessly when retrieved.

The purpose of this document is not to advertise HTMX (though we think it's pretty neat!), nor to document how to use it (HTMX's own [documentation](https://htmx.org/docs/) is quite comprehensive), but simply to provide some guidelines around its use in Nautobot.

## Object List Views and HTMX

Beginning in Nautobot v3.1, object "list" views (those based on either `generic.ObjectListView` or `NautobotUIViewSet`) use HTMX to improve the responsiveness of the UI. Specifically, the initial (non-HTMX) browser request now renders the page *structure* (nav menu, headers, footers, filtering and saved view options, etc.) but does not initially load and populate the *contents* of the object list/table itself (or more specifically, it renders the table but with an always-empty `QuerySet.none()` as its initial data). Once that page is rendered, HTMX then issues a *second* request *to the same URL* (but this time with an additional HTTP header, `HX-Request: true`). The view code in Nautobot detects that additional header and this time loads the actual requested object QuerySet, renders and returns *just the object table HTML* (actually, the object table HTML plus a couple of associated HTML fragments for the "select all N objects" box above the table and the paginator below the table), and the client-side HTMX logic dynamically swaps these HTML fragments into the appropriate locations within the already-loaded page structure.

In practice, what this means for *users* is that previously slow-to-load list views (due to a high `PAGINATE_COUNT` or `per_page` setting, a large number of columns to display, or other reasons) become *visible and responsive* much faster than before, allowing the user to more immediately take actions like applying a saved view, filtering/sorting, etc., even if the actual time to fully render the object data remains more-or-less constant.

In practice, what this means for *developers* is that the change of behavior may necessitate some other code changes:

- If you're using the generic view or UIViewSet in its default way, it will "just work". However, if you have customized or overridden any part of the page rendering logic (e.g. `get()`, `get_template_name()`, `list()`, etc.) then you may need to update your custom code as described here and below.
- Similarly, if you're using the default template (`generic/object_list.html`), it will "just work", but if you've got a custom template, it may require some updates as well.
- Similarly, if you're using the generic `ViewTestCases` classes, they have already been updated and will "just work", but if you have any custom view test cases of your own for the list view, they may also require some updates.
    - Specifically, if you're testing for the *contents of the object list table*, you should make sure your test client is including the `HX-Request` header, for example `self.client.get(list_url, headers={"HX-Request": "true"})`, but conversely if you're testing for the *page structure as a whole*, you can and should omit that header. And if you're testing *both*, you may need to make two separate requests (one each with and without the `HX-Request` header, just like the actual browser behavior) and inspect each response separately as appropriate.
    - Note that this test change is *probably* backwards-compatible with Nautobot 3.0 (without the HTMX enhancements), as the older code will simply ignore the `HX-Request` header entirely.

## HTMX and Browser History/Cache

A core tenet of Nautobot's use of HTMX is that page state must be restorable/recoverable whether or not HTMX is in use. This means that if HTMX is used to dynamically render or alter part of the page content, the _end state_ of the page must be correct even after the user clicks their browser's "refresh/reload" and "back"/"forward" buttons.

For example, in the object-list views, choosing a different value from the "per-page" dropdown to change the pagination may use HTMX to re-load only the repaginated table rather than the whole browser page. If the user then clicks "Reload" to refresh the entire page, the refreshed page should continue to respect the _new_ per-page pagination rather than the _original_ pagination. Normally this is done by pushing an updated URL to the browser. This is typically done in HTMX by including the attribute `hx-push-url="true"` on any element whose action needs to do this.

However! In HTMX 2.0, `hx-push-url`, in addition to updating the displayed browser URL, also by default **adds the resulting HTML (page or fragment) associated with that HTMX request into the browser's local storage cache**. This can have various surprising and unintended side effects, most commonly seen when using the "back"/"forward" buttons in the browser to navigate to/from a page that used this API. Symptoms can include rendering of HTML fragments instead of the entire page as expected, JavaScript `DOMContentLoaded` callbacks applying multiple times, etc. We have found that the best way to work around this class of issues is to **disable this feature of HTMX** in Nautobot. This is done through a couple of directives in `nautobot/core/templates/inc/javascript.html` to set certain global HTMX config flags, and additionally through **setting the attribute `hx-history="false"` on any HTML template or fragment that might be returned by an HTMX request**.

Note that even the author of HTMX concedes that this history-caching behavior in HTMX 2.0 is [problematic and will be off by default](https://htmx.org/essays/the-fetchening/#no-locally-cached-history) in the (yet to be released as of this writing) HTMX 4.0:

> Another source of pain for both us and for htmx users is history support. htmx 2.0 stores history in local cache to make navigation faster. Unfortunately, snapshotting the DOM is often brittle because of third-party modifications, hidden state, etc. There is a terrible simplicity to the web 1.0 model of blowing everything away and starting over. There are also security concerns storing history information in session storage.
>
> In htmx 2.0, we often end up recommending that people facing history-related issues simply disable the cache entirely, and that usually fixes the problems.
>
> In htmx 4.0, history support will no longer snapshot the DOM and keep it locally.

In short:

!!! tip
    - Use `hx-push-url="true"` if a given HTMX request needs to update the browser's displayed URL
    - Use `hx-history="false"` on at least one element in any HTML template fragment that might be loaded through HTMX
    - When adding/changing any HTMX functionality, be sure to manually test with your browser's "back", "forward", and "refresh" buttons.

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
