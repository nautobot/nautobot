# Table Sticky Headers

+++ 3.3.0

Object list views keep their table column headers visible at the top of the browser viewport as you scroll down the page.

Table headers are sticky on list views only. Tables elsewhere, such as those on object detail pages and in search results, scroll with the page as before.

Choosing which columns a list view shows is covered in [Configurable Table Columns](configurablecolumns.md).

## Browser Support

Table sticky headers rely on a CSS feature that is currently available only in Chromium-based browsers, such as Chrome and Edge. Firefox and Safari do not support it yet.

In browsers not supporting table sticky headers, list views behave exactly as they did before: the headers scroll with the table.
