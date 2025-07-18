# New Nautobot Custom UI APIs

## Nautobot custom HTML data attributes and CSS classes

Up until v3.x, Nautobot has been *"smuggling"* its own CSS classes along with other 3rd party libraries. In v3.x we decided that it is only fair to be transparent about which of these are exclusive to Nautobot.

From now on, all HTML data attributes and CSS classes which refer to Nautobot custom functionalities are prefixed with `nb-*`.

Here's a list of what's changed:

| v2.x                                  | v3.0                                                                                              |
|---------------------------------------|---------------------------------------------------------------------------------------------------|
| `accordion-toggle`                    | `nb-collapse-toggle`                                                                              |
| `accordion-toggle-all`                | *removed*, refer to [Toggle All (Collapse All / Expand All)](#toggle-all-collapse-all-expand-all) |
| `banner-bottom`                       | `nb-banner-bottom`                                                                                |
| `btn-inline`                          | `nb-btn-inline-hover`, refer to [Hover Copy Buttons](#hover-copy-buttons)                         |
| `hover_copy`                          | *removed*, refer to [Hover Copy Buttons](#hover-copy-buttons)                                     |
| `hover_copy_button`                   | *removed*, refer to [Hover Copy Buttons](#hover-copy-buttons)                                     |
| `cable-trace`                         | `nb-cable-trace`                                                                                  |
| `active` (scoped to cable trace)      | `nb-active`                                                                                       |
| `cable` (scoped to cable trace)       | `nb-cable`                                                                                        |
| `node` (scoped to cable trace)        | `nb-node`                                                                                         |
| `termination` (scoped to cable trace) | `nb-termination`                                                                                  |
| `trace-end` (scoped to cable trace)   | `nb-trace-end`                                                                                    |
| `color-block`                         | `nb-color-block`                                                                                  |
| `inline-color-block`                  | *removed*                                                                                         |
| `editor-container`                    | `nb-editor-container`                                                                             |
| `filter-container`                    | *removed*, refer to [Multi-badge](#multi-badge)                                                   |
| `display-inline` (scoped to filters)  | *removed*, refer to [Multi-badge](#multi-badge)                                                   |
| `filter-selection`                    | *removed*, refer to [Multi-badge](#multi-badge)                                                   |
| `filter-selection-choice`             | *removed*, refer to [Multi-badge](#multi-badge)                                                   |
| `filter-selection-choice-remove`      | *removed*, refer to [Multi-badge](#multi-badge)                                                   |
| `filter-selection-rendered`           | *removed*, refer to [Multi-badge](#multi-badge)                                                   |
| `remove-filter-param`                 | *removed*, refer to [Multi-badge](#multi-badge)                                                   |
| `loading` (scoped to AJAX loaders)    | `nb-loading`                                                                                      |
| `required` (scoped to form labels)    | `nb-required`                                                                                     |
| `noprint`                             | *removed*, use `d-print-none` instead                                                             |
| `powered-by-nautobot`                 | *removed*                                                                                         |
| `report-stats`                        | `nb-report-stats`                                                                                 |
| `right-side-panel`                    | `nb-right-side-panel`                                                                             |
| `software-image-hierarchy`            | `nb-software-image-hierarchy`                                                                     |
| `tree-hierarchy`                      | `nb-tree-hierarchy`                                                                               |
| `tiles`                               | `nb-tiles`                                                                                        |
| `tile`                                | `nb-tile`                                                                                         |
| `clickable` (scoped to tiles)         | `nb-clickable`                                                                                    |
| `disabled` (scoped to tiles)          | `nb-disabled`                                                                                     |
| `tile-description`                    | `nb-tile-description`                                                                             |
| `tile-footer`                         | `nb-tile-footer`                                                                                  |
| `tile-header`                         | `nb-tile-header`                                                                                  |

## Table configuration button

Configurable table columns are no novelty for Nautobot. However, when we redesigned user interface in v3.x, we also changed the way table configuration buttons are rendered, and as result they are now more coupled with tables they manage. Table configuration buttons are no longer standalone buttons on the page, instead they are rendered in the top right header cell of any **configurable** table.

!!! note
    Generic Nautobot list views provide this feature out of the box and do not require you to do anything. This guide is relevant only for templates other than generic Nautobot list views.

1. You are no longer responsible for rendering table configuration buttons in templates, and you should remove existing `{% table_config_button ... %}` template tag usages.
2. Tables with customizable columns are now explicitly **configurable**. You are required to do one of the following to enable table configurability:
    - Pass `configurable=True` keyword argument to constructor of a standard table which inherits from `BaseTable`.
    - Set `self.configurable = True` property in custom table class object utilizing core `table.html` template under the hood.
    - Manually include `{% table_config_button table %}` in top right header cell if table class has its own custom template.

## Table action buttons

In v3.x we moved table action buttons to dropdown menus. It does not affect the way buttons work, but impacts the way they are presented. Tables using standard core `ButtonsColumn` ship with this feature already implemented.

In case you provided your own HTML in `prepend_template`, you need to migrate flat buttons to dropdown menu items. Below is an example of how has `prepend_template` changed, for more details see [how to upgrade Dropdowns](./upgrading-from-bootstrap-v3-to-v5.md#dropdowns).

!!! warning
    If you used `TemplateColumn` to render table action buttons, you are not required to do anything, and they will continue operating the way they did. However, since v3.x it is Nautobot design system recommendation to display table action buttons within dropdown menus.

Nautobot v2.x:

```html
<button
    data-url="{% url 'extras:gitrepository_sync' pk=record.pk %}"
    type="submit" class="btn btn-primary btn-xs sync-repository"
    title="Sync" {% if not perms.extras.change_gitrepository %}disabled="disabled"{% endif %}
>
    <i class="mdi mdi-source-branch-sync" aria-hidden="true"></i>
</button>
```

Nautobot v3.x:

```html
<li>
    <button
        data-url="{% url 'extras:gitrepository_sync' pk=record.pk %}"
        type="submit"
        class="dropdown-item sync-repository{% if perms.extras.change_gitrepository %} text-primary"{% else %}" disabled="disabled"{% endif %}
    >
        <span class="mdi mdi-source-branch-sync" aria-hidden="true"></span>
        Sync
    </button>
</li>
```

## Drawer

In addition to [Bootstrap v5.x Offcanvas](https://getbootstrap.com/docs/5.3/components/offcanvas/), Nautobot v3.x ships with its own Drawer component. These are the most notable differences between them:

| Offcanvas                                                              | Drawer                                                                             |
|------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| Generic Bootstrap v5.x component with many configurable options.       | Tailored for specific use cases without much configurability involved.             |
| Renders in front of everything else overlaying given side of the page. | Occupies right-hand side of the page pushing the rest of its content further left. |

In Nautobot we use Drawer more often than Offcanvas but as usual, there is no one-size-fits-all and both components have their strengths and weaknesses.

The best place to see how to use Offcanvas is Bootstrap v5.x documentation. For Drawer, let's take a look example below:

```html
<!-- Drawer toggle button -->
<button
    type="button"
    class="btn btn-secondary"
    data-nb-toggle="drawer"
    data-nb-target="#myDrawer"
    aria-expanded="false"
    aria-controls="myDrawer"
>
    <span class="mdi mdi-view-compact-outline" aria-hidden="true"></span>
    <span class="visually-hidden">Saved Views</span>
</button>

<!-- Drawer -->
{% block drawer %}
    <section class="nb-drawer" tabindex="-1" id="myDrawer">
        <div class="nb-drawer-header">
            <h1>My drawer</h1>
            <button type="button" class="btn-close" data-nb-dismiss="drawer" aria-label="Close"></button>
        </div>
        <div class="nb-drawer-body">
            My drawer body.
        </div>
    </section>
{% endblock %}
```

### Table Drawers

Some of the components converted from modals to drawers are table related forms and controls - Config, Filters and Saved Views. As result, `filter_form_modal.html` template and `{% filter_form_modal %}` template tag have been renamed to `filter_form_drawer.html` and `{% filter_form_drawer %}` respectively.

## Draggable

Nautobot v2.1 introduced reorderable panels on the homepage. In v3.0 we internally standardized reordering items with native [HTML Drag and Drop API](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API) and now are ready to give it away to use in Nautobot apps as well. Here's what you need to know about Nautobot draggable API:

1. First and foremost, Nautobot draggable API is tailored specifically for reordering elements. In case your feature requires other kinds of drag and drop behavior, you still have to implement it on your own.
2. Drag and drop interactive area must be surrounded by a wrapper element of `nb-draggable-container` class.
3. Draggable elements must have the `nb-draggable` class and a unique `id`. Note that you should not attribute these elements with `draggable=true` in HTML because this is already handled by Nautobot core draggable script.
4. Drag handle requires `nb-draggable-handle` class. Handle is the element you can interact with to grab `nb-draggable`. If an entire `nb-draggable` is intended to be *"grabbable"*, it should be given both `nb-draggable` and `nb-draggable-handle` classes.
5. To subscribe to the DOM node order changes, for example to be able to save it in a persistent storage, create a custom JavaScript script to observe `nb-draggable-container` using native `MutationObserver` with `{ childList: true }` config.

```html
<ul class="list-group nb-draggable-container">
    <li class="list-group-item nb-draggable" id="draggable-1">
        <button class="btn nb-draggable-handle">Grab me 1</button>
    </li>
    <li class="list-group-item nb-draggable" id="draggable-2">
        <button class="btn nb-draggable-handle">Grab me 2</button>
    </li>
    <li class="list-group-item nb-draggable" id="draggable-3">
        <button class="btn nb-draggable-handle">Grab me 3</button>
    </li>
</ul>

<script>
    (() => {
        window.addEventListener('DOMContentLoaded', () => {
            const draggableContainer = document.querySelector('.nb-draggable-container');
            const mutationObserver = new MutationObserver(() => {
                // Do something, for example save the new element order to a persistent storage.
            });
            mutationObserver.observe(draggableContainer, { childList: true });
        });
    })();
</script>
```

## Form Sticky Footers

It is now recommended to use sticky footers to host action buttons in all Nautobot forms. Nautobot implements the `nb-form-sticky-footer` CSS class to achieve this behavior, but it requires a certain page structure to function properly - sticky footer container should occupy the entire remaining browser viewport height and push the footer down to the bottom of the page. Let's take a look at an example:

```html
<form class="h-100 vstack">
    {% csrf_token %}
    <div class="row align-content-start flex-fill">
        <!-- Form content goes here, it is irrelevant for this example. -->
    </div>
    <div class="nb-form-sticky-footer">
        <button type="submit" class="btn btn-primary">
            <span aria-hidden="true" class="mdi mdi-check me-4"></span><!--
            -->Submit
        </button>
        <a href="{{ return_url }}" class="btn btn-secondary">
            <span aria-hidden="true" class="mdi mdi-close me-4"></span><!--
            -->Cancel
        </a>
    </div>
</form>
```

## Hover Copy Buttons

Hover Copy Buttons work as before but they require little adjustments to their existing implementations. Here's what's changed:

1. `btn-inline` CSS class has been renamed to `nb-btn-inline-hover` and it is now the sole indicator that a button is expected to be hidden when idle and only appear on hover.
2. `hover_copy` CSS class has been removed and is no longer required for annotating Hover Copy Button parent elements. Instead, hover button now always appears while hovering over its immediate parent, regardless of set classes and data attributes.
3. `hover_copy_button` CSS class has also been removed.

Before:

```html
<span class="hover_copy">
    <span id="uuid_copy">{{ object.id }}</span>
    <button class="btn btn-inline btn-default hover_copy_button" data-clipboard-target="#uuid_copy">
        <span class="mdi mdi-content-copy"></span>
    </button>
</span>
```

After:

```html
<span>
    <span id="uuid_copy">{{ object.id }}</span>
    <button class="btn btn-secondary nb-btn-inline-hover" data-clipboard-target="#uuid_copy">
        <span aria-hidden="true" class="mdi mdi-content-copy"></span>
        <span class="visually-hidden">Copy</span>
    </button>
</span>
```

## Toggle All (Collapse All / Expand All)

To extend the basic Bootstrap 5 Accordion and Collapse components functionality, Nautobot delivers a Toggle All (Collapse all / Expand all) button implementation. Although Bootstrap 5 is shipped with a feature to toggle multiple collapsibles with a single button, it treats controlled elements individually rather than collectively, by inverting their current state and not by forcing them to collapse or expand, as we would expect. Depending on desired behavior, you are free to choose between the default Bootstrap 5 or custom Nautobot mechanisms.

Most of the logic is already implemented in Nautobot by default and there are just two data attributes that control a Toggle All (Collapse All / Expand All) button:

1. `data-nb-toggle="collapse-all"` - mandatory, indicates that given button is of Toggle All (Collapse All / Expand All) type.
2. `data-nb-target="{collapse CSS selector}"` - optional, specifies which collapse elements does the button control; when not explicitly set, target collapse CSS selector falls back to `".collapse"`.

```html
<button
    aria-expanded="true"
    class="btn btn-secondary"
    data-nb-toggle="collapse-all"
    data-nb-target="#accordion .collapse"
    type="button"
>
    Collapse All
</button>
```

## Multi-badge

In place of legacy `filter-container` and `filter-selection`, Nautobot 3.0 introduces a general purpose Multi-badge component to serve as a container for multiple badges.

1. Use both `badge` and `nb-multi-badge` CSS classes on an element to make it a multi-badge container.
2. Wrap `badge` child elements of a multi-badge container in an element of `nb-multi-badge-items` CSS class.
3. Like basic badges, multi-badge and badges inside it support clear/remove buttons.

```html
<span class="badge nb-multi-badge">
    Multi-badge:
    <span class="nb-multi-badge-items">
        <span class="badge">Badge</span>
        <span class="badge">Badge</span>
    </span>
</span>
```

```html
<span class="badge nb-multi-badge">
    <button type="button">
        <span aria-hidden="true" class="mdi mdi-close"></span>
        <span class="visually-hidden">Remove All</span>
    </button>
    Multi-badge:
    <span class="nb-multi-badge-items">
        <span class="badge"><!--
            --><button type="button">
                <span aria-hidden="true" class="mdi mdi-close"></span>
                <span class="visually-hidden">Remove</span>
            </button><!--
            -->Badge
        </span>
        <span class="badge"><!--
            --><button type="button">
                <span aria-hidden="true" class="mdi mdi-close"></span>
                <span class="visually-hidden">Remove</span>
            </button><!--
            -->Badge
        </span>
    </span>
</span>
```

## Extended Bootstrap Utilities

Nautobot extends Bootstrap utilities with its own subset of CSS classes, properties and values.

!!! note
    We elaborate more on [Bootstrap v5.x Helpers and Utilities](./upgrading-from-bootstrap-v3-to-v5.md#helper-classes-helpers-and-utilities) in another migration guide.

| Class                     | Style                              |
|---------------------------|------------------------------------|
| `nb-color-transparent`    | `color: transparent;`              |
| `nb-cursor-unset`         | `cursor: unset;`                   |
| `nb-text-none`            | `text-transform: none;`            |
| `nb-transition-base`      | `transition: all .2s ease-in-out;` |
| `nb-transition-fade`      | `transition: opacity .15s linear;` |
| `nb-transition-none`      | `transition: none;`                |
| `nb-w-0`                  | `width: 0;`                        |
| `nb-w-0`                  | `width: 0;`                        |
| `nb-z-dropdown`           | `z-index: 1000;`                   |
| `nb-z-sticky`             | `z-index: 1020;`                   |
| `nb-z-fixed`              | `z-index: 1030;`                   |
| `nb-z-offcanvas-backdrop` | `z-index: 1040;`                   |
| `nb-z-offcanvas`          | `z-index: 1045;`                   |
| `nb-z-modal-backdrop`     | `z-index: 1050;`                   |
| `nb-z-modal`              | `z-index: 1055;`                   |
| `nb-z-popover`            | `z-index: 1070;`                   |
| `nb-z-tooltip`            | `z-index: 1080;`                   |
| `nb-z-toast`              | `z-index: 1090;`                   |
