# Generic Views

!!! warning
    In new development, rather than implementing these individual class-based views, you will typically want to use [`NautobotUIViewSet`](../apps/api/views/nautobotuiviewset.md) (or its component mixin classes) as it enables similar functionality with less boilerplate code required.

* `ObjectView` - Retrieve a single object for display.
* `ObjectListView` - List a series of objects.
* `ObjectEditView` - Create or edit a single object.
* `ObjectDeleteView` - Delete a single object.
* `BulkCreateView` - Create new objects in bulk.
* `BulkDeleteView` - Delete objects in bulk.
* `BulkEditView` - Edit objects in bulk.

--- 2.2.0
    `BulkImportView` is deprecated as it's been replaced by a system Job; it will be removed from the code base in Nautobot 3.0 and should not be used in any new development in the interim.

Once you define a view by subclassing any of the above generic classes, you must register it in your `urls.py` as usual. There are a few things to be aware of here:

* Reverse URL naming needs to follow a template of `{modelname}_{method}` where the **model name** is lowercased model class name from `models.py` and **method** is the purpose of the view. E.g. `_list`, `_add`, `_edit`.
* The default rendering context for the `ObjectListView` includes some standard `action_buttons` for interacting with the listed model. By default this view defines `action_buttons = ("add", "import", "export")`. The `export` and `import` actions are handled automatically by `ObjectListView`, but the `add` action needs a corresponding view in order to work. In other words, if you implement an `ObjectListView` and do not override its `action_buttons`, you must also implement and register the corresponding `ObjectEditView`.

If you do not need `ObjectEditView` for your particular model, as an alternative you can simply update your `ObjectListView` subclass to overload the action buttons.  For example, `action_buttons = ("import", "export")` or if none are required `action_buttons = ()`.
