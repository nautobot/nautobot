# Generic Views

* `ObjectView` - Retrieve a single object for display.
* `ObjectListView` - List a series of objects.
* `ObjectEditView` - Create or edit a single object.
* `ObjectDeleteView` - Delete a single object.
* `BulkCreateView` - Create new objects in bulk.
* `BulkDeleteView` - Delete objects in bulk.
* `BulkEditView` - Edit objects in bulk.
* `BulkImportView` - Import objects in bulk from CSV.

Once you define a view by subclassing any of the above generic classes, you must register it in your `urls.py` as usual. There are a few things to be aware of here:

* Reverse URL naming needs to follow a template of `{modelname}_{method}` where the **model name** is lowercased model class name from `models.py` and **method** is the purpose of the view. E.g. `_list`, `_add`, `_edit`.
* The default rendering context for the `ObjectListView` includes some standard `action_buttons` for interacting with the listed model. By default this view defines `action_buttons = ("add", "import", "export")`. The `export` action is handled automatically by `ObjectListView`, but the `add` and `import` actions need corresponding views in order to work. In other words, if you implement an `ObjectListView` and do not override its `action_buttons`, you must also implement and register the corresponding `ObjectEditView` and `BulkImportView` subclasses as well.

!!! warning
    If you're missing any of the aforementioned URLs/Views, when accessing your list view it will result in a error `Reverse for 'None' not found. 'None' is not a valid view function or pattern name.`

If you do not need `ObjectEditView` and/or `BulkImportView` for your particular model, as an alternative you can simply update your `ObjectListView` subclass to overload the action buttons.  For example, `action_buttons = ("add",)` or if none are required `action_buttons = ()`.

To demonstrate these concepts we can look at the `example_plugin` included in the Nautobot repository.

The example plugin has a simple model called `ExampleModel`:

```python
class ExampleModel(OrganizationalModel):
    name = models.CharField(max_length=20, help_text="The name of this Example.")
    number = models.IntegerField(default=100, help_text="The number of this Example.")

    csv_headers = ["name", "number"]

    class Meta:
        ordering = ["name"]
```

The list view for this model subclasses `generic.ObjectListView` and does **not** overload the `action_buttons`:

```python
class ExampleModelListView(generic.ObjectListView):
    """List `ExampleModel` objects."""

    queryset = ExampleModel.objects.all()
    filterset = filters.ExampleModelFilterSet
    filterset_form = forms.ExampleModelFilterForm
    table = tables.ExampleModelTable
```

!!! info
    Since `action_buttons` was not overloaded, `action_buttons = ("add", "import", "export")` is inherited.

In order for this to work properly we expect to see `urls.py` have each of the required URLs/Views implemented with the template mentioned above.

```python
urlpatterns = [
    ...
    path("models/", views.ExampleModelListView.as_view(),name="examplemodel_list"),
    path("models/add/", views.ExampleModelEditView.as_view(), name="examplemodel_add"),
    ...
    path(
        "models/import/",
        views.ExampleModelBulkImportView.as_view(),
        name="examplemodel_import",
    ),
    ...
]
```
