# Migration Guide: Embedded Actions

## Background: the shift to Embedded Actions

In 3.1 release, Nautobot has significantly improved the user experience of creating and updating objects by introducing embedded create and search actions. Historically, if a user was filling out a form and needed to select a related object that didn't exist yet (e.g., needing to create a new Manufacturer while adding a Device Type), they had to navigate away, create the object, and then return — often losing their progress.

To solve this, Nautobot 3.1 introduced:

- Embedded Search: Allowing users to perform advanced filtering and selection of related objects dynamically within a modal.
- Embedded Create: Permitting users to create new related objects on the fly via a modal without ever leaving their current page or losing their form context.

!!! info
    Embedded Actions were introduced only in standard object add/create/update/edit form views which inherit from generic Nautobot form and view or vieweset classes. Any custom form views or other non-CRUD forms (such as Jobs) were not affected in any way by this change.

## Overview of the new API

Nautobot 3.1 introduces support for rendering specific object creation templates directly within the embedded object creation modals.

Because these embedded forms are loaded dynamically into the DOM via AJAX after the initial page load, any JavaScript that traditionally relied on `$(document).ready()` or `DOMContentLoaded` event will not execute for the newly loaded modal content. Moreover, unscoped JavaScript code executed on page load may potentially leak into and unwillingly linger in the global `window` object, causing bugs. To resolve this and give developers a clean way to hook into the form lifecycle, we have introduced a new frontend API: `window.nb.form`.

This guide explains how Nautobot App developers should update their form-related JavaScript to remain fully compatible with both standard page loads and dynamic modals.

When a user opens a dynamic modal to create an object, the modal content is fetched and injected into the page. Because the document is already "ready", those initialization events do not re-fire for the dynamically injected content, leaving your custom form logic uninitialized and broken.

The new `window.nb.form` API provides a standardized lifecycle event that dispatches both on the initial page load and whenever a dynamic form is loaded into a modal.

## Migrating to `window.nb.form`

The `window.nb.form` object provides an interface to register your form initialization scripts so they run at the correct time and target the correct fields.

### 1. Loading `jquery.formset.js` script is no longer required when a template extends `generic/object_create.html`

While loading `jquery.formset.js` in this case won't break any of the existing behaviors, it is no longer required as it is now loaded by default on every page that extends `generic/object_create.html`.

### 2. Stop relying on `$(document).ready()` or `DOMContentLoaded` event

Any logic directly manipulating, styling, or reading form fields should be decoupled from the global page load event.

Before (deprecated):

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // ❌ Fails when this form is loaded dynamically in a modal later!
     document.querySelector('#custom_widget').addEventListener('click', function() {
        // Handle toggle logic...
    });
});
```

### 3. Use the new API lifecycle event

Wrap your initialization logic using the `nb-form:load:{{ obj_type }}` event API.

After:

```javascript
// ✅ Executes reliably on page load AND when the form renders asynchronoulsy inside a modal
document.addEventListener('nb-form:load:{{ obj_type }}', () => {
     document.querySelector('#custom_widget').addEventListener('click', () => {
        // Handle toggle logic...
    });
});
```

### 4. Dynamically resolve field IDs

When forms are loaded in a modal, Django may apply prefixes to the form fields to prevent ID collisions with the background page. Because of this, hardcoding IDs like `$('#id_status')` is no longer safe.

You are encouraged to use `window.nb.form.getFieldAutoId(autoId, fieldName, querySelector)` to get the dynamically generated, context-aware ID for your field.

- **`formAutoId`**: The Django form's auto ID format string, usually passed from the template via `'{{ form.auto_id }}'`.
- **`name`**: The name of your target field (e.g., `'my_custom_widget'`).
- **`querySelector`**: An optional boolean, `true` by default. If set to `false`, the function will not automatically prefix the returned string with a `#`, making it a plain ID string rather than an immediately usable CSS selector in jQuery or `document.querySelector`.

❌ Anti-pattern:

```javascript
document.addEventListener('nb-form:load:{{ obj_type }}', () => {
  // ❌ Hardcoded IDs might select the background page's field instead of the modal's!
  document.querySelector('#id_field_name').doSomething();
});
```

✅ Best practice:

```javascript
document.addEventListener('nb-form:load:{{ obj_type }}', () => {
  // ✅ Resolves the correct selector for the current context (page load vs. modal)
  const fieldSelector = window.nb.form.getFieldAutoId('{{ form.auto_id }}', 'field_name');
  // Use the resolved selector to safely query the DOM
  document.querySelector(fieldSelector).doSomething();
});
```

!!! tip
    In case your script makes reference to certain fields multiple times, you may also consider a helper function, like `getField` below:

    ```javascript
    document.addEventListener('nb-form:load:{{ obj_type }}', () => {
        const getField = (name) => document.querySelector(window.nb.form.getFieldAutoId('{{ form.auto_id }}', name));
        getField('field_name').doSomething();
        getField('other_field_name').doSomethingElse();
    });
    ```

### 5. Let `jsify_form` handle Select2 initialization for standard fields

Whenever a form is loaded — whether on the initial page load or dynamically inside an embedded action modal — Nautobot automatically calls a core function named `jsify_form`. This function is responsible for initializing standard Nautobot UI components, which natively includes applying Select2 to certain dropdowns.

You should remove manual `.select2()` calls on standard Nautobot fields to prevent conflicts or double-initialization bugs.

!!! note
    If your app introduces specific, highly customized fields that `jsify_form` does not process by default, you may still need to manually call `.select2()` on those specific custom fields inside your `nb-form:load:{{ obj_type }}` event listener.

## Summary checklist for App Developers

- Read up on the transition to embedded search and create forms to understand the new UX paradigm.
- Identify all JavaScript content in your app that interacts with add/create/update/edit forms.
- Remove `jquery.formset.js` script loads when templates extend `generic/object_create.html`.
- Remove `$(document).ready()` or `document.addEventListener('DOMContentLoaded', ...)` wrappers around form manipulation logic.
- Wrap the logic in the new `nb-form:load:{{ obj_type }}` event listener.
- Replace hardcoded field ID selectors (like `$('#id_field_name')` or `document.querySelector('#id_field_name')`) with dynamically resolved selectors using `window.nb.form.getFieldAutoId('{{ form.auto_id }}', 'field_name')`.
- Remove manual `.select2()` initialization calls for standard fields, relying on the core `jsify_form` function being called by default instead. Keep it only for specific custom fields if strictly necessary.
