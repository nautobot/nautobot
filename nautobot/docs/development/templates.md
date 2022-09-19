# Page Templates

Nautobot comes with a variety of page templates that allow for a lot of flexibility
while keeping the page style consistent with the rest of the application.
This document presents these templates and their features.

You can use these templates as the basis for your templates by calling `{% extends '<template_name>' %}`
at the top of your template file.

## Object Detail

+++ 1.2.0

The most customizable template is `generic/object_detail.html`, as object detail views have a wide range of specific requirements to be accommodated. It provides the following blocks:

* `header`: overloading this block allows for changing the entire top row of
  the page, including the title, breadcrumbs, search field, and tabs.
    * `breadcrumbs`: overloading this block allows for changing the entire
      breadcrumbs block.
        * `extra_breadcrumbs`: this enables extending the breadcrumbs block
          just before the model without having to redefine the entire block.
    * `buttons`: overloading this block allows redefining the entire button
      section on the right of the page.
        * `extra_buttons`: this block enables extending the buttons block
          without losing the predefined buttons. Custom buttons will appear
          between the plugin buttons and clone/edit/delete actions.
    * `masthead`: is the block that contains the title. Overloading it enables
      to change anything about the title block.
    * `title`: is the block contained by `masthead` and wrapped in a heading
      block. Overloading it makes it possible to change the heading text as
      well as the page title shown in the browser.
    * `nav_tabs`: are the navigation tabs. If overloaded, custom tabs can be
      rendered instead of the default.
        * `extra_nav_tabs`: this block allows to add new tabs without having to
          override the default ones.
* `content`: is the entire content of the page below the `header`.
    * `content_left_page`: is a half-width column on the left. Multiple panels
      can be rendered in a single block.
    * `content_right_page`: is a half-width column on the right.
    * `content_full_width_page`: is a full-width column.

## Object List

The base template for listing objects is `generic/object_list.html`, with the following blocks:

* `buttons`: may provide a set of buttons at the top right of the page, to the
  left of the table configuration button.
* `sidebar`: may implement a sidebar below the search form on the right.
* `bulk_buttons`: may be a set of buttons at the bottom of the table, to the
  left of potential bulk edit or delete buttons.

## Object Edit

The base template for object addition or change is `generic/object_edit.html`,
with the following blocks:

* `form`: is the block in which the form gets rendered. This can be overridden
  to provide a custom UI or UX for form views beyond what `render_form`
  provides.

## Object Import

The base template for object import is `generic/object_import.html`, with the following blocks:

* `tabs`: may provide tabs at the top of the page. The default import view is
  not tabbed.

## Object Deletion

The base template for object deletion is `generic/object_delete.html`, with the following blocks:

* `message`: is the confirmation message for deletion, which can be overridden.
    * `message_extra`: provides a way to add to the default message without
      overriding it.

## Bulk Edit

The base template for bulk object change is `generic/object_bulk_edit.html`. It
does not provide any blocks for customizing the user experience.

## Bulk Import

The base template for bulk object import is `generic/object_bulk_import.html`, with the following blocks:

* `tabs`: may provide tabs at the top of the page. The default import view is
  not tabbed.

## Bulk Deletion

The base template for bulk object deletion is `generic/object_bulk_delete.html`, with the following blocks:

* `message_extra`: provides a way to add to the default message.

**Note**: contrary to the deletion of a single object, this template does *not*
provide a way to completely override the deletion message.

## Bulk Renaming

The base template for renaming objects in bulk is `generic/object_bulk_rename.html`.
It does not provide any blocks for customizing the user experience.
