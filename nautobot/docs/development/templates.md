# Templates for Plugins

Nautobot comes with a variety of plugins that allow for a lot of flexibility
while keeping the page style consistent with the rest of the application.
This document presents these templates and their features.

You can use it for your templates by calling `{% extends '<template_name>' %}`
at the top of your template file.

## Object Detail

The most customizable template available to plugin authors is
`generic/object_detail.html`.

The following blocks are available to you:

- `header`: overloading this block allows for changing the entire top row of
  the page, including the title, breadcrumbs, search field, and tabs.
    - `breadcrumbs`: overloading this block allows for changing the entire
      breadcrumbs block.
        - `extra_breadcrumbs`: this enables extending the breadcrumbs block
          just before the model without having to redefine the entire block.
    - `buttons`: overloading this block allows redefining the entire button
      section on the right of the page.
        - `extra_buttons`: this block enables extending the buttons block
          without losing the predefined buttons. Custom buttons will appear
          between the plugin buttons and clone/edit/delete actions.
    - `masthead`: is the block that contains the title. Overloading it enables
      to change anything about the title block.
    - `title`: is the block contained by `masthead` and wrapped in a heading
      block. Overloading it makes it possible to change the heading text as
      well as the page title shown in the browser.
    - `nav_tabs`: are the navigation tabs. If overloaded, custom tabs can be
      rendered instead of the default.
        - `extra_nav_tabs`: this block allows to add new tabs without having to
          override the default ones.
- `content`: is the entire content of the page below the `header`.
    - `content_left_page`: is a half-width column on the left. Multiple panels
      can be rendered in a single block.
    - `content_right_page`: is a half-width column on the right.
    - `content_full_width_page`: is a full-width column.

## Object List

The base view for listing objects is `generic/object_list.html`.

In it, the following blocks may be implemented:

- `buttons`: may provide a set of buttons at the top right of the page, to the
  left of the table configuration button.
- `sidebar`: may implement a sidebar below the search form on the right.
- `bulk_buttons`: may be a set of buttons at the bottom of the table, to the
  left of potential bulk edit or delete buttons.

## Object Edit

The base view for object addition or change is `generic/object_edit.html`, with
the following blocks:

- `form`: is the block in which the form gets rendered. This can be overriden
  to provide a custom UI or UX for form views beyond what `render_form`
  provides.

## Object Import

The base view for object import is `generic/object_import.html`.

The blocks that views may override are:

- `tabs`: may provide tabs at the top of the page. The default import view is
  not tabbed.

## Object Deletion

The base view for object deletion is `generic/object_delete.html`.

It provides the following custom blocks:

- `message`: is the overridable confirmation message for deletion.
    - `message_extra`: provides a way to add to the default message without
      overriding it.

## Bulk Edit

The base view for bulk object change is `generic/object_bulk_edit.html`. It
does not provide any blocks for customizing the user experience.

## Bulk Import

The base view for bulk object import is `generic/object_bulk_import.html`.

The blocks that views may override are:

- `tabs`: may provide tabs at the top of the page. The default import view is
  not tabbed.

## Bulk Deletion

The base view for bulk object deletion is `generic/object_bulk_delete.html`.

It provides the following custom blocks:

- `message_extra`: provides a way to add to the default message.

**Note**: contrary to the deletion of a single object, this view does *not*
provide a way to completely override the deletion message.

## Bulk Renaming

The base view for renaming object in bulk is `generic/object_bulk_rename.html`.
It does not provide any blocks for customizing the user experience.
