# App Code Updates for Nautobot v2

## Update Code Import Locations

Most changes in code location arise from the merging of the `nautobot.utilities` module into the `nautobot.core` module. Note that in most cases, the recommended approach for Jobs and Apps is to import from `nautobot.apps` rather than `nautobot.core` (see below).

??? info "Full table of code location changes"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-code-location-changes.yaml}

Other than models, most other imports from Nautobot should be imported from `nautobot.apps.*` as described here.

<!-- pyml disable-num-lines 2 proper-names -->
??? info "Full table of `nautobot.apps` code locations"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-code-nautobot-app-location.yaml}

## Replace PluginMenuItem with NavMenuItem

In your app's `navigation.py` file. If you are still using `PluginMenuItem` from `nautobot.extras.plugin`, you should replace those code with `NavMenuGroup`, `NavMenuItem`, and `NavMenuTab` from `nautobot.apps.ui`.

For example:

Before:

```python

    from nautobot.extras.plugins import PluginMenuItem

    menu_items = (
        PluginMenuItem(
            link="plugins:your_app:dashboard",
            link_text="Dashboard",
            permissions=["your_app.view_sync"],
        ),
        PluginMenuItem(
            link="plugins:your_app:sync_list",
            link_text="History",
            permissions=["your_app.view_sync"],
        ),
        PluginMenuItem(
            link="plugins:your_app:synclogentry_list",
            link_text="Logs",
            permissions=["your_app.view_synclogentry"],
        ),
    )

```

After:

```python

from nautobot.apps.ui import NavMenuGroup, NavMenuItem, NavMenuTab


items = [
    NavMenuItem(
        link="plugins:your_app:dashboard",
        name="Dashboard",
        permissions=["your_app.view_sync"],
    ),
    NavMenuItem(
        link="plugins:your_app:sync_list",
        name="History",
        permissions=["your_app.view_sync"],
    ),
    NavMenuItem(
        link="plugins:your_app:synclogentry_list",
        name="Logs",
        permissions=["your_app.view_synclogentry"],
    ),
]

menu_items = (
    NavMenuTab(
        name="Apps",
        groups=(NavMenuGroup(weight=1000, name="Your App", items=tuple(items)),),
    ),
)

```

### Remove Tag/Tags Filter from FilterSet Definitions

In Nautobot 2.0, you can safely remove `tag = TagFilter(...)` from your filter set definitions as long as your filter sets inherit from `NautobotFilterSet` class and `tags` is added to the filter set class `Meta.fields`.

For example, before the filter set could look like this:

```py

class AppModelFilterSet(BaseFilterSet):

    name = MultiValueCharFilter(...)
    number = MultiValueNumberFilter(...)
    tag = TagFilter(...)

    class Meta:
        fields = ["name", "number"]
```

After changing the base class to `NautobotFilterSet` the `tag` filter should be removed:

```py

class AppModelFilterSet(NautobotFilterSet):

    name = MultiValueCharFilter(...)
    number = MultiValueNumberFilter(...)

    class Meta:
        fields = ["name", "number", "tags"]

```

## Replace DjangoFilterBackend with NautobotFilterBackend

If your REST API has any `FilterBackend` classes derived from `DjangoFilterBackend`, you should replace `DjangoFilterBackend` with `NautobotFilterBackend`.

## App Model Serializer Inheritance

App Model Serializers for any models that could have a Generic Foreign Key or a Many to Many relationship from a Nautobot Core model **must** inherit from BaseModelSerializer at a minimum so that they have a properly generated `object_type` field. This also applies to the case where your model is a subclass of `ChangeLoggedModel` and you will have a Generic Foreign Key from `ObjectChange`'s `changed_object` field. Otherwise drf-spectacular schema generation will throw an error:

```no-highlight
(drf_spectacular.E001) Schema generation threw exception "Field name `object_type` is not valid for model `YourAppModel`.
```

## Revamp REST API Serializers

`NestedSerializer` classes are no longer needed in Nautobot 2.0. If any `NestedSerializers` exist for your models, you should just remove their class definitions and references.

After removing existing `NestedSerializers`, you can change the `fields` attribute in your serializers' `class Meta` to `__all__` and that will automatically include all the model's fields in the serializer, including related-model fields that would previously have required a reference to a `NestedSerializer`. If you want to exclude certain fields of the model, you can specify a list of fields you want to display in the `fields` attribute instead.

!!! warning
    Use caution around `fields = "__all__"` -- if your model has any fields that should _not_ be exposed in the REST API, you should avoid using `"__all__"` and instead use an explicit `fields` list to ensure that such fields are not exposed. In some cases, it may be appropriate to use `"__all__"` in combination with flags such as `write_only=True` on specific fields, but proceed with caution and examine the REST API data carefully to ensure that its contents are as expected.

Include all model attributes:

```python
class ExampleModelSerializer(NautobotModelSerializer):
    """Used for normal CRUD operations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:example_app-api:anotherexamplemodel-detail")

    class Meta:
        model = AnotherExampleModel
        fields = "__all__"
```

Include only specified model attributes:

```python
class ExampleModelSerializer(NautobotModelSerializer):
    """Used for normal CRUD operations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:example_app-api:anotherexamplemodel-detail")

    class Meta:
        model = AnotherExampleModel
        # example_attribute_4 is not included in the serializer
        fields = ["url", "example_attribute_1", "example_attribute_2", "example_attribute_3"]
```

In addition, the `?brief=` API query parameter is replaced by `?depth=<0-10>`. As a result, the ability to specify `brief_mode` in `DynamicModelChoiceField`, `DynamicModelMultipleChoiceField`, and `MultiMatchModelMultipleChoiceField` has also been removed. For every occurrence of the aforementioned fields where you have `brief_mode` set to `True/False` (e.g. `brief_mode=True`), please remove the statement, leaving other occurrences of the fields where you do not have `brief_mode` specified as they are. Check out our [API documentation](../../../user-guide/platform-functionality/rest-api/overview.md#depth-query-parameter) for this change.

## Revamp CSV Import and Export

CSV Import for models are now done automatically via the REST API. As a result of this change, `CSVForm` classes are no longer needed and should be deleted. In addition, the Model `csv_headers` attribute and `to_csv` method are no longer needed or used in CSV generation, and should be removed from your model definitions. Check out our [release notes](../../../release-notes/version-2.0.md#revamped-csv-import-and-export-254) for this specific change.

## Deprecated Templates

Over time, some templates have been deprecated and either consolidated or replaced with new ones.
If you are using a deprecated template, you should migrate to the new template.
We have included a script to help migrate all html files that extend a deprecated template to the new template.
You can run it with the following command:

```bash
nautobot-migrate-deprecated-templates <path-to-your-app> [--dry-run]
```

This will recursively find all `.html` files in the given path and replace extends references (`{% extends 'path/to/deprecated_template.html' %}`) to deprecated templates with the replacement ones.
You can also run it with the `--dry-run` flag to see what changes would be made without actually making any changes.

For a list of deprecated templates and their replacements, see the following table:

??? info "Full table of deprecated templates and their replacements"
    {data-table development/apps/migration/tables/deprecated-html-templates.yml}
