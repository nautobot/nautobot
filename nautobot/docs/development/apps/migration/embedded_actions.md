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

Previously, when you wrote JavaScript to enhance an app's form (e.g., toggling field visibility based on user input, or setting up dynamic formsets), you likely wrapped your logic in a global document-ready block.

When a user opens a dynamic modal to create an object, the modal content is fetched and injected into the page. Because the document is already "ready", those initialization events do not re-fire for the dynamically injected content, leaving your custom form logic uninitialized and broken.

The new `window.nb.form` API provides a standardized lifecycle event that dispatches both on the initial page load and whenever a dynamic form is loaded into a modal.

## Controlling Embedded Actions on forms

While the embedded search and create modals significantly improve the default user experience, there are times when they might not be appropriate for your app's specific workflow. For instance, you might have a highly customized field where a generic creation modal doesn't capture the necessary context, or a field where you explicitly want to prevent users from creating new related objects on the fly.

To give developers granular control over the UI, Nautobot forms and fields support several attributes to explicitly enable or disable these embedded action buttons on a per-field basis. You can define these attributes directly on your form class:

### 1. Form meta class attributes

You can define inclusion and exclusion lists on your form meta class to control which fields get embedded action buttons:

- **`embedded_create`**: An inclusion list of field names that should display the embedded object create button. If defined, only the fields in this list will get the button.
- **`exclude_embedded_create`**: An exclusion list of field names that should not display the embedded object create button. All other compatible fields will display it by default.
- **`embedded_search`**: An inclusion list of field names that should display the embedded object search button.
- **`exclude_embedded_search`**: An exclusion list of field names that should not display the embedded object search button.

!!! note
    Inclusion and exclusion lists of the same category (e.g. `embedded_create` and `exclude_embedded_create`) are mutually exclusive and cannot be defined both at once on the same class.

```python
from nautobot.extras.forms import NautobotModelForm

from my_app.models import MyModel


class MyModelForm(NautobotModelForm):
    class Meta:
        model = MyModel
        fields = "__all__"
        # ℹ️ Allow embedded search ONLY for "device"
        embedded_search = ["device"]
```

### 2. Field-Level constructor arguments

Alternatively, if you are explicitly declaring a `DynamicModelChoiceField` or `DynamicModelMultipleChoiceField`, the constructor supports `embedded_create` and `embedded_search` boolean keyword arguments.

```python
from nautobot.dcim.models import Device
from nautobot.extras.forms import NautobotModelForm

from my_app.models import MyModel


class MyModelForm(NautobotModelForm):
    # ℹ️ Disable the embedded create button ONLY for "device"
    device = DynamicModelChoiceField(queryset=Device.objects.all(), embedded_create=False)

    class Meta:
        model = MyModel
        fields = "__all__"
```

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

You are encouraged to use `window.nb.form.getFieldAutoId(formAutoId, name, querySelector)` to get the dynamically generated, context-aware ID for your field.

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

### 6. Prevent variables from leaking into the global scope

Because forms can now be loaded multiple times within the same browser session (for example, opening and closing the embedded modal repeatedly), it is crucial to keep your variables, constants, and functions tightly scoped.

If you declare variables in the global scope (outside of your `nb-form:load:{{ obj_type }}` event handler or [IIFE](https://developer.mozilla.org/en-US/docs/Glossary/IIFE)), they will be attached to the global scope (either the main block or `window` object, depending on used declaration keyword or lack thereof). This means subsequent modal opens will attempt to overwrite them, potentially causing exceptions, state bleed, race conditions, or bugs where interacting with a new modal inadvertently affects the background page.

❌ Anti-pattern:

```javascript
// ❌ Leaks into the global scope! Will throw syntax errors if the modal is opened multiple times.
const fieldSelector = window.nb.form.getFieldAutoId('{{ form.auto_id }}', 'field_name');

document.addEventListener('nb-form:load:{{ obj_type }}', () => {
    document.querySelector(fieldSelector).addEventListener('input', () => {
        // Logic...
    });
});
```

✅ Best Practice:

```javascript
document.addEventListener('nb-form:load:{{ obj_type }}', () => {
    // ✅ Safely scoped to the specific execution of this form load instance
    const fieldSelector = window.nb.form.getFieldAutoId('{{ form.auto_id }}', 'field_name');

    document.querySelector(fieldSelector).addEventListener('input', () => {
        // Logic...
    });
});
```

## Summary checklist for App Developers

- Read up on the transition to embedded search and create forms to understand the new UX paradigm.
- Determine if you need to opt specific fields out of embedded actions using proper form- or field-level kwargs.
- Identify all JavaScript content in your app that interacts with add/create/update/edit forms.
- Remove `jquery.formset.js` script loads when templates extend `generic/object_create.html`.
- Remove `$(document).ready()` or `document.addEventListener('DOMContentLoaded', ...)` wrappers around form manipulation logic.
- Wrap the logic in the new `nb-form:load:{{ obj_type }}` event listener.
- Replace hardcoded field ID selectors (like `$('#id_field_name')` or `document.querySelector('#id_field_name')`) with dynamically resolved selectors using `window.nb.form.getFieldAutoId('{{ form.auto_id }}', 'field_name')`.
- Remove manual `.select2()` initialization calls for standard fields, relying on the core `jsify_form` function being called by default instead. Keep it only for specific custom fields if strictly necessary.
- Ensure all variables, constants, and helper functions are properly encapsulated to avoid their leakage into the global scope.
