# Upgrading from Bootstrap v3.4.1 to v5.x

## Overview
Since its inception, Nautobot user interface was built on top of [Bootstrap v3.4.1](https://getbootstrap.com/docs/3.4/). Along the way it benefited from several lifting efforts but besides that it was still being based on the same foundations.

In Nautobot v3.x we are slightly shaking these foundations and delivering a major UI/UX redesign with a long anticipated upgrade to [Boostrap 5.x](https://getbootstrap.com/docs/5.3/). Although we did our best to make the migration as smooth as possible for app developers, we were not able to avoid some of the **breaking changes**. Keep reading this guide to see how to upgrade.

## Dependency management
In case you were not using any plugins and had not maintained your own custom CSS or JS code dependent on Bootstrap v3.4.1, you don't need to do anything related to dependency management.

Otherwise, you will need to individually review whether the packages and/or modules you are using, are still compatible with Bootstrap 5.x and in case they are not, update them accordingly.

## HTML structures and CSS classes
The best place to see what's changed in the core library is to review [Bootstrap 5.x migration guide](https://getbootstrap.com/docs/5.3/migration/). That said, we are aware that it is a lot of information to digest, not delivered in the most approachable form, moreover some of it irrelevant for Nautobot UI. To make it easier for you, we created our own Nautobot UI Bootstrap v3.4.1 to v5.x migration guide below, highlighting the most important changes accompanied by examples.

!!! note
    We are not covering all the UI/UX changes done to Bootstrap and Nautobot components here. Instead, we narrow down the scope of this guide to only the technical part focused on HTML element structures and attributes, and CSS class names.

### Helper classes / Helpers and Utilities
One major difference between Bootstrap v3.4.1 and v5.x is that [Helper classes](https://getbootstrap.com/docs/3.4/css/#helper-classes) no longer exist. Instead, they were replaced with [Helpers](https://getbootstrap.com/docs/5.3/helpers/) and [Utilities](https://getbootstrap.com/docs/5.3/utilities/) which offer far more comprehensive set of CSS classes for styling elements on the page without having to write custom CSS. Below is a table with helpers and utilities that correspond to former helper classes for a quick search-and-replace reference. Items not listed here did not change and can be left as-is.

| Helper class        | Utility                                                                                                                    |
|---------------------|----------------------------------------------------------------------------------------------------------------------------|
| `text-muted`        | `text-secondary`                                                                                                           |
| `close`             | `btn-close` *(technically speaking, close button is a component now, not a helper or utility)*                             |
| `caret`             | *removed, use an icon from icon library instead*                                                                           |
| `pull-left`         | `float-start`                                                                                                              |
| `pull-right`        | `float-end`                                                                                                                |
| `center-block`      | `d-block mx-auto` *(you can also consider using flexbox for content centering)*                                            |
| `show`              | `d-block`                                                                                                                  |
| `hidden`            | `d-none`                                                                                                                   |
| `sr-only`           | `visually-hidden `                                                                                                         |
| `sr-only-focusable` | `visually-hidden-focusable` **(must not be used in combination with the `visually-hidden` class)**                         |
| `text-hide`         | *removed, as per Bootstrap v5.0 documentation: "it’s an antiquated method for hiding text that shouldn’t be used anymore"* |

It is highly encouraged to at least briefly familiarize with Bootstrap v5.x documentation on Helpers and Utilities and the array of possibilities they provide, because in many cases they can relieve developers from the burden of writing custom CSS code. At the same time, mind that not all default Bootstrap maps can be treated as source of truth, there are several Nautobot overwrites which, most notably, include [spacing](#spacing-ie-margins-and-paddings).

#### Spacing (i.e. margins and paddings)
To avoid unnecessary mapping of abstract to pixel values, Nautobot defines spacing sizes in straightforward concrete pixel values. On one hand it requires developers to think about pixels rather than semantic meaning of a particular spacing but on the other, there really are no spacing guidelines for Bootstrap nor Nautobot, so these abstract names would be arbitrary and made up anyway. Available sizes are:
```
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

### Breadcrumbs
TODO

### Buttons
The most notable difference between Bootstrap v3.4.1 and Bootstrap v5.x is that `btn-default` has been renamed to `btn-secondary`. Nautobot will keep supporting `btn-default` class, nevertheless we recommend replacing old `btn-default` class name with `btn-secondary`. Other than that, there were no major changes to buttons and no special migration effort should be required for standard button use cases.

### Dropdowns
Complete Bootstrap 5.x dropdowns documentation can be found at: https://getbootstrap.com/docs/5.3/components/dropdowns/.

In Bootstrap v3.4.1, dropdowns were kind of second class citizens, missing out much on configurability mainly due to just a handful of dedicated classes. Bootstrap v5.x amends that and to some extent redefines dropdown HTML structure and attributes, and CSS classes.

Differences include:
1. Dropdown wrapper component is no longer of class `btn-group` but `dropdown` instead.
2. Dropdown toggle button `data-toggle` attribute has been renamed to `data-bs-toggle`, and `aria-haspopup` attribute is no longer recommended.
3. As already mentioned in [Helper classes / Helpers and Utilities](#helper-classes--helpers-and-utilities) section above, if dropdown toggle button used `caret` element, it must be replaced by an icon from available icon library.
4. Likewise, if dropdown toggle button used a descriptive text of class `sr-only`, it should be changed to `visually-hidden`.
5. List items do not expect any particular CSS class but elements within them do. This is especially relevant for separators (dividers).
6. Clickable items (mainly `button` and `a` elements) should be of `dropdown-item` class.
7. Separators (dividers) should be `hr` elements with `dropdown-divider` class.

Let's take a look at this example from [Bootstrap v3.4.1 Single button dropdowns](https://getbootstrap.com/docs/3.4/components/#btn-dropdowns-single) documentation and how to migrate it over to Bootstrap v5.x:

Bootstrap v3.4.1:
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

Bootstrap v5.x:
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

### Panels / Cards
TODO

### Tabs
TODO
