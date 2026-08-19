# User Facing Messages

To display a user facing message in Nautobot, queue it through the [Django messages framework](https://docs.djangoproject.com/en/stable/ref/contrib/messages/).

```python
from django.contrib import messages

messages.success(request, f"Created device {device}.")
```

The message level — `info`, `success`, `warning`, or `error` — corresponds to the style of the message. A message belongs to a single request and is shown only once. Additionally, when the browser tab is active, the page polls every 15 seconds, so asynchronous messages queued after the page render still reach the user without requiring a full page reload.

!!! tip
    For a permanent notice your app puts on the page, add a [banner](banners.md) instead.

## Message Lifetime and Placement

+/- 3.3.0 "Messages now render as toasts by default, instead of alerts"

By default, a message is shown as a toast: a small notification in the top-right corner, overlaying the page, that dismisses itself after ten seconds. This default behavior is overridable via `extra_tags`, a space-separated keyword list, of which Nautobot recognizes the following:

| Tag | Effect                                                                               |
| --- |--------------------------------------------------------------------------------------|
| _(none)_ | Toast dismissed after ten seconds.                                                   |
| `indefinite` | Toast displayed until manually closed by a user.                            |
| `header_message` | Full-width alert at the top of the page, above the title, default behavior prior to 3.3.0. |

We recommend using `indefinite` when a user who steps away from their screen must not miss the message:

```python
messages.warning(request, "This job is already running; your changes will not take effect until it finishes.", extra_tags="indefinite")
```

Using `header_message` is recommended when the message has to be read before the rest of the page content:

```python
messages.error(request, "This device has no primary IP address, so it cannot be reached.", extra_tags="header_message")
```

An alert is displayed until manually closed by a user or until the page is reloaded, so `indefinite` has no meaning for it and is ignored if you combine the two.

!!! tip
    Use `indefinite` and `header_message` tags sparingly. A screen of notifications that never clear themselves is quick to become noise.

## Rendering Toasts Directly

+++ 3.3.0

Toasts are not limited to the messages framework. The `{% toast %}` template tag renders one directly, with an optional title, custom icon, call-to-action buttons, autohide delay, and more.

```django
{% load helpers %}

{% toast content="Synchronization finished." status="success" title="Done" %}
```

Toasts appended to the global `#toast-messages` container are automatically recognized by Nautobot's frontend scripting, and initialized immediately. A toast inserted elsewhere, after the page has loaded, for example from an HTMX response swapped into the middle of the page, stays hidden until you initialize it yourself:

```javascript
window.nb.messages.initializeToasts();
```
