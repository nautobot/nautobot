# Extending Models

Below is a list of tasks to consider when adding a new field to a core model.

## Generate and run database migrations

Django migrations are used to express changes to the database schema. In most cases, Django can generate these automatically, however very complex changes may require manual intervention. Always remember to specify a short but descriptive name when generating a new migration.

!!! warning
    Assert that you have installed Nautobot in your development environment using `poetry install` so that changes you make to migrations will apply to the source tree!

```no-highlight
nautobot-server makemigrations <app> -n <name>
nautobot-server migrate
```

Where possible, try to merge related changes into a single migration. For example, if three new fields are being added to different models within an app, these can be expressed in the same migration. You can merge a new migration with an existing one by combining their `operations` lists.

!!! note
    Migrations can only be merged within a release. Once a new release has been published, its migrations cannot be altered (other than for the purpose of correcting a bug).

### Advanced Database Migration Topics

Before creating any custom database migration files it's a good idea to read Django's excellent [documentation on migrations](https://docs.djangoproject.com/en/stable/topics/migrations/). Here are some common pitfalls to avoid when writing migrations:

* **Data Migrations**: If you need to write a migration that manipulates data using the `RunPython` operation, make sure to put this in a separate migration file from any schema changes (`CreateModel`, `AddField`, etc.).

* **Dependencies**: It's important to declare the correct dependencies for your migrations. Django does a good job of determining the dependencies for automatically generated schema migrations, but if you're writing a custom migration you will need to specify dependencies manually. A good rule of thumb for data migrations is to always include a dependency for any app used in an `apps.get_model` call. For example, if your migration includes a line containing `apps.get_model("dcim", "Device")`, you should include a dependency on the `dcim` app.

## Add validation logic to `clean()`

If the new field introduces additional validation requirements (beyond what's included with the field itself), implement them in the model's `clean()` method. Remember to call the model's original method using `super()` before or after your custom validation as appropriate:

```python
class Foo(models.Model):

    def clean(self):

        super().clean()

        # Custom validation goes here
        if self.bar is None:
            raise ValidationError()
```

## Update relevant querysets

If you're adding a relational field (e.g. `ForeignKey`) and intend to include the data when retrieving a list of objects, be sure to include the field using `select_related()` (for `ForeignKey` forward lookups) and/or `prefetch_related()` (for `ForeignKey` reverse lookups and `ManyToManyField` lookups) as appropriate. This will optimize the view and avoid extraneous database queries.

## Update API serializer

Extend the model's API serializer in `nautobot.<app>.api.serializers` to include the new field, if necessary.

+++ 2.0.0
Most model serializers now use `fields = [__all__]`, in which case you do not have to explicitly include the new field in the model's API serializer. The serializer will automatically pick up the field and render it according to Nautobot standards. If the default rendering does not meet your API needs, you can explicitly declare the field on the serializer.

## Add field to forms

Extend any forms to include the new field as appropriate. Common forms include:

* **Create/edit** - Manipulating a single object
* **Bulk edit** - Performing a change on many objects at once
* **Filter** - Displays the options available for filtering a list of objects (both UI and API)

## Extend object filter set

If the new field should be filterable, add it to the `FilterSet` for the model. If the field should be searchable, remember to reference it in the FilterSet's `SearchFilter` definition.

All filtersets should inherit from `BaseFilterSet` or `NautobotFilterSet` as appropriate to the scope of the model's functionality.

## Add column to object table

If the new field will be included in the object list view, add a column to the model's table. For simple fields, adding the field name to `Meta.fields` will be sufficient. More complex fields may require declaring a custom column.

!!! tip
    In the vast majority of cases, a table's `Meta.fields` should have `"pk"` as the first entry and (if present as a column) `"actions"` as the last entry, so that these two columns appear correctly at the far left and far right of the table. When adding new entries to `Meta.fields` please be sure to follow this pattern.

## Update the UI templates

Edit the object's view template to display the new field. There may also be a custom add/edit form template that needs to be updated.

## Validate the new field in GraphQL

If the model is already part of the GraphQL schema, the new field will be included automatically. Validate that the new field is rendering properly in GraphQL. If the field is not compatible with GraphQL or shouldn't be included in GraphQL it's possible to exclude a specific field in the GraphQL Type Object associated with this specific model. You can refer to the [graphene-django documentation](https://docs.graphene-python.org/projects/django/en/latest/queries/#specifying-which-fields-to-include) for additional information.

Note that if you're using the `convert_django_field` registry to override the default GraphQL representation for any field type, this override must be registered within the relevant app's `ready()` function, rather than at module import time.

## Create/extend test cases

Create or extend the relevant test cases to verify that the new field and any accompanying validation logic perform as expected. This is especially important for relational fields. Nautobot incorporates various test suites, including:

* API serializer/view tests (should be based on `nautobot.core.testing.api.APIViewTestCases`)
* Filter tests (should be based on `nautobot.core.testing.filters.FilterTestCases`)
* Form tests (should be based on `nautobot.core.testing.forms.FormTestCases`)
* Model tests (should be based on `nautobot.core.testing.models.ModelTestCases`)
* View tests (should be based on `nautobot.core.testing.views.ViewTestCases`)

Be diligent to ensure all of the relevant test suites are adapted or extended as necessary to test any new functionality.

## Update the model's documentation

Each model has a dedicated page in the documentation, typically either at `docs/user-guide/core-data-model/<app>/<model>.md`, or in the case of the `extras` app, at `docs/user-guide/platform-functionality/<model>.md`. Some models are exceptions to this pattern; if so, they should declare the path as a `documentation_static_path` attribute on the model class definition.

Update this file to include any relevant information about the new field. Note that this documentation page should automatically be accessible through the web UI via a "question mark" icon on the corresponding model create/edit page.
