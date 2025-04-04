# Nautobot V3 UI Migration Guide

With the release of Nautobot v3, the UI has undergone significant improvements to enhance usability, flexibility, and maintainability. This version introduces an upgrade from Bootstrap 3.4.1 to Bootstrap 5. This transition brings modern UI enhancements, improved accessibility, and better responsiveness. While these changes provide a more consistent and intuitive user experience, they also introduce necessary modifications that may impact existing custom UI components and templates.

The following is a detailed migration guide outlining the steps to help app authors update their app's UI for compatibility with the Bootstrap upgrade. Additional changes that are needed and might not be captured in this migration guide can be found in the Bootstrap V5 documentation.

## Breadcrumb Items

- Breadcrumb Item is changed from `<li>` to `<li class="breadcrumb-item">`
- Active breadcrumb item is changed from `<li class="active">Data</li>` to `<li class="breadcrumb-item active" aria-current="page">Data</li>`

Bootstrap 3:

```html
<ol class="breadcrumb">
  <li><a href="#">Home</a></li>
  <li><a href="#">Library</a></li>
  <li class="active"><a href="#">Data</a></li>
</ol>
```

Bootstrap 5:

```html
<ol class="breadcrumb">
    <li class="breadcrumb-item"><a href="#">Home</a></li>
    <li class="breadcrumb-item"><a href="#">Library</a></li>
    <li class="breadcrumb-item active" aria-current="page"><a href="#">Data</a></li>
</ol>
```

## Buttons

- `.btn-default` is replaced by `.btn-secondary`
- `.close` is replaced by `.btn-close`
- `.btn-xs` (extra small) is removed; use `.btn-sm` as the smallest size

Bootstrap 3:

```html
<button class="btn-default"></button>
<button class="close" data-dismiss="alert">×</button>
```

Bootstrap 5:

```html
<button class="btn-secondary"></button>
<button class="btn-close" data-bs-dismiss="alert"></button>
```

## Hide/Show Elements

- `.hidden` is replaced by `d-none`
- `.visible-*` is replaced by `d-block` or `d-inline`
- `.hidden-xs` is replaced by `d-block d-sm-none` (hide on extra small)
- `.visible-xs` is replaced by `d-none d-sm-block` (show on extra small)
- `hidden` is replaced by `visually-hidden` (visually hide elements but keep them accessible to assistive technologies e.g. screen readers)

## Label to Badge

- `.label` is replaced with `.badge`
- The contextual classes (e.g., `.label-primary`, `.label-success`) are now `.badge-primary`, `.badge-success`, etc

Bootstrap 3:

```html
<span class="label label-primary">Primary</span>
<span class="label label-success">Success</span>
<span class="label label-danger">Danger</span>
```

Bootstrap 5:

```html
<span class="badge bg-primary">Primary</span>
<span class="badge bg-success">Success</span>
<span class="badge bg-danger">Danger</span>
```

## Nav Tab Items and Nav Tab Links

- `.nav-item` is now required for each `<li>`
- `.nav-link` must be applied to `<a>` elements
- `.active` must be applied to the `.nav-link` instead of `<li>`

Bootstrap 3:

```html
<ul class="nav nav-tabs">
  <li class="active" role="presentation"><a href="#home">Home</a></li>
  <li role="presentation"><a href="#profile">Profile</a></li>
  <li role="presentation"><a href="#messages">Messages</a></li>
</ul>
```

Bootstrap 5:

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

## Pagination Items and Pagination Links

- `.page-item` needs to be applied to `<li>` elements
- `.page-link` needs to be applied to `<a>` elements
- `.active` is now applied to `<li>` instead of `<a>`
- `.disabled` should be applied to `<li>` instead of `<a>`
- replace `<i class="mdi mdi-chevron-double-left"></i>` with `<span aria-hidden="true">&laquo;</span>`
- replace `<i class="mdi mdi-chevron-double-right"></i>` with `<span aria-hidden="true">&raquo;</span>`

Bootstrap 3:

```html
<ul class="pagination">
  <li class="disabled"><a href="#previous_page"><i class="mdi mdi-chevron-double-left"></i></a></li>
  <li class="active"><a href="#">1</a></li>
  <li><a href="#">2</a></li>
  <li><a href="#">3</a></li>
  <li><a href="#"><i class="mdi mdi-chevron-double-left"></i></a></li>
</ul>
```

Bootstrap 5:

```html
<ul class="pagination">
    <li class="page-item disabled"><a class="page-link" href="#" aria-disabled="true"><span aria-hidden="true">&laquo;</span></a></li>
    <li class="page-item active" aria-current="page"><a class="page-link" href="#">1</a></li>
    <li class="page-item"><a class="page-link" href="#">2</a></li>
    <li class="page-item"><a class="page-link" href="#">3</a></li>
    <li class="page-item"><a class="page-link" href="#"><span aria-hidden="true">&raquo;</span></a></li>
</ul>
```

## Panel Components

- `.panel` is no longer available, use `.card` instead
- `.panel-heading` is replaced by `.card-header`
- `.panel-body` is replaced by `.card-body`
- `.panel-footer` is replaced by `.card-footer`
- `.panel-default`, `.panel-primary` is replaced by a combination of `.border-*` and `.bg-*` classes applied to `.card` and `.card-header`
- `<div class="panel panel-default">` is replaced by `<div class="card">` without additional classes

Bootstrap 3:

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

Bootstrap 5:

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

## Positioning and Layout

!!! note
    It is recommended that instead of using `.float-start` and `.float-end`, we should use the [grid system](https://getbootstrap.com/docs/5.0/layout/grid/) in Bootstrap 5 for a more structured approach to positioning elements and layout.

- `.pull-left` is now `.float-start`
- `.pull-right` is now `.float-end`
- `.center-block` is now `.mx-auto`
- Bootstrap 5 now has `position-relative`, `position-absolute`, and etc. to help you to position elements
- Bootstrap 3 grid system:
    - Uses 12-column grid system
    - Requires explicit breakpoint prefixes (`xs`, `sm`, `md`, `lg`)
    - Column widths are fixed per breakpoint
    - `offset` classes control positioning
- Bootstrap 5 grid system:
    - No more `xs` breakpoint
    - Uses `.col-*` auto-sizing if not specified (no need for exact column width)
    - Specifies `gutter` width via `.g-*` classes
    - `offset` classes are placed with `ms-auto`, `me-auto`, and `mx-auto`

Above is a short summary for the positioning and layout changes in Bootstrap 5, see more details in the Bootstrap 5 documentation about [columns](https://getbootstrap.com/docs/5.0/layout/columns/), [float](https://getbootstrap.com/docs/5.0/utilities/float/), and [position](https://getbootstrap.com/docs/5.0/utilities/position/).

## JavaScript Plugin Updates

- No more jQuery dependency; Bootstrap v5 javascript now use vanilla JavaScript
- Ensure that your custom scripts do not rely on jQuery-based Bootstrap 3 functions
- Data attributes renamed:
    - `data-toggle` is now `data-bs-toggle`
    - `data-dismiss` is now `data-bs-dismiss`
    - `data-target` is now `data-bs-target`
    - `data-title` is now `data-bs-title`

Bootstrap 3:

```html
<button data-toggle="modal" data-target="#myModal">Open Modal</button>
<button class="close" data-dismiss="alert">×</button>
```

Bootstrap 5:

```html
<button data-bs-toggle="modal" data-bs-target="#myModal">Open Modal</button>
<button class="btn-close" data-bs-dismiss="alert"></button>
```
