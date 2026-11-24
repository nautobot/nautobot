# Using the Code and Diff Editor

Nautobot bundles the [Monaco editor](https://microsoft.github.io/monaco-editor/) and provides a small wrapper, `js/editor.js`, that Apps can use to display read-only code, an editable code field, or a diff of two texts. The editor follows the user's selected light or dark theme.

## Rendering an Editor

The editor wrapper is not part of Nautobot's main JavaScript bundle, so each page that uses it must load `js/editor.js` itself, in the template's `javascript` block as shown below. The script is small, and Monaco itself is only downloaded the first time an editor is created on the page.

With the script loaded, add an element with the `nb-editor-container` class. The editor is configured through `data-*` attributes:

| Attribute       | Description                                                                  |
| --------------- | ---------------------------------------------------------------------------- |
| `data-mode`     | Set to `diff` for a diff viewer; omit for a standard editor                  |
| `data-lang`     | Language syntax, such as `json`, `yaml`, `xml`, or `text`                    |
| `data-value`    | Initial content of a standard editor                                         |
| `data-original` | Original content of a diff viewer                                            |
| `data-modified` | Modified content of a diff viewer                                            |
| `data-options`  | JSON string of Monaco editor options, merged over Nautobot's default options |

```django
{% load static %}

{% block content %}
    <div class="nb-editor-container"
         data-mode="diff"
         data-lang="text"
         data-original="{{ original_text }}"
         data-modified="{{ modified_text }}"
         data-options='{"lineNumbers": "on"}'
         style="max-height: 800px">
    </div>
{% endblock content %}

{% block javascript %}
    {{ block.super }}
    <script src="{% static 'js/editor.js' %}"></script>
{% endblock javascript %}
```

Every `nb-editor-container` element that is present when the page loads is initialized automatically. The editor grows to fit its content, up to the element's CSS `max-height` if one is set.

## Rendering an Editor in Dynamically Loaded Content

+++ 3.2.10

Elements that are added to the page after it has loaded, such as the body of a modal or a tab that is populated by an AJAX request, are not initialized automatically. Use the `window.nb.editor` API to initialize and clean them up:

| Function                         | Description                                                                                                            |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `window.nb.editor.create(host)`  | Initializes an editor in the given `nb-editor-container` element, loading Monaco first if needed. Returns a `Promise`. |
| `window.nb.editor.dispose(host)` | Disposes the editor in the given element, if there is one. Call this before removing the element from the page.        |

Calling `create()` again on an element that already has an editor replaces that editor. If the editor cannot be initialized, an error message is shown in the element and the `Promise` resolves with `null`.

The recommended way to load such content is [HTMX](../../../core/htmx.md). For example, a button that opens a modal and loads a fragment containing an `nb-editor-container` element into its body:

```django
<button type="button"
        class="btn btn-primary"
        data-bs-toggle="modal"
        data-bs-target="#my-modal"
        hx-get="{% url 'plugins:my_app:my_diff_fragment' %}"
        hx-target="#my-modal .modal-body">
    Show diff
</button>
```

```javascript
const modalBody = document.querySelector("#my-modal .modal-body");

// Dispose the editors in the content that is about to be replaced
modalBody.addEventListener("htmx:beforeSwap", () => {
    modalBody.querySelectorAll(".nb-editor-container").forEach((host) => window.nb.editor.dispose(host));
});

// Initialize the editors in the content that was just loaded
modalBody.addEventListener("htmx:afterSwap", () => {
    modalBody.querySelectorAll(".nb-editor-container").forEach((host) => window.nb.editor.create(host));
});
```

`js/editor.js` must be loaded by the page itself, not by the fragment, because `window.nb.editor` has to exist before the content arrives. The page does not need to contain an `nb-editor-container` element when it loads.
