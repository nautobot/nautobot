# Model Development Checklist

A general best-practices checklist to follow when adding a new data model in Nautobot or adding new fields to an existing model.

<!-- pyml disable-num-lines 9 no-inline-html -->
<style>
article ul li:before {
    content: '□';
    margin:0 5px 0 -15px;
}
article ul li {
    list-style-type: none;
}
</style>

## Bootstrapping a new Model

### Data Model

- Implement model in `nautobot.<app>.models` module
    - Use appropriate [base class](best-practices.md#base-classes) and mixin(s)
    - Use appropriate [`@extras_features`](#extras-features) decorator values
    - Unless there is a strong reason not to, all models should have a ForeignKey to `tenancy.Tenant` named `tenant`
    - Define appropriate uniqueness constraint(s)
    - Define appropriate `__str__()` logic
    - _optional_ Define appropriate additional [`clean()`](best-practices.md#model-validation) logic
        - Be sure to always call `super().clean()` as well!
    - _optional_ Define appropriate `verbose_name`/`verbose_name_plural` if defaults aren't optimal
    - _optional_ Opt out of specific model features **if and only if** there is a strong justification for doing so:
        - Contact/team association (`is_contact_associable_model = False`, OrganizationalModel/PrimaryModel only)
        - Dynamic-group association (`is_dynamic_group_associable_model = False`, OrganizationalModel/PrimaryModel only)
        - Object-metadata association (`is_metadata_associable_model = False`, any base class)
        - Saved-view support (`is_saved_view_model = False`, OrganizationalModel/PrimaryModel only)
- Generate database schema migration(s) with `invoke makemigrations <app> -n <migration_name>`
- _optional_ Add [data migration(s)](https://docs.djangoproject.com/en/stable/topics/migrations/#data-migrations) to populate default records, migrate data from existing models, etc.
    - Remember: data migrations must not share a file with schema migrations or vice versa!
    - Specify appropriate migration dependencies (for example, against another app that you're using models from). If you're retrieving models in a data migration with `apps.get_model("app_label.model_name")`, your migration should have a dependency that ensures the model is in the desired state before your migration runs. This may only require a dependency on the migration where that model was created or, if a specific field is required on the referenced model, the migration where that field was introduced.
- _optional_ Enhance `ConfigContext` if the new model can be used as a filter criteria for assigning Devices or Virtual Machines to Config Contexts
    - Update ConfigContextQuerySet, ConfigContextFilterSet, ConfigContext forms, edit and detail views and HTML templates
- _optional_ Expose any new relevant Python APIs in `nautobot.apps` namespace for App consumption

#### Extras Features

- `cable_terminations`: Models that can be connected to another model with a `Cable`
- `config_context_owners`: Models that can be assigned to the `owner` GenericForeignKey field on a `ConfigContext`
- `custom_fields`: (DEPRECATED - Uses `nautobot.extras.utils.populate_model_features_registry` to populate [Model Features Registry](model-features.md)) Models that support ComputedFields and CustomFields, used for limiting the choices for the `CustomField.content_types` and `ComputedField.content_type` fields
- `custom_links`: Models that can display `CustomLinks` on the object's detail view (by default, all models that use `generic/object_retrieve.html` as a base template support custom links)
- `custom_validators`: Models that can support custom `clean` logic by implementing a [`CustomValidator`](../apps/api/platform-features/custom-validators.md)
- `dynamic_groups`: Models that can be assigned to a `DynamicGroup`, used for limiting the choices for the `DynamicGroup.content_type` form field (DEPRECATED - Use the `DynamicGroupsModelMixin` class mixin instead)
- `export_template_owners`: Models that can be assigned to the `owner` GenericForeignKey field on an `ExportTemplate`
- `export_templates`: Models that can be exported using an `ExportTemplate`, used for limiting the choices for the `ExportTemplate.content_type` field
- `graphql`: Models that should be exposed through the [GraphQL API](../apps/api/models/graphql.md), used to build the list of registered models to build the GraphQL schema
- `job_results`: No longer used.
- `locations`: Models that support a foreign key to `Location`, used for limiting the choices for the `LocationType.content_types` field
- `relationships`: (DEPRECATED - Uses `nautobot.extras.utils.populate_model_features_registry` to populate [Model Features Registry](model-features.md)) Models that support custom relationships
- `statuses`: Models that support a foreign key to `Status`, used for limiting the choices for the `Status.content_types` field
- `webhooks`: Models that can be used to trigger webhooks, used for limiting the choices for the `Webhook.content_types` field

Most new models should use the `custom_links`, `custom_validators`, `export_templates`, `graphql`, and `webhooks` features at minimum.

### REST API

- Implement `<Model>FilterSet` class in `nautobot.<app>.filters` module
    - Use appropriate [base class](best-practices.md#base-classes) and mixin(s)
    - Define `Meta.fields` [appropriately](best-practices.md#mapping-model-fields-to-filters)
- Implement API `<Model>Serializer` class in `nautobot.<app>.api.serializers` module
    - Use appropriate [base class](best-practices.md#base-classes) and mixin(s)
- Implement API `<Model>ViewSet` class in `nautobot.<app>.api.views` module
    - Use appropriate [base class](best-practices.md#base-classes) and mixin(s)
    - Use appropriate `select_related`/`prefetch_related` for performance (bearing in mind that in Nautobot 2.4.0 and later, the viewset can perform many of these optimizations automatically)
- Add API viewset to `nautobot.<app>.api.urls` module

### UI

- Implement UI `<Model>Table` class in `nautobot.<app>.tables` module
    - Use appropriate [base class](best-practices.md#base-classes) and mixin(s)
    - In the vast majority of cases, a table's `Meta.fields` should have `"pk"` as the first entry and (if present as a column) `"actions"` as the last entry, so that these two columns appear correctly at the far left and far right of the table.
- Implement `<Model>Form` class in `nautobot.<app>.forms` module
    - Use appropriate [base class](best-practices.md#base-classes) and mixin(s)
- Implement `<Model>FilterForm` class in `nautobot.<app>.forms` module
    - Use appropriate [base class](best-practices.md#base-classes) and mixin(s)
- Implement `<Model>BulkEditForm` class in `nautobot.<app>.forms` module
    - Use appropriate [base class](best-practices.md#base-classes) and mixin(s)
- Implement `NautobotUIViewSet` subclass in `nautobot.<app>.views` module
    - Use appropriate [base class](best-practices.md#base-classes) and mixin(s)
    - Use appropriate `select_related`/`prefetch_related` for performance (bearing in mind that in the list view, the table class can perform many of these optimizations automatically)
    - Implement `object_detail_content` using the UI Component Framework
        - (only if strictly necessary) Implement `nautobot/<app>/templates/<app>/<model>_retrieve.html` detail template
- Add UI viewset to `nautobot.<app>.urls` module
- Add menu item in `nautobot.<app>.navigation` module
- _optional_ Add model link and counter to home page panel in `nautobot.<app>.homepage` module
- _optional_ Add model to `nautobot.<app>.apps.<App>Config.searchable_models` to include it in global search

### Test Coverage

- Implement `<Model>Factory` class in `nautobot.<app>.factory` module
    - Add `<Model>Factory` invocation to `nautobot-server generate_test_data` command
- Implement `<Model>TestCase` class in `nautobot.<app>.tests.test_api` module
    - Use appropriate `APITestCases` base class and mixin(s)
- Implement `<Model>TestCase` class in `nautobot.<app>.tests.test_filters` module
    - Use appropriate `FilterTestCases` base class and mixin(s)
- _optional_ Implement `<Model>TestCase` class in `nautobot.<app>.tests.test_forms` module
    - Use appropriate `FormTestCases` base class and mixin(s)
- Implement `<Model>TestCase` class in `nautobot.<app>.tests.test_models` module
    - Use appropriate `ModelTestCases` base class and mixin(s)
- Implement `<Model>TestCase` class in `nautobot.<app>.tests.test_views` module
    - Use appropriate base class and mixin(s)

### Documentation

- Write `nautobot/docs/user-guide/core-data-model/<app>/<model>.md` user documentation
    - Add document to `mkdocs.yml`
    - Add redirect from `models/<app>/<model>.md` in `mkdocs.yml` (this is needed so that the "question mark" button on the model's create/edit page will resolve correctly)
- Write an overview of the new model in the release-note `Release Overview` section

## Adding any new Field to a Model

- Name the field [appropriately](best-practices.md#field-naming-in-data-models)
- For CharFields, use [`CHARFIELD_MAX_LENGTH`](best-practices.md#charfield-and-slugfield-max-length) as appropriate
- Generate schema migration
    - Updating an existing migration is preferred if the model/migration hasn't yet shipped in a release. Once a new release has been published, its migrations **may not** be altered (other than for the purpose of correcting a bug).
- Add field to `<Model>Factory`
- Add field to `<Model>Form.fields`
- Add field to `<Model>BulkEditForm.fields`
- Add field filter(s) to `<Model>FilterSet`
    - Follow [best practices](best-practices.md#filter-naming-and-definition) for FilterSet fields
    - _optional_ Add field to `<Model>FilterSet` `q` filter
- Add field to `<Model>FilterForm.fields`
- Add field column to `<Model>Table.fields`
    - Keep `"pk"` as the first column and `"actions"` (if present) as the last column
    - _optional_ Add field column to `<Model>Table.default_columns` if desired
- Add field to `nautobot/<app>/templates/<app>/<model>_retrieve.html` detail template
- Add field to test data in appropriate unit tests (including view, filter, model, and API tests)
    - Add field testing in`test_api.<Model>TestCase`
    - Add field testing in `test_filters.<Model>TestCase`
    - Add field testing in `test_models.<Model>TestCase`
    - Add field testing in `test_views.<Model>TestCase`
    - _optional_ Add field testing in `test_forms.<Model>TestCase` if applicable
- Validate that the field appears correctly in GraphQL
    - If the field is not compatible with GraphQL or shouldn't be included in GraphQL it's possible to exclude a specific field in the GraphQL Type Object associated with this specific model. You can refer to the [`graphene-django` documentation](https://docs.graphene-python.org/projects/django/en/latest/queries/#specifying-which-fields-to-include) for additional information.
- Add field to model documentation with an appropriate version annotation
- _optional_ Add field to `<Model>Serializer` if default representation isn't optimal
- _optional_ Add field to `<Model>Serializer.fields` if it's not using `fields = ["__all__"]`
- _optional_ Add field to any custom create/edit template
- _optional_ Update model `clean()` with any new logic needed

### Adding a Foreign Key from ModelA to ModelB

- Specify appropriate [`related_name`](best-practices.md#field-naming-in-data-models)
- Select appropriate `on_delete` behavior (`SET_NULL`, `CASCADE`, `PROTECT`)
- Add a `DynamicModelChoiceField` to `<ModelA>Form`
- Add a [`NaturalKeyOrPKMultipleChoiceFilter`](best-practices.md#filter-naming-and-definition) to `<ModelA>FilterSet`
- Add a `DynamicModelMultipleChoiceField(required=False, ...)` to `<ModelA>FilterForm`
- Add a `DynamicModelChoiceField(required=False, ...)` to `<ModelA>BulkEditForm`
- Add `select_related` to API `<ModelA>ViewSet.queryset`
- Add `select_related` to UI `<ModelA>UIViewSet.queryset`
- Validate that the reverse relation is accessible through GraphQL on ModelB.
- _optional_ Add [`has_<related_name>` `RelatedMembershipBooleanFilter` filter](best-practices.md#filter-naming-and-definition) to `<ModelB>FilterSet`
- _optional_ Add `annotate(<model_a>_count=count_related(ModelA,...)` to `<ModelB>ViewSet.queryset`
    - Add `<model_a>_count` field to `<ModelB>Serializer`
- _optional_ Add `<model_a>_count = LinkedCountColumn(...)` to `<ModelB>Table` and `<ModelB>Table.fields`
- _optional_ Add related object table to ModelB detail view
    - For Role-related models, you **must** add the related object table to the Role detail view as we have a test that checks this

#### Adding a Status or Role field to a Model

- Use `StatusField` or `RoleField` in place of a generic `ForeignKey`
- Add [data migration](https://docs.djangoproject.com/en/stable/topics/migrations/) providing default Status/Role records for this model
    - Remember: data migrations must not share a file with schema migrations or vice versa!
    - Specify appropriate migration dependencies (for example, against another app that you're using models from)

### Adding a Many-to-Many from ModelA to ModelB

The through table should generally be treated as a new model (see above), but the following are most important.

- Specify appropriate [`related_name`](best-practices.md#field-naming-in-data-models)
- Add a `DynamicModelMultipleChoiceField` to `<ModelA>Form`
- Add `prefetch_related` to API `<ModelA>ViewSet.queryset`
- Add `prefetch_related` to UI `<ModelA>UIViewSet.queryset`
- Add REST API endpoint for managing the M2M
    - Serializer
    - FilterSet
    - ViewSet
    - URLs
    - Tests
- Add related object table to ModelA detail view
- Validate that the forward relation is accessible through GraphQL on ModelA.
- Validate that the reverse relation is accessible through GraphQL on ModelB.
- _optional_ Add `annotate(<model_a>_count=count_related(ModelA,...)` to `<ModelB>ViewSet.queryset`
    - Add `<model_a>_count` field to `<ModelB>Serializer`
- _optional_ Add `<model_a>_count = LinkedCountColumn(...)` to `<ModelB>Table` and `<ModelB>Table.fields`
- _optional_ Add related object table to ModelB detail view
