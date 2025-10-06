# Upgrading from Bootstrap v3 to v5

With the release of Nautobot v3.0, the UI has undergone significant improvements to enhance usability, flexibility, and maintainability. This version introduces an upgrade from [Bootstrap v3.4](https://getbootstrap.com/docs/3.4/) to [Bootstrap v5.3](https://getbootstrap.com/docs/5.3/). This transition brings modern UI enhancements, improved accessibility, and better responsiveness. While these changes provide a more consistent and intuitive user experience, they also introduce necessary modifications that may impact existing custom UI components and templates.

The following is a detailed migration guide outlining the steps to help app authors update their app's UI for compatibility with the Bootstrap upgrade. Additional changes that are needed and might not be captured here can be found in the [Bootstrap 5.x migration guide](https://getbootstrap.com/docs/5.3/migration/).

!!! note
    This document does not cover all the UI/UX changes brought to Bootstrap and Nautobot components. Instead, this guide scope is narrowed down to only the technicalities concerning HTML element structures and attributes, and CSS class names.

## Dependency management

Bootstrap v5.x JavaScript now uses vanilla JavaScript and jQuery dependency has been removed. For now, Nautobot will keep supporting jQuery for backward compatibility, but consider it marked as **deprecated**. Ensure that your custom scripts do not rely on jQuery and jQuery-based Bootstrap v3.4.1 functions.

In case you were not using any plugins and had not maintained your own custom CSS or JS code dependent on jQuery or Bootstrap v3.4.1, you don't need to do anything related to dependency management.

Otherwise, you will need to individually review whether the packages and/or modules you are using, are still compatible with Bootstrap 5.x and in case they are not, update them accordingly.

## Migration Script

When Nautobot v3.x is installed, in addition to the `nautobot-server` CLI command, it now also provides a `nautobot-migrate-bootstrap-v3-to-v5` CLI command. This command can be run against your App's `templates` directory in order to autocorrect and/or flag for manual correction many of the below-documented required changes to your CSS and HTML.

```no-highlight
nautobot-migrate-bootstrap-v3-to-v5 my_app/templates/ --resize
```

!!! tip "The `--resize` flag"
    The first time you run `nautobot-migrate-bootstrap-v3-to-v5`, you should use the `--resize` optional parameter, which will resize all Bootstrap column breakpoints in your templates to use the next larger breakpoint. (See [Columns](#columns) below for the details of why this is recommended.) This is the only part of the script that is not idempotent and should not be rerun repeatedly, as each time the script is run with `--resize`, it will adjust the breakpoints upward again. Therefore, on all subsequent runs of the script against your app, you should omit this parameter. Besides this special case, it is otherwise safe to run the script multiple times if desired.

```no-highlight
nautobot-migrate-bootstrap-v3-to-v5 my_app/templates/
```

You can also run the script against a single template file if desired:

```no-highlight
nautobot-migrate-bootstrap-v3-to-v5 my_app/templates/my_app/my_template.html
```

When run, the script will produce verbose output documenting the files that it is changing, any files that it cannot fix up automatically in full that will need manual review, and finally a summary of the overall results:

```no-highlight
→ object_new_team.html: 2 class replacements, 6 panel replacements,
→ metadatatype_create.html: 3 class replacements, 9 panel replacements,
→ graphqlquery_retrieve.html: 4 class replacements, 7 panel replacements,
→ role_retrieve.html: 23 class replacements, 36 panel replacements,
→ approvalworkflowdefinition_update.html: 2 class replacements, 6 panel replacements,
→ inc/configcontext_format.html: 1 class replacements,
  !!! Manual review needed for nav-item fixes at:
    - nautobot/extras/templates/extras/inc/configcontext_format.html - Please review manually 'btn {% if format == 'json' %}btn-primary{% else %}btn-default{% endif %}'

...

=== Global Summary ===
Total issues fixed: 417
- Class replacements:          149
- Extra-breadcrumb fixes:      0
- <li> in <ol.breadcrumb>:     5
- <li> in <ul.nav-tabs>:       6
- Panel class replacements:    257
- Resizing breakpoint xs:      0
-------------------------------------
- Resizing other breakpoints:  0
```

In the case of the above output snippet, you can see that while the script fixed 417 migration issues automatically, it encountered some uncertainty in `nautobot/extras/templates/extras/inc/configcontext_format.html`, likely due to the Django template logic wrapping the `btn-primary` and `btn-default` classes. In this case you'd (as documented below in [Buttons](#buttons)) likely want to manually replace the `btn-default` case with `btn-secondary`.

## Overview of High-Level Changes

### Bootstrap `data-*` attributes

In Bootstrap v5.x, some reused native HTML attributes became `data-*` attributes for less ambiguity. In addition to that, all custom Bootstrap `data-*` attributes are prefixed with an additional `bs-` for even more clarity. For example, `data-toggle="collapse"` is now `data-bs-toggle="collapse"`, and Tooltip's `title` attribute has been changed to `data-bs-title`.

=== "Bootstrap v3"

    ```html
    <a class="btn btn-primary" data-toggle="collapse" href="#collapse" role="button" aria-expanded="false" aria-controls="collapse">Toggle collapse</a>
    <button type="button" class="btn btn-default" data-toggle="tooltip" title="Custom tooltip">Custom tooltip</button>
    <button data-toggle="modal" data-target="#myModal">Open Modal</button>
    <button class="close" data-dismiss="alert">×</button>
    ```

=== "Bootstrap v5"

    ```html
    <a class="btn btn-primary" data-bs-toggle="collapse" href="#collapse" role="button" aria-expanded="false" aria-controls="collapse">Toggle collapse</a>
    <button type="button" class="btn btn-secondary" data-bs-toggle="tooltip" data-bs-title="Custom tooltip">Custom tooltip</button>
    <button data-bs-toggle="modal" data-bs-target="#myModal">Open Modal</button>
    <button class="btn-close" data-bs-dismiss="alert"></button>
    ```

### Helper classes / Helpers and Utilities

One major difference between Bootstrap v3 and v5 is that [Helper classes](https://getbootstrap.com/docs/3.4/css/#helper-classes) no longer exist. Instead, they were replaced with [Helpers](https://getbootstrap.com/docs/5.3/helpers/) and [Utilities](https://getbootstrap.com/docs/5.3/utilities/) which offer far more comprehensive set of CSS classes for styling elements on the page without having to write custom CSS. Below is a table with helpers and utilities that correspond to former helper classes for a quick search-and-replace reference. Items not listed here did not change and can be left as-is.

| Helper class        | Utility                                                                                                                    |
|---------------------|----------------------------------------------------------------------------------------------------------------------------|
| `text-muted`        | `text-secondary`                                                                                                           |
| `text-left`         | `text-start`                                                                                                               |
| `text-right`        | `text-end`                                                                                                                 |
| `close`             | `btn-close` *(technically speaking, close button is a component now, not a helper or utility)*                             |
| `caret`             | *removed, use an icon from icon library instead*                                                                           |
| `pull-left`         | `float-start`                                                                                                              |
| `pull-right`        | `float-end`                                                                                                                |
| `center-block`      | `d-block mx-auto` *(consider using flexbox for content centering)*                                                         |
| `show`              | `d-block`                                                                                                                  |
| `hidden`            | `d-none`                                                                                                                   |
| `sr-only`           | `visually-hidden`                                                                                                          |
| `sr-only-focusable` | `visually-hidden-focusable` **(must not be used in combination with the `visually-hidden` class)**                         |
| `text-hide`         | *removed, as per Bootstrap v5.0 documentation: "it’s an antiquated method for hiding text that shouldn’t be used anymore"* |

It is highly encouraged to at least briefly familiarize with Bootstrap v5.x documentation on Helpers and Utilities and the array of possibilities they provide, because in many cases they can relieve developers from the burden of writing custom CSS code. At the same time, mind that not all default Bootstrap maps can be treated as source of truth, there are several Nautobot overwrites which, most notably, include [spacing](#spacing-ie-margins-and-paddings).

### Spacing (i.e. margins and paddings)

To avoid unnecessary mapping of abstract to pixel values, Nautobot defines spacing sizes in straightforward concrete pixel values. On one hand it requires developers to think about pixels rather than semantic meaning of a particular spacing but on the other, there really are no spacing guidelines for Bootstrap nor Nautobot, so these abstract names would be arbitrary and made up anyway. Available sizes are:

```no-highlight
0: 0
1: 1px
2: 2px
4: 4px
6: 6px
8: 8px
10: 10px
12: 12px
14: 14px
16: 16px
20: 20px
24: 24px
auto: auto
```

Negative margins are also supported. They require preceding requested size with an `n`.

Example:

```html
<div class="p-4"></div> <!-- padding: 4px; -->
<div class="px-10"></div> <!-- padding-left: 10px; padding-right: 10px; -->
<div class="my-n8"></div> <!-- margin-bottom: -8px; margin-top: -8px; -->
```

!!! note
    Everything presented in this section was simplified for the default font size equal to `16px`. Were this value overwritten, for accessibility concerns Bootstrap and Nautobot define all sizes in `rem` units, which scale in relation to document root font size, a practice also recommended for app developers.

### Grid

!!! note
    It is recommended that instead of using `float-start` and `float-end` classes, you should use the [grid system](https://getbootstrap.com/docs/5.3/layout/grid/) in Bootstrap v5.x for a more structured approach to positioning elements and layout.

- Bootstrap v5.x now has `position-relative`, `position-absolute`, etc. to help you to position elements on the page.
- Bootstrap v3.4.1 grid system:
    - Uses 12-column grid system.
    - Requires explicit breakpoint prefixes (`xs`, `sm`, `md`, `lg`).
    - Column widths are fixed per breakpoint.
    - `col-*-offset-*` classes control horizontal positioning.
- Bootstrap v5.x grid system:
    - No more `xs` breakpoint.
    - Uses `col-*` auto-sizing if not specified (no need for exact column width).
    - Specifies `gutter` width via `g-*` classes.
    - Specifies column horizontal offset with `offset-*`, though other new utilities are available to control positioning as well and may be preferable.

Above is a short summary for the positioning and layout changes in Bootstrap v5.x, see more details in the Bootstrap v5.x documentation about [columns](https://getbootstrap.com/docs/5.3/layout/columns/), [float](https://getbootstrap.com/docs/5.3/utilities/float/), and [position](https://getbootstrap.com/docs/5.3/utilities/position/).

### Responsive utilities

Bootstrap v3.4.1 shipped with [Responsive utilities](https://getbootstrap.com/docs/3.4/css/#responsive-utilities) which provided simple mechanisms to display and hide elements on various screen sizes and for print. Bootstrap v5.x takes this idea a step further and delivers media breakpoints for **all** [Helpers and Utilities](#helper-classes-helpers-and-utilities), no longer constraining responsive utility classes to an arbitrary set.

- Breakpoint values and names have changed, refer to [Bootstrap v3.4.1 breakpoints](https://getbootstrap.com/docs/3.4/css/#responsive-utilities-classes) and [Bootstrap v5.x breakpoints](https://getbootstrap.com/docs/5.3/layout/breakpoints/#available-breakpoints) for more detail.
- `xs` breakpoint no longer exists (at least not in CSS class names). It is a result of Bootstrap v5.x (and web, in general) mobile-first approach which defaults layouts to the smallest breakpoint available and goes up from there. Do not worry, it does not mean you have to support mobile layouts. But in case you do, see how is `xs` migrated in examples below.
- `hidden-xs` is replaced by `d-block d-sm-none` (hide on extra small). Note the change from `xs` to `sm` due to the change in layout breakpoint sizes in Bootstrap v5.
- `visible-xs` is replaced by `d-none d-sm-block` (show on extra small).

## Guidance on Specific Cases

### Breadcrumbs

In general you may want to migrate to defining your breadcrumbs [in the Python view code](../ui-component-framework/breadcrumbs-titles.md) instead of defining them directly in an HTML template. If your breadcrumbs are still defined in HTML, the following changes are needed:

- Breadcrumb item is changed from `<li>` to `<li class="breadcrumb-item">`.
- Active breadcrumb item is changed from `<li class="active">Data</li>` to `<li class="breadcrumb-item active" aria-current="page">Data</li>`.

=== "Bootstrap v3"

    ```html
    <ol class="breadcrumb">
        <li><a href="#">Home</a></li>
        <li><a href="#">Library</a></li>
        <li class="active"><a href="#">Data</a></li>
    </ol>
    ```

=== "Bootstrap v5"

    ```html
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="#">Home</a></li>
        <li class="breadcrumb-item"><a href="#">Library</a></li>
        <li class="breadcrumb-item active" aria-current="page"><a href="#">Data</a></li>
    </ol>
    ```

### Buttons

- `btn-default` is replaced by `btn-secondary`. *Nautobot will keep supporting `btn-default` class, nevertheless it is recommended to replace old `btn-default` class name with `btn-secondary`.*
- `btn-xs` (extra small) is removed; use `btn-sm` as the smallest size. *Similarly to `btn-default` and `btn-secondary`, Nautobot will keep supporting `btn-xs` class but despite its name, it looks and behaves exactly the same as `btn-sm`.*
- `close` is replaced by `btn-close` as mentioned above in [Helper classes / Helpers and Utilities](#helper-classes-helpers-and-utilities).

=== "Bootstrap v3"

    ```html
    <button class="btn-default"></button>
    <button class="close" data-dismiss="alert">×</button>
    ```

=== "Bootstrap v5"

    ```html
    <button class="btn-secondary"></button>
    <button class="btn-close" data-bs-dismiss="alert"></button>
    ```

### Columns

See more details in the Bootstrap v5.x documentation about [columns](https://getbootstrap.com/docs/5.3/layout/columns/), but generally speaking you'll need to make two types of changes to your column definitions:

1. Increase to the next larger breakpoint (see note below).
2. Replace `col-<breakpoint>-offset-<amount>` with `offset-<breakpoint>-<amount>`.

!!! note "Generally increase column breakpoints by one stage when migrating"
    A subtle change between Bootstrap v3 and v5 columns, in addition to the removal of `xs`, is that the other grid breakpoints have generally changed. For example, in v3, a `col-sm-4` would apply to windows up to 768px in size, but in v5, `col-sm-4` applies only up to 576px in size while `col-md-4` applies to windows between 577px and 768px. The net result of this change is that *in general* you will want to adjust all size-specific column definitions "up" one size increment, so `col-sm-*` becomes `col-md-*`, `col-md-*` becomes `col-lg-*`, etc.

    That said, you may also want to refer to the Bootstrap v5 docs linked above to see if you can simplify your HTML/CSS classes to achieve the desired results more simply with the new grid features in Bootstrap v5.

=== "Bootstrap v3"

    ```html
    <div class="row">
        <div class="col-md-4 col-md-offset-4">
            This column is 4 wide (1/3 the page width) and offset by 4 (making it centered) at breakpoint "md" and smaller.
        </div>
    </div>
    ```

=== "Bootstrap v5"

    ```html
    <div class="row">
        <div class="col-lg-4 offset-lg-4">
            This column is 4 wide (1/3 the page width) and offset by 4 (making it centered) at breakpoint "lg" and smaller.
        </div>
    </div>
    ```

=== "Bootstrap v5 (alternate)"

    ```html
    <div class="row">
        <div class="col-lg-4 mx-auto">
            This column is 4 wide (1/3 the page width) and centered (automatic left/right margins) on breakpoint "lg" and smaller.
        </div>
    </div>
    ```

### Dropdowns

Complete Bootstrap 5.x dropdowns documentation can be found at: [https://getbootstrap.com/docs/5.3/components/dropdowns/](https://getbootstrap.com/docs/5.3/components/dropdowns/).

In Bootstrap v3.4.1, dropdowns were kind of second class citizens, missing out much on configurability mainly due to just a handful of dedicated classes. Bootstrap v5.x amends that and to some extent redefines dropdown HTML structure and attributes, and CSS classes.

Differences include:

- Dropdown wrapper component is no longer of class `btn-group` but `dropdown` instead.
- Dropdown toggle button `data-toggle` attribute has been renamed to `data-bs-toggle`, and `aria-haspopup` attribute is no longer recommended.
- As already mentioned in [Helper classes / Helpers and Utilities](#helper-classes-helpers-and-utilities) section above, if dropdown toggle button used `caret` element, it must be replaced by an icon from available icon library.
- Likewise, if dropdown toggle button used a descriptive text of class `sr-only`, it should be changed to `visually-hidden`.
- List items do not expect any particular CSS class but elements within them do. This is especially relevant for separators (dividers).
- Clickable items (mainly `button` and `a` elements) should be of `dropdown-item` class.
- Separators (dividers) should be `hr` elements with `dropdown-divider` class.

Let's take a look at this example from [Bootstrap v3.4.1 Single button dropdowns](https://getbootstrap.com/docs/3.4/components/#btn-dropdowns-single) documentation and how to migrate it over to Bootstrap v5.x:

=== "Bootstrap v3"

    ```html
    <div class="btn-group">
        <button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
            Action <span class="caret"></span>
        </button>
        <ul class="dropdown-menu">
            <li><a href="#">Action</a></li>
            <li><a href="#">Another action</a></li>
            <li><a href="#">Something else here</a></li>
            <li role="separator" class="divider"></li>
            <li><a href="#">Separated link</a></li>
        </ul>
    </div>
    ```

=== "Bootstrap v5"

    ```html
    <div class="dropdown">
        <button type="button" class="btn btn-secondary dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false">
            Action <span class="mdi mdi-chevron-down"></span>
        </button>
        <ul class="dropdown-menu">
            <li><a href="#" class="dropdown-item">Action</a></li>
            <li><a href="#" class="dropdown-item">Another action</a></li>
            <li><a href="#" class="dropdown-item">Something else here</a></li>
            <li><hr class="dropdown-divider"></li>
            <li><a href="#" class="dropdown-item">Separated link</a></li>
        </ul>
    </div>
    ```

### Forms

- Class `form-group` is removed; in most Nautobot model forms it should be replaced by `mb-10 d-flex justify-content-center`.
    - In the specific case of "drawer" forms (filter forms, table config, etc.), where limited horizontal space is available, you can use class `nb-form-group` instead.
- Class `control-label` is removed; in most Nautobot model forms it should be replaced by `col-form-label` ([https://getbootstrap.com/docs/5.3/forms/layout/#horizontal-form](https://getbootstrap.com/docs/5.3/forms/layout/#horizontal-form)).
    - In the specific case of "drawer" forms using `nb-form-group`, you should use class `form-label` instead ([https://getbootstrap.com/docs/5.3/migration/#forms-1](https://getbootstrap.com/docs/5.3/migration/#forms-1)).
- Class `form-control-static` is replaced by `form-control-plaintext`.
- Class `help-block` is replaced by `form-text`.
- Classes `checkbox` and `checkbox-inline` are removed; use `form-check` and `form-check-input` instead: [https://getbootstrap.com/docs/5.3/forms/checks-radios/#checks](https://getbootstrap.com/docs/5.3/forms/checks-radios/#checks).
- Required form fields should use class `nb-required` on their `label` element.

### Labels / Badges

- `label` is replaced with `badge`.
- The contextual classes (e.g. `label-primary`, `label-success`) now use the general-purpose classes (`bg-primary`, `bg-success`, etc.).

=== "Bootstrap v3"

    ```html
    <span class="label label-primary">Primary</span>
    <span class="label label-success">Success</span>
    <span class="label label-danger">Danger</span>
    ```

=== "Bootstrap v5"

    ```html
    <span class="badge bg-primary">Primary</span>
    <span class="badge bg-success">Success</span>
    <span class="badge bg-danger">Danger</span>
    ```

### Horizontal rules

By default, [Horizontal rules](https://getbootstrap.com/docs/5.3/content/reboot/#horizontal-rules) inherit their color from text. To draw a line with standard Nautobot border color, use `border-top` CSS class on the `<hr>` element.

```html
<!-- Inherit color from text. -->
<hr>

<!-- Set color to standard Nautobot border color. -->
<hr class="border-top">
```

### Paginators

- `page-item` class needs to be applied to `<li>` elements.
- `page-link` class needs to be applied to `<a>` elements.
- `active` and `disabled` classes are now applied to outer `page-item` element (`<li>`) instead of inner `page-link` (`<a>`).
- Replace icons with HTML character entities:
    - `<i class="mdi mdi-chevron-double-left"></i>` with `<span aria-hidden="true">&laquo;</span>`.
    - `<i class="mdi mdi-chevron-double-right"></i>` with `<span aria-hidden="true">&raquo;</span>`.

=== "Bootstrap v3"

    ```html
    <ul class="pagination">
        <li class="disabled"><a href="#previous_page"><i class="mdi mdi-chevron-double-left"></i></a></li>
        <li class="active"><a href="#">1</a></li>
        <li><a href="#">2</a></li>
        <li><a href="#">3</a></li>
        <li><a href="#"><i class="mdi mdi-chevron-double-left"></i></a></li>
    </ul>
    ```

=== "Bootstrap v5"

    ```html
    <ul class="pagination">
        <li class="page-item disabled"><a class="page-link" href="#" aria-disabled="true"><span aria-hidden="true">&laquo;</span></a></li>
        <li class="page-item active" aria-current="page"><a class="page-link" href="#">1</a></li>
        <li class="page-item"><a class="page-link" href="#">2</a></li>
        <li class="page-item"><a class="page-link" href="#">3</a></li>
        <li class="page-item"><a class="page-link" href="#"><span aria-hidden="true">&raquo;</span></a></li>
    </ul>
    ```

### Panels / Cards

- `panel` class is no longer available, use `card` instead.
- `panel-heading` class is replaced by `card-header`.
- `panel-body` class is replaced by `card-body`. Note that `card-body` is not required as `card` child and does not have any functional nor semantic meaning on its own, [use it whenever you need a padded section within a card](https://getbootstrap.com/docs/5.3/components/card/#body).
- `panel-footer` class is replaced by `card-footer`.
- `panel-default` and `panel-primary` classes are replaced by a combination of `border-*` and `bg-*` applied to `card` and `card-header`.
- `<div class="panel panel-default">` is replaced by `<div class="card">` without additional classes.

=== "Bootstrap v3"

    ```html
    <div class="panel panel-default">
        <div class="panel-heading">
            <h3 class="panel-title">Panel Title</h3>
        </div>
        <div class="panel-body">
            Panel content goes here.
        </div>
        <div class="panel-footer">Panel Footer</div>
    </div>
    <div class="panel panel-primary">
        <div class="panel-heading">
            <h3 class="panel-title">Panel Title</h3>
        </div>
        <div class="panel-body">
            Panel content goes here.
        </div>
        <div class="panel-footer">Panel Footer</div>
    </div>
    ```

=== "Bootstrap v5"

    ```html
    <div class="card">
        <div class="card-header">
            <h5 class="card-title">Panel Title</h5>
        </div>
        <div class="card-body">
            Panel content goes here.
        </div>
        <div class="card-footer">Panel Footer</div>
    </div>
    <div class="card border-primary">
        <div class="card-header bg-primary text-white">
            <h5 class="card-title">Panel Title</h5>
        </div>
        <div class="card-body">
            Panel content goes here.
        </div>
        <div class="card-footer">Panel Footer</div>
    </div>
    ```

### Tabs

- `nav-item` class is now required for each `<li>`.
- `nav-link` class must be applied to clickable `<a>` and `<button`> elements.
- `active` class must be applied to the inner `nav-link` element (`<a>`, `<button>`) instead of `nav-item` (`<li>`).

=== "Bootstrap v3"

    ```html
    <ul class="nav nav-tabs">
        <li class="active" role="presentation">
            <a href="#home">Home</a>
        </li>
        <li role="presentation">
            <a href="#profile">Profile</a>
        </li>
        <li role="presentation">
            <a href="#messages">Messages</a>
        </li>
    </ul>
    ```

=== "Bootstrap v5"

    ```html
    <ul class="nav nav-tabs" role="tablist">
        <li class="nav-item" role="presentation">
            <a class="nav-link active" href="#home">Home</a>
        </li>
        <li class="nav-item" role="presentation">
            <a class="nav-link" href="#profile">Profile</a>
        </li>
        <li class="nav-item" role="presentation">
            <a class="nav-link" href="#messages">Messages</a>
        </li>
    </ul>
    ```
