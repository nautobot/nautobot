# Model Development Checklist

A general best-practices checklist to follow when adding a net-new data model in Nautobot or adding new fields to an existing model.

## Bootstrapping a new Model

- ▢ Implement model in `nautobot.<app>.models` module
    - ▢ Use appropriate base class (`PrimaryModel` or `BaseModel`) and mixin(s)
    - ▢ Use appropriate `@extras_features` decorator values
    - ▢ Define appropriate uniqueness constraint(s)
    - ▢ Define appropriate `__str__()` logic
    - ▢ _optional_ Define appropriate additional `clean()` logic
        - ▢ Be sure to always call `super().clean()` as well!
    - ▢ _optional_ Define appropriate `verbose_name`/`verbose_name_plural` if defaults aren't optimal
- ▢ Generate database schema migration(s) with `invoke makemigrations <app> -n <migration_name>`
- ▢ Implement API `<Model>Serializer` class in `nautobot.<app>.api.serializers` module
    - ▢ Use appropriate base class and mixin(s)
- ▢ Implement `<Model>FilterSet` class in `nautobot.<app>.filters` module
    - ▢ Use appropriate base class (`NautobotFilterSet` or `BaseFilterSet`) and mixin(s)
- ▢ Implement API `<Model>ViewSet` class in `nautobot.<app>.api.views` module
    - ▢ Use appropriate base class and mixin(s)
    - ▢ Use appropriate `select_related`/`prefetch_related` for performance
- ▢ Add API viewset to `nautobot.<app>.api.urls` module
- ▢ Implement UI `<Model>Table` class in `nautobot.<app>.tables` module
    - ▢ Use appropriate base class and mixin(s)
    - ▢ In the vast majority of cases, a table's `Meta.fields` should have `"pk"` as the first entry and (if present as a column) `"actions"` as the last entry, so that these two columns appear correctly at the far left and far right of the table.
- ▢ Implement `<Model>Form` class in `nautobot.<app>.forms` module
    - ▢ Use appropriate base class and mixin(s)
- ▢ Implement `<Model>FilterForm` class in `nautobot.<app>.forms` module
    - ▢ Use appropriate base class and mixin(s)
- ▢ Implement `<Model>BulkEditForm` class in `nautobot.<app>.forms` module
    - ▢ Use appropriate base class and mixin(s)
- ▢ Implement `nautobot/<app>/templates/<app>/<model>.html` detail template
- ▢ Implement `NautobotUIViewSet` subclass in `nautobot.<app>.views` module
    - ▢ Use appropriate base class and mixin(s)
    - ▢ Use appropriate `select_related`/`prefetch_related` for performance
- ▢ Add UI viewset to `nautobot.<app>.urls` module
- ▢ Add menu item in `nautobot.<app>.navigation` module

### Additional Functionality to Consider

- ▢ _optional_ Add model link and counter to home page panel in `nautobot.<app>.homepage` module
- ▢ _optional_ Add model to `nautobot.<app>.apps.<App>Config.searchable_models` to include it in global search
- ▢ _optional_ Expose any new relevant APIs in `nautobot.apps` namespace for App consumption
- ▢ _optional_ Enhance `ConfigContext` to be assignable by new Device-related model
    - ▢ Update ConfigContextQuerySet, ConfigContextFilterSet, ConfigContext forms, edit and detail views and HTML templates
- ▢ _optional_ Add [data migration(s)](https://docs.djangoproject.com/en/stable/topics/migrations/) to populate default records, migrate data from existing models, etc.
    - ▢ Remember: data migrations must not share a file with schema migrations or vice versa!
    - ▢ Specify appropriate migration dependencies (for example, against another app that you're using models from)

### Test Coverage

- ▢ Implement `<Model>Factory` class in `nautobot.<app>.factory` module
    - ▢ Add `<Model>Factory` invocation to `nautobot-server generate_test_data` command
- ▢ Implement `<Model>TestCase` class in `nautobot.<app>.tests.test_api` module
    - ▢ Use appropriate `APITestCases` base class and mixin(s)
- ▢ Implement `<Model>TestCase` class in `nautobot.<app>.tests.test_filters` module
    - ▢ Use appropriate `FilterTestCases` base class and mixin(s)
- ▢ _optional_ Implement `<Model>TestCase` class in `nautobot.<app>.tests.test_forms` module
    - ▢ Use appropriate `FormTestCases` base class and mixin(s)
- ▢ Implement `<Model>TestCase` class in `nautobot.<app>.tests.test_models` module
    - ▢ Use appropriate `ModelTestCases` base class and mixin(s)
- ▢ Implement `<Model>TestCase` class in `nautobot.<app>.tests.test_views` module
    - ▢ Use appropriate base class and mixin(s)

### Documentation

- ▢ Write `nautobot/docs/user-guide/core-data-model/<app>/<model>.md` user documentation
    - ▢ Add document to `mkdocs.yml`
    - ▢ Add redirect from `models/<app>/<model>.md` in `mkdocs.yml` (this is needed so that the "question mark" button on the model's create/edit page will resolve correctly)
- ▢ Write an overview of the new model in the release-note `Release Overview` section

## Adding any new Field to a Model

- ▢ Generate schema migration
    - ▢ Updating an existing migration is preferred if the model/migration hasn't yet shipped in a release. Once a new release has been published, its migrations **may not** be altered (other than for the purpose of correcting a bug).
- ▢ Add field to `<Model>Factory`
- ▢ Add field to `<Model>Form.fields`
- ▢ Add field to `<Model>BulkEditForm.fields`
- ▢ Add field filter(s) to `<Model>FilterSet`
    - ▢ _optional_ Add field to `<Model>FilterSet` `q` filter
- ▢ Add field to `<Model>FilterForm.fields`
- ▢ Add field column to `<Model>Table.fields`
    - ▢ Keep `"pk"` as the first column and `"actions"` (if present) as the last column
    - ▢ _optional_ Add field column to `<Model>Table.default_columns` if desired
- ▢ Add field to `nautobot/<app>/templates/<app>/<model>.html` detail template
- ▢ Add field to test data in appropriate unit tests (including view, filter, model, and API tests)
    - ▢ Add field testing in`test_api.<Model>TestCase`
    - ▢ Add field testing in `test_filters.<Model>TestCase`
    - ▢ Add field testing in `test_models.<Model>TestCase`
    - ▢ Add field testing in `test_views.<Model>TestCase`
    - ▢ _optional_ Add field testing in `test_forms.<Model>TestCase` if applicable
- ▢ Validate that the field appears correctly in GraphQL
    - ▢ If the field is not compatible with GraphQL or shouldn't be included in GraphQL it's possible to exclude a specific field in the GraphQL Type Object associated with this specific model. You can refer to the [graphene-django documentation](https://docs.graphene-python.org/projects/django/en/latest/queries/#specifying-which-fields-to-include) for additional information.
- ▢ Add field to model documentation with an appropriate version annotation
- ▢ _optional_ Add field to `<Model>Serializer` if default representation isn't optimal
- ▢ _optional_ Add field to `<Model>Serializer.fields` if it's not using `fields = ["__all__"]`
- ▢ _optional_ Add field to any custom create/edit template
- ▢ _optional_ Update model `clean()` with any new logic needed

### Adding a Foreign Key from ModelA to ModelB

- ▢ Select appropriate `on_delete` behavior (`SET_NULL`, `CASCADE`, `PROTECT`)
- ▢ Add a `DynamicModelChoiceField` to `<ModelA>Form`
- ▢ Add a `NaturalKeyOrPKMultipleChoiceFilter` to `<ModelA>FilterSet`
- ▢ Add a `DynamicModelMultipleChoiceField(required=False, ...)` to `<ModelA>FilterForm`
- ▢ Add a `DynamicModelChoiceField(required=False, ...)` to `<ModelA>BulkEditForm`
- ▢ Add `select_related` to API `<ModelA>ViewSet.queryset`
- ▢ Add `select_related` to UI `<ModelA>UIViewSet.queryset`
- ▢ _optional_ Add `annotate(<model_a>_count=count_related(ModelA,...)` to `<ModelB>ViewSet.queryset`
    - ▢ Add `<model_a>_count` field to `<ModelB>Serializer`
- ▢ _optional_ Add `<model_a>_count = LinkedCountColumn(...)` to `<ModelB>Table` and `<ModelB>Table.fields`
- ▢ _optional_ Add related object table to ModelB detail view

#### Adding a Status or Role field to a Model

- ▢ Use `StatusField` or `RoleField` in place of a generic `ForeignKey`
- ▢ Add [data migration](https://docs.djangoproject.com/en/stable/topics/migrations/) providing default Status/Role records for this model
    - ▢ Remember: data migrations must not share a file with schema migrations or vice versa!
    - ▢ Specify appropriate migration dependencies (for example, against another app that you're using models from)

### Adding a Many-to-Many from ModelA to ModelB

The through table should generally be treated as a new model (see above), but the following are most important.

- ▢ Add a `DynamicModelMultipleChoiceField` to `<ModelA>Form`
- ▢ Add `prefetch_related` to API `<ModelA>ViewSet.queryset`
- ▢ Add `prefetch_related` to UI `<ModelA>UIViewSet.queryset`
- ▢ Add REST API endpoint for managing the M2M
    - ▢ Serializer
    - ▢ FilterSet
    - ▢ ViewSet
    - ▢ URLs
    - ▢ Tests
- ▢ Add related object table to ModelA detail view
- ▢ _optional_ Add `annotate(<model_a>_count=count_related(ModelA,...)` to `<ModelB>ViewSet.queryset`
    - ▢ Add `<model_a>_count` field to `<ModelB>Serializer`
- ▢ _optional_ Add `<model_a>_count = LinkedCountColumn(...)` to `<ModelB>Table` and `<ModelB>Table.fields`
- ▢ _optional_ Add related object table to ModelB detail view
