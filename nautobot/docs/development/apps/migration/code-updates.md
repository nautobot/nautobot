# App Code Updates for Nautobot v2

## Update Code Import Locations

Most changes in code location arise from the merging of the `nautobot.utilities` module into the `nautobot.core` module.

??? info "Full table of code location changes"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-code-location-changes.yaml}

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
        name="Plugins",
        groups=(NavMenuGroup(name="Your App", weight=1000, items=tuple(items)),),
    ),
)

```

## Replace DjangoFilterBackend with NautobotFilterBackend

If your REST API has any `FilterBackend` classes derived from `DjangoFilterBackend`, you should replace `DjangoFilterBackend` with `NautobotFilterBackend`.

## Revamp Rest API Serializers

`NestedSerializer` classes are no longer needed in Nautobot 2.0. If any `NestedSerializers` exist for your models, you should just remove their class definitions and references.

After removing existing `NestedSerializers`, you can change the `fields` attribute in your serializers' `class Meta` to `__all__` and that will automatically include all the model's fields in the serializer, including related-model fields that would previously have required a reference to a `NestedSerializer`. If you want to exclude certain fields of the model, you can specify a list of fields you want to display in the `fields` attribute instead.

Include all model attributes:

```python
class ExampleModelSerializer(NautobotModelSerializer):
    """Used for normal CRUD operations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:example_plugin-api:anotherexamplemodel-detail")

    class Meta:
        model = AnotherExampleModel
        fields = "__all__"
```

Include only specified model attributes:

```python
class ExampleModelSerializer(NautobotModelSerializer):
    """Used for normal CRUD operations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:example_plugin-api:anotherexamplemodel-detail")

    class Meta:
        model = AnotherExampleModel
        # example_attribute_4 is not included in the serializer
        fields = ["url", "example_attribute_1", "example_attribute_2", "example_attribute_3"]
```

In addition, the `?brief=` API query parameter is replaced by `?depth=<0-10>`. As a result, the ability to specify `brief_mode` in `DynamicModelChoiceField`, `DynamicModelMultipleChoiceField`, and `MultiMatchModelMultipleChoiceField` has also been removed. For every occurrence of the aforementioned fields where you have `brief_mode` set to `True/False` (e.g. `brief_mode=True`), please remove the statement, leaving other occurrences of the fields where you do not have `brief_mode` specified as they are. Check out our [API documentation](../../../user-guide/platform-functionality/rest-api/overview.md#depth-query-parameter) for this change.

## Revamp CSV Import and Export

CSV Import for models are now done automatically via the Rest API. As a result of this change, `CSVForms` classes are no longer needed and should be deleted. In addition, `csv_headers` and `to_csv` attributes should be removed from your model definition. Check out our [release notes](../../../release-notes/version-2.0.md#revamped-csv-import-and-export-2569-3715) for this specific change.
