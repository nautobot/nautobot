# Nautobot v3.3

This document describes all new features and chagnes in Nautobot 3.3.

## Upgrade Actions

### Administrators

TODO

## Release Overview

### Added

TODO

### Changed

TODO

#### Enhanced Export/Import

The object export/import functionality has been enhanced in several ways:

- JSON and YAML formats are now supported in addition to the existing CSV format support.
- Imports can now update existing records as well as create existing records, when requested ("upsert" functionality).
- CSV export/import now includes a metadata header row, and includes support for a wider range of many-to-many fields.

For more details, refer to the [import and export documentation](../user-guide/feature-guides/import-and-export.md).

### Dependencies

#### Removed Python 3.10 Support

As Python 3.10 is now end-of-life, Nautobot 3.3 has dropped support for Python 3.10.

<!-- pyml disable-num-lines 2 blanks-around-headers -->

<!-- towncrier release notes start -->

## v3.3.0a0 (2026-11-09)

### Breaking Changes in v3.3.0a0

- [#4138](https://github.com/nautobot/nautobot/issues/4138) - It is no longer possible to change the `ip_address`, `interface`, or `vm_interface` of an existing IP Address Assignment (`IPAddressToInterface`), including via the REST API; delete the assignment and create a new one instead.

### Security in v3.3.0a0

- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated dependency `gitpython` to `>=3.2.0,<3.3` to mitigate multiple vulnerabilities.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated dependency `urllib3` to `>=2.8.0,<3.0` to mitigate multiple vulnerabilities.

### Added in v3.3.0a0

- [#4138](https://github.com/nautobot/nautobot/issues/4138) - Added `PRIMARY_IP_REQUIRES_INTERFACE_ASSIGNMENT` configuration setting; when disabled, an IP address that is not assigned to any interface can be designated as the primary IP of a Device, Virtual Machine, or Virtual Device Context.
- [#4138](https://github.com/nautobot/nautobot/issues/4138) - Added "Unassigned primary IPv4" and "Unassigned primary IPv6" fields to the Device, Virtual Machine, and Virtual Device Context create/edit forms when `PRIMARY_IP_REQUIRES_INTERFACE_ASSIGNMENT` is disabled, allowing a primary IP to be set at creation time.
- [#4138](https://github.com/nautobot/nautobot/issues/4138) - Added `primary_ip4_for_virtual_machines` and `primary_ip6_for_virtual_machines` reverse relations from IP Address to Virtual Machine, including in GraphQL.
- [#4138](https://github.com/nautobot/nautobot/issues/4138) - Added `assigned` filter to IP Addresses, matching IP addresses that are assigned to an interface or designated as the primary IP of a Device, Virtual Machine, or Virtual Device Context.
- [#4138](https://github.com/nautobot/nautobot/issues/4138) - Added optional "Primary IP For" column to the IP Address list view.
- [#4138](https://github.com/nautobot/nautobot/issues/4138) - Added display of the Devices, Virtual Machines, and Virtual Device Contexts using an IP address as their primary IP to the "Assignment" row of the IP Address detail view, when the IP address is not assigned to any interface.
- [#8520](https://github.com/nautobot/nautobot/issues/8520) - Added drag-and-drop reordering for navbar favorite pages.
- [#9386](https://github.com/nautobot/nautobot/issues/9386) - Implemented UI toast component.
- [#9402](https://github.com/nautobot/nautobot/issues/9402) - Added background refresh of Django messages while the browser tab is active.
- [#9408](https://github.com/nautobot/nautobot/issues/9408) - Enhanced `ExportObjectList` system Job to support export to JSON and YAML formats for all models.
- [#9409](https://github.com/nautobot/nautobot/issues/9409) - Added a Playwright-based UI test framework as the forward standard for browser-based test coverage: shared page-object and fixture infrastructure in `nautobot/playwright/`, per-app test suites under `nautobot/<app>/tests/integration/`, an optional `playwright` dependency group, an `invoke playwright` task, and a `playwright-test` CI job. The Locations list view filter Selenium test was replaced by its Playwright equivalent.
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Exposed new environment variable `NAUTOBOT_RATE_LIMITING_REST_BUDGET_WINDOW_IN_SECONDS`
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Exposed new environment variable `NAUTOBOT_RATE_LIMITING_REST_BUDGET`
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Exposed new environment variable `NAUTOBOT_RATE_LIMITING_REST_MODE`
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Exposed new environment variable `NAUTOBOT_RATE_LIMITING_REST_READ_COST`
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Exposed new environment variable `NAUTOBOT_RATE_LIMITING_REST_WRITE_COST`
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Exposed new environment variable `NAUTOBOT_RATE_LIMITING_REST_INDEXABLE_LOOKUP_COST`
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Exposed new environment variable `NAUTOBOT_RATE_LIMITING_REST_UNINDEXABLE_LOOKUP_COST`
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Exposed new environment variable `NAUTOBOT_RATE_LIMITING_REST_PAGINATION_COST`
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Exposed new environment variable `NAUTOBOT_RATE_LIMITING_REST_DEPTH_MULTIPLIER_PER_LEVEL`
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Exposed new environment variable `NAUTOBOT_RATE_LIMITING_REST_COMPUTED_FIELDS_MULTIPLIER`
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Exposed new environment variable `NAUTOBOT_RATE_LIMITING_REST_CSV_MULTIPLIER`
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Exposed new environment variable `NAUTOBOT_RATE_LIMITING_GRAPHQL_MODE`
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Added `nautobot/core/rate_limiting` for rate limiting logic
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Added `to_int_or_none` helper function to `nautobot/core/utils/data.py`
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Added `RestReadRequestFeatures` to track identifiable query features in a REST read request
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Added `classify_rest_read_request_features` to generate a `RestReadRequestFeatures` from a REST request
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Added `estimate_rest_read_request_cost` to generate an estimated cost from a `RestReadRequestFeatures` object
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Added `calculate_records_per_page` to resolve the page size the paginator will actually serve
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Added `number` type support to `nautobot/core/tests/test_settings_schema.py`
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Added `ClassifyRestRequestFeaturesTestCase` in `nautobot/core/tests/test_rate_limiting.py` for validation
- [#9411](https://github.com/nautobot/nautobot/issues/9411) - Documented new settings in `nautobot/core/settings.yaml`
- [#9416](https://github.com/nautobot/nautobot/issues/9416) - Added a message to the "Export Object List" job when a many-to-many field has additional data recorded about each association (such as the priority recorded against each of an InterfaceRedundancyGroup's interfaces), noting which values are not included in the export and where to find them.
- [#9420](https://github.com/nautobot/nautobot/issues/9420) - Added an internal `nautobot.extras.conditions` package (comparison operators, event payload builder, and condition preset catalog) with a `condition_presets` registry that Apps can register into via `register_condition_preset()`.
- [#9421](https://github.com/nautobot/nautobot/issues/9421) - Added `ObjectOverviewViewMixin`, providing a per-object overview endpoint on `NautobotUIViewSet`.
- [#9428](https://github.com/nautobot/nautobot/issues/9428) - Added a summary of recent successful run durations to the Job run form and job modal, showing the median and, for jobs whose runtime varies, the longest recent run.
- [#9441](https://github.com/nautobot/nautobot/issues/9441) - Added `RequestPerformanceMeasurementsMiddleware` to measure and report request performance measurements as a `Server-Timing` header in HTTP responses.
- [#9441](https://github.com/nautobot/nautobot/issues/9441) - Added `REQUEST_TOTAL_DURATION_HEADER_ENABLED` settings variable, which when set to true enables a "total request duration" performance measurement on each request/response.
- [#9441](https://github.com/nautobot/nautobot/issues/9441) - Added `REQUEST_DB_DURATION_HEADER_ENABLED` settings variable, which when set to true enables a "database query duration" performance measurement on each request/response.
- [#9448](https://github.com/nautobot/nautobot/issues/9448) - Enhanced `ExportObjectList` system Job with an `export_fields` parameter, restricting an export to the fields named and rendering the columns in that order. Fields may include nested references to related objects that the user has permission to view, such as `status__name` or `device_type__manufacturer__name`, as well as custom fields, such as `cf_my_field`.
- [#9448](https://github.com/nautobot/nautobot/issues/9448) - Added suppression of the `match_fields` import metadata when the selected fields do not cover the entirety of a model's default natural key.
- [#9450](https://github.com/nautobot/nautobot/issues/9450) - Added an expand button on object list rows that reveals an overview of the object's fields without leaving the list.
- [#9455](https://github.com/nautobot/nautobot/issues/9455) - Added `ConditionTypeChoices`.
- [#9455](https://github.com/nautobot/nautobot/issues/9455) - Added `ConditionRow` (preset and raw-expression rows), expression compilation and `check()` to the internal `nautobot.extras.conditions` package.
- [#9462](https://github.com/nautobot/nautobot/issues/9462) - Enhanced the `ExportObjectList` system Job to apply the launching list view's sort order, including a saved view's stored `sort_order`, in addition to its filters.
- [#9462](https://github.com/nautobot/nautobot/issues/9462) - Added a `nautobot-server export_objects` management command that runs the `ExportObjectList` Job locally, for development and manual testing of the export pipeline.
- [#9462](https://github.com/nautobot/nautobot/issues/9462) - Added `NON_FILTER_PARAMS` and `resolve_filter_params()` to `nautobot.apps.utils`, for Apps that need to resolve the filters a list view has applied the way Nautobot's own list views resolve them.
- [#9468](https://github.com/nautobot/nautobot/issues/9468) - Added `ComplexityCostRateLimitingMiddleware` to instrument request complexity costs into response header.
- [#9469](https://github.com/nautobot/nautobot/issues/9469) - Added the `CHANGELOG_SKIP_UNCHANGED_SAVES` setting, which can be set to `False` to keep recording change records for saves that modify none of an object's field values, as Nautobot did before 3.3.0.
- [#9469](https://github.com/nautobot/nautobot/issues/9469) - Exposed `event_topic_has_subscriber()` in `nautobot.apps.events`, which reports whether any registered event broker would receive a given topic, so that an App can skip building a payload that nothing would consume.
- [#9501](https://github.com/nautobot/nautobot/issues/9501) - Added a "Fields to Export" picker to the export dialog and to the `Export Object List` Job's own form, for checking the specific fields to export - including fields of related objects, such as a device's manufacturer, and each custom field - and dragging them into the order the columns should appear in.
- [#9501](https://github.com/nautobot/nautobot/issues/9501) - Added a "Match the list view" button to that picker, which fills the selection in with the columns the list view is displaying, in the order it displays them - those of the saved view in use, else your own table configuration, else the table's defaults - so they can be reviewed and adjusted before the export runs. A related-object-count column is carried across as the relation it counts, where an export can emit that relation; any column with no exportable equivalent is named rather than quietly dropped.
- [#9501](https://github.com/nautobot/nautobot/issues/9501) - Added a download button to the export progress dialog, offering the exported file as soon as the export finishes.
- [#9501](https://github.com/nautobot/nautobot/issues/9501) - Added support for a Job variable's form field to be configured from the rest of the Job form, through a `configure_for_form()` method, so that an App can offer a variable whose choices depend on what another variable is set to.
- [#9513](https://github.com/nautobot/nautobot/issues/9513) - Added a `conditions` field to webhooks and job hooks.
- [#9513](https://github.com/nautobot/nautobot/issues/9513) - Added a condition preset catalog endpoint at `/api/extras/condition-presets/`, so a client building condition rows reads the available presets and their parameters.
- [#9521](https://github.com/nautobot/nautobot/issues/9521) - Added evaluation of conditions on webhooks and job hooks, so an action that carries conditions now runs only for the changes those conditions accept.
- [#9521](https://github.com/nautobot/nautobot/issues/9521) - Added an error log entry naming the action and the condition when a condition cannot be evaluated. The action does not run for that change.
- [#9524](https://github.com/nautobot/nautobot/issues/9524) - Added `nautobot.apps.utils.mock_wsgi_request` helper function.
- [#9524](https://github.com/nautobot/nautobot/issues/9524) - Added JSON and YAML support to the `Import Objects` system Job, which previously accepted CSV only. The format is auto-detected from the file extension or content, or can be selected explicitly.
- [#9524](https://github.com/nautobot/nautobot/issues/9524) - Added support for importing a file that declares its own `model`, in which case the content type need not be specified. A file that declares a different model than the one requested is refused.
- [#9524](https://github.com/nautobot/nautobot/issues/9524) - Added a `nautobot-server import_objects` management command, which runs the `Import Objects` Job locally.
- [#9524](https://github.com/nautobot/nautobot/issues/9524) - Added a `ScriptVariable.default` attribute, recording the `default=` a Job variable was declared with.
- [#9524](https://github.com/nautobot/nautobot/issues/9524) - Added `APIViewTestCases.CreateObjectViewTestCase.test_recreate_object_document`, a generic per-model check that an object exported to the JSON/YAML document format can be imported back from it.
- [#9542](https://github.com/nautobot/nautobot/issues/9542) - Added row selection and bulk edit helpers (`select_row`, `click_edit_selected`, `expect_bulk_edit_count`, `get_bulk_edit_pks`, `apply_bulk_edit`) to `nautobot.playwright.list_page.ListPage`.
- [#9543](https://github.com/nautobot/nautobot/issues/9543) - Added a `searchable` attribute to nav menu items, so they can be excluded from the global search bar's model filters.
- [#9547](https://github.com/nautobot/nautobot/issues/9547) - Added in-place updates to the `Import Objects` system Job: records that match an existing object, by default on its natural key, update that object instead of creating a new one.
- [#9547](https://github.com/nautobot/nautobot/issues/9547) - Added a `Meta.import_match_fields` attribute for REST API serializers, declaring the match fields of a model whose natural key isn't spelled in the serializer's own fields, and declared it for IP addresses (`namespace`, and `address` matched on its host alone), IP address ranges (`namespace`, `start_address`) and prefixes (`prefix`, `namespace`).
- [#9547](https://github.com/nautobot/nautobot/issues/9547) - Added support for `IPAddressRange.objects.filter(start_address=..., end_address=...)` and the equivalent `exclude()`, as with `IPAddress.objects.filter(address=...)`.
- [#9558](https://github.com/nautobot/nautobot/issues/9558) - Added `get_all_saved_views_for_user` to `nautobot.apps.views`.
- [#9559](https://github.com/nautobot/nautobot/issues/9559) - Added request duration and db duration metrics to Prometheus.
- [#9559](https://github.com/nautobot/nautobot/issues/9559) - Added rest complexity cost rate limiting metrics to Prometheus.
- [#9561](https://github.com/nautobot/nautobot/issues/9561) - Added a Conditions section to the webhook and job hook edit forms, and a Conditions panel to their detail views.
- [#9561](https://github.com/nautobot/nautobot/issues/9561) - Added `ColorSelectMultiple` to `nautobot.apps.forms`, a `ColorSelect` for a field that holds several colors at once.
- [#9562](https://github.com/nautobot/nautobot/issues/9562) - Added optional `depth`, `depth_unit`, `weight` and `weight_unit` fields to the Device Type model.
- [#9562](https://github.com/nautobot/nautobot/issues/9562) - Added optional `weight` and `weight_unit` fields to the Module Type model.
- [#9562](https://github.com/nautobot/nautobot/issues/9562) - Added the new depth and weight fields to the single-record YAML/JSON import and export of Device Types and Module Types, which follow the devicetype-library format.
- [#9562](https://github.com/nautobot/nautobot/issues/9562) - Added `WeightUnitChoices` to `nautobot.apps.choices`.
- [#9571](https://github.com/nautobot/nautobot/issues/9571) - Added a `job_form` block to the `extras/htmx/job_form_modal.html` template.
- [#9574](https://github.com/nautobot/nautobot/issues/9574) - Added the `contains` operator for a condition on a many-valued field such as tags.
- [#9584](https://github.com/nautobot/nautobot/issues/9584) - Added Custom Fields in conditions selects.
- [#9588](https://github.com/nautobot/nautobot/issues/9588) - Added support for passing a file object as the `content` of `Job.create_file()`.
- [#9594](https://github.com/nautobot/nautobot/issues/9594) - Added the ability to favorite any page.
- [#9602](https://github.com/nautobot/nautobot/issues/9602) - Added the `NAUTOBOT_RATE_LIMITING_CUSTOM_COMPLEXITY_COST_ESTIMATION_FUNCTION` setting, allowing a deployment to replace Nautobot's built-in rate limiting complexity cost estimation with its own function.
- [#9605](https://github.com/nautobot/nautobot/issues/9605) - Added `DetailPage.click_edit()`, `ListPage.select_all_rows()`, `ListPage.select_all_matching()`, `ListPage.assign_all_matching_to_group()` and the `restore_page_size` fixture to `nautobot.playwright`.
- [#9615](https://github.com/nautobot/nautobot/issues/9615) - Added `ObjectFormPage`, `create_object.track()`, and the `created_location`, `created_device_type` and `created_role` fixtures to `nautobot.playwright`.
- [#9671](https://github.com/nautobot/nautobot/issues/9671) - Added `nautobot.playwright.accessibility.assert_no_accessibility_violations()` and the `axe_core_on_load` fixture for axe-core scans in Playwright tests.
- [#9704](https://github.com/nautobot/nautobot/issues/9704) - Added an "Import Mode" input ("Create/Update", "Create Only", or "Update Only") to the Import Objects system Job, and a matching `--mode` option to `nautobot-server import_objects`.
- [#9704](https://github.com/nautobot/nautobot/issues/9704) - Added a `can_import` filter to the content types REST API endpoint.
- [#9729](https://github.com/nautobot/nautobot/issues/9729) - Added sticky table headers to object list views.
- [#9740](https://github.com/nautobot/nautobot/issues/9740) - Added `export` and `import` model features and `is_exportable_model` and `is_importable_model` class attributes on `BaseModel`, which a model can set to `False` to opt out of support by the "Export Object List" and "Import Objects" system Jobs respectively.
- [#9740](https://github.com/nautobot/nautobot/issues/9740) - Added `FeatureQuery.includes()` method to check whether a given model supports a given feature.
- [#9753](https://github.com/nautobot/nautobot/issues/9753) - Added a search field to the object embedded search form.
- [#9754](https://github.com/nautobot/nautobot/issues/9754) - Added the `namespace` field to IP Address and IP Address Range REST API responses; it was previously accepted on create but not returned.
- [#9754](https://github.com/nautobot/nautobot/issues/9754) - Added the `namespace` property to the IP Address and IP Address Range models.
- [#9754](https://github.com/nautobot/nautobot/issues/9754) - Added the `translate_import_match_field_and_value_to_database_lookup()` serializer method, which an app's serializer can override to control how an import looks up existing records from a given match field.
- [#9754](https://github.com/nautobot/nautobot/issues/9754) - Added the `Meta.related_field_query_paths` serializer option, mapping a related field that exists only on the serializer to the database path it is reached by, for export and import matching.
- [#9754](https://github.com/nautobot/nautobot/issues/9754) - Added the `Meta.derived_fields_omitted_from_default_export` serializer option, listing fields that an export leaves out unless they are explicitly selected.
- [#9778](https://github.com/nautobot/nautobot/issues/9778) - Added `htmx_only` optional kwarg for use by `NautobotViewSetMixin` actions that only respond positively to HTMX requests.

### Changed in v3.3.0a0

- [#4138](https://github.com/nautobot/nautobot/issues/4138) - Changed Virtual Device Context primary IP validation to require that the IP address be assigned to one of the interfaces assigned to the Virtual Device Context, rather than to any of the parent Device's interfaces, and to also permit the NAT outside address of such an IP address.
- [#4138](https://github.com/nautobot/nautobot/issues/4138) - Changed the "Assigned" column of the IP Address list view to also indicate IP addresses designated as the primary IP of a Device, Virtual Machine, or Virtual Device Context.
- [#4138](https://github.com/nautobot/nautobot/issues/4138) - Changed the validation of Device, Virtual Machine, and Virtual Device Context primary IP addresses to permit a primary IP that is not assigned to any interface and is unchanged from its saved value, regardless of `PRIMARY_IP_REQUIRES_INTERFACE_ASSIGNMENT`.
- [#4138](https://github.com/nautobot/nautobot/issues/4138) - Changed the IP Address merge tool to abort with an error, rather than complete, if the merged IP address would not be a valid primary IP for the Devices, Virtual Machines, and Virtual Device Contexts using the merged IP addresses as their primary IP.
- [#4138](https://github.com/nautobot/nautobot/issues/4138) - Changed IP address to interface assignment validation to reject assigning an IP address to an interface that does not belong to the Device, Virtual Machine, or Virtual Device Context using it as a primary IP without an interface assignment.
- [#9402](https://github.com/nautobot/nautobot/issues/9402) - Changed Django messages to render as toasts by default instead of alerts.
- [#9408](https://github.com/nautobot/nautobot/issues/9408) - Changed the format of CSV exports produced by `ExportObjectList` system Job to include a header comment containing metadata.
- [#9408](https://github.com/nautobot/nautobot/issues/9408) - Changed CSV exports to include more many-to-many fields by default.
- [#9408](https://github.com/nautobot/nautobot/issues/9408) - Changed the `ExportObjectList` system Job `export_format` parameter to distinguish between `yaml` (the new generic YAML export format) and `devicetype_library` (the custom YAML format used specifically for DeviceType and ModuleType interoperability with the [`devicetype-library` repository](https://github.com/nautobot/devicetype-library/)). Previously running the Job with `export_format="yaml"` would generate the latter format, now it generates the new format instead.
- [#9408](https://github.com/nautobot/nautobot/issues/9408) - Added database query optimizations to the `ExportObjectList` system Job to improve performance of exports.
- [#9416](https://github.com/nautobot/nautobot/issues/9416) - Changed JSON/YAML export of many-to-many fields to nest each member's related-object keys (`software_version: {version: ...}`) instead of flattening them (`software_version__version: ...`), matching how other related objects are exported.
- [#9469](https://github.com/nautobot/nautobot/issues/9469) - Changed saving an object that modifies none of its fields to no longer create a change record, and to no longer trigger webhooks, job hooks, or events. The object's `last_updated` timestamp is still written.
- [#9469](https://github.com/nautobot/nautobot/issues/9469) - Changed the `prechange` snapshot in webhook and event payloads to be generated from the stored database row at the time of the save, instead of being retrieved from the object's previous ObjectChange record.
- [#9501](https://github.com/nautobot/nautobot/issues/9501) - Changed the "Export to file" action on object list views to open a dialog in which the export format and the fields to export can be selected, in place of the previous one-click "Export as CSV" and "Export as YAML" entries.
- [#9501](https://github.com/nautobot/nautobot/issues/9501) - Changed the "Export to file" action to be disabled, with an explanatory tooltip, for users who cannot run the "Export Object List" Job, or when that Job is disabled.
- [#9514](https://github.com/nautobot/nautobot/issues/9514) - Changed multiple custom links to be collected into a single dropdown menu.
- [#9514](https://github.com/nautobot/nautobot/issues/9514) - Changed custom link buttons to display a link icon.
- [#9516](https://github.com/nautobot/nautobot/issues/9516) - Changed `ComplexityCostRateLimitingMiddleware` to persist rate limit budget in Redis
- [#9516](https://github.com/nautobot/nautobot/issues/9516) - 
- [#9516](https://github.com/nautobot/nautobot/issues/9516) - Renamed `NAUTOBOT_RATE_LIMITING_LIMIT` to `NAUTOBOT_RATE_LIMITING_REST_BUDGET`
- [#9517](https://github.com/nautobot/nautobot/issues/9517) - Lightened borders, dividers, and navigation menu links hover highlight in dark mode.
- [#9524](https://github.com/nautobot/nautobot/issues/9524) - Changed the `Import Objects` system Job to reject data containing unrecognized fields, including unrecognized `cf_<key>` custom fields, rather than silently ignoring them. Fields that Nautobot generates rather than stores, such as `display` and `object_type`, continue to be accepted and ignored so that an exported file re-imports unchanged.
- [#9524](https://github.com/nautobot/nautobot/issues/9524) - Changed the object-list "Import" button to read "Import from File", the Job now accepting more than CSV.
- [#9543](https://github.com/nautobot/nautobot/issues/9543) - Excluded the following nav menu items from the global search bar's model filters: Apps Marketplace, Installed Apps, Device Constraints, IP Address Assignments, Wireless Controllers and (Wireless) Device Groups.
- [#9543](https://github.com/nautobot/nautobot/issues/9543) - Renamed the Virtualization "Interfaces" nav menu item to "VM Interfaces".
- [#9547](https://github.com/nautobot/nautobot/issues/9547) - Changed exported `match_fields` metadata to name the object's own fields rather than lookups into related objects, for example `match_fields=manufacturer model` for device types rather than `match_fields=manufacturer__name model`.
- [#9547](https://github.com/nautobot/nautobot/issues/9547) - Changed CSV import, including via the REST API, to treat a related object whose every column reads `NoObject` as null, so that updating an object from such a row clears the relation rather than leaving it unchanged.
- [#9547](https://github.com/nautobot/nautobot/issues/9547) - Changed the `Import Objects` system Job to update, rather than fail on, records that match an existing object, including when no match fields are given. The Job now also returns the counts of created, updated and unchanged objects, and the match fields it used.
- [#9562](https://github.com/nautobot/nautobot/issues/9562) - Renamed the REST API OpenAPI schema component for the Rack `outer_unit` choices from `OuterUnitEnum` to `RackDimensionUnitChoices`, as the same choices now also apply to the Device Type `depth_unit` field.
- [#9571](https://github.com/nautobot/nautobot/issues/9571) - Changed the "Import from file" action on object list views to open the `Import Objects` Job in a dialog.
- [#9571](https://github.com/nautobot/nautobot/issues/9571) - Changed the "Import from file" action to be disabled for users who cannot run the `Import Objects` Job, or when that Job is disabled.
- [#9571](https://github.com/nautobot/nautobot/issues/9571) - Changed the `job_import_button` template tag to require the template context.
- [#9576](https://github.com/nautobot/nautobot/issues/9576) - Changed the default placeholder for dropdown menus from `---------` to a single em-dash.
- [#9587](https://github.com/nautobot/nautobot/issues/9587) - Changed the "Fields to Export" picker so that checking a related object selects the fields that identify it, then all of its fields, then none; added a "Natural key" option where those fields are not all listed, and an "All custom fields" option.
- [#9601](https://github.com/nautobot/nautobot/issues/9601) - Changed webhooks and job hooks to allow more than one hook with the same content type, the same target (payload URL or Job) and a common action. Previously the second such hook was refused with "A webhook already exists" or "A job hook already exists".
- [#9621](https://github.com/nautobot/nautobot/issues/9621) - Changed the styling of expandable table rows.
- [#9670](https://github.com/nautobot/nautobot/issues/9670) - Added a filter box to the Swagger UI REST API documentation page for filtering endpoints by path.
- [#9704](https://github.com/nautobot/nautobot/issues/9704) - Changed object list views and the Import Objects Job form to offer importing to users with either of `add` or `change` permission.
- [#9710](https://github.com/nautobot/nautobot/issues/9710) - Changed the API Tokens view to partially obscure displayed token keys.
- [#9740](https://github.com/nautobot/nautobot/issues/9740) - Changed the "Import Objects" and "Export Object List" system Jobs to only accept content-types for Nautobot core and App models (`BaseModel` subclasses), plus `auth.Group` and (for export only) `contenttypes.ContentType`, rather than any installed model such as those provided by `django-celery-beat` or `django-constance`.
- [#9740](https://github.com/nautobot/nautobot/issues/9740) - Changed object list views to omit the "Import" or "Export" button for models that do not support import or export respectively.
- [#9754](https://github.com/nautobot/nautobot/issues/9754) - Changed the export of IP Addresses and IP Address Ranges to leave out their parent Prefix unless it is explicitly selected, as it is determined by their Namespace and address, so that an exported file can still be imported after the parent Prefix changes.
- [#9754](https://github.com/nautobot/nautobot/issues/9754) - Changed `assertInstanceEqual()` to compare a model instance returned by a non-field attribute, such as a property, by its primary key, as it already compares foreign key fields.
- [#9761](https://github.com/nautobot/nautobot/issues/9761) - Improved the hover and focus appearance of tag links.

### Deprecated in v3.3.0a0

- [#4138](https://github.com/nautobot/nautobot/issues/4138) - Deprecated the `VirtualDeviceContext.validate_primary_ips()` method; primary IP validation is performed by `VirtualDeviceContext.clean()`.
- [#9754](https://github.com/nautobot/nautobot/issues/9754) - Deprecated the `_namespace` property of the IP Address and IP Address Range models in favor of the new `namespace` property.

### Removed in v3.3.0a0

- [#9576](https://github.com/nautobot/nautobot/issues/9576) - Removed default `placeholder` text identical to the form-field `label` from most forms. Form fields with explicitly specified `placeholder` values are unaffected.
- [#9601](https://github.com/nautobot/nautobot/issues/9601) - Removed the `Webhook.check_for_conflicts()` and `JobHook.check_for_conflicts()` class methods.
- [#9671](https://github.com/nautobot/nautobot/issues/9671) - Removed `SeleniumTestCase.assertNoAccessibilityViolations()`. Playwright tests call `nautobot.playwright.accessibility.assert_no_accessibility_violations()` instead.

### Fixed in v3.3.0a0

- [#4138](https://github.com/nautobot/nautobot/issues/4138) - Fixed an exception when removing an IP address from an interface on a module that is not installed in a Device.
- [#4138](https://github.com/nautobot/nautobot/issues/4138) - Fixed a Virtual Device Context's primary IP not being cleared when the IP address is removed from the Virtual Device Context's interfaces.
- [#4138](https://github.com/nautobot/nautobot/issues/4138) - Fixed the IP Address merge tool clearing, rather than updating, the primary IP of Virtual Device Contexts using one of the merged IP addresses.
- [#9111](https://github.com/nautobot/nautobot/issues/9111) - Fixed duplication of form fields when a NautobotUIViewSet-based embedded "create" modal failed form validation.
- [#9111](https://github.com/nautobot/nautobot/issues/9111) - Fixed an exception being raised when viewing the detail view of an IPAddress with a null `parent`.
- [#9416](https://github.com/nautobot/nautobot/issues/9416) - Fixed CSV export of many-to-many fields whose values contain a comma, double-quote, or newline; such values are now quoted so they can be imported correctly.
- [#9416](https://github.com/nautobot/nautobot/issues/9416) - Fixed CSV import of a many-to-many column exported for related objects that are identified by more than one field, such as a Device's software image files.
- [#9448](https://github.com/nautobot/nautobot/issues/9448) - Fixed representation of nested UUIDs in object-list exports from MySQL.
- [#9462](https://github.com/nautobot/nautobot/issues/9462) - Fixed the `ExportObjectList` system Job discarding a saved view's stored filters when the query string carried only non-filter parameters, such as `sort` or `page`, exporting every object instead of the view's own. Saved-view filters are now resolved exactly as `ObjectListView` resolves them.
- [#9462](https://github.com/nautobot/nautobot/issues/9462) - Fixed the `ExportObjectList` system Job treating a list view's own query parameters as filters, such as `expanded_subtree` on the Prefix and Device list views. An export launched from such a view discarded the saved view's filters; the Job now takes the set of non-filter parameters from the launching view.
- [#9462](https://github.com/nautobot/nautobot/issues/9462) - Fixed the `ExportObjectList` system Job failing to export a content type that has no filterset, or whose model is a plain Django model rather than a Nautobot one - `auth | group` and `contenttypes | content type` are both. Object permissions continue to be applied to these exports, and filters that cannot be applied for want of a filterset now fail the Job with an explanatory message rather than being silently ignored.
- [#9462](https://github.com/nautobot/nautobot/issues/9462) - Fixed the `ExportObjectList` system Job raising an unhandled exception, rather than reporting a clear error, when asked to export a content type whose model no longer exists.
- [#9469](https://github.com/nautobot/nautobot/issues/9469) - Fixed a slow memory leak in change logging, where the captured pre-change state of an object was retained for the lifetime of the worker process instead of the request that captured it.
- [#9514](https://github.com/nautobot/nautobot/issues/9514) - Fixed the "New window" option on custom links having no effect.
- [#9524](https://github.com/nautobot/nautobot/issues/9524) - Fixed Job `BooleanVar` variables declared with `default=True` (such as `ImportObjects.roll_back_if_error`) being received as `False` when omitted from a REST API job-run request.
- [#9524](https://github.com/nautobot/nautobot/issues/9524) - Fixed the `Import Objects` system Job being unable to import models whose serializer takes the owning user from the request, such as Tokens and Saved Views; the Job now deserializes under a request carrying the user who ran it.
- [#9524](https://github.com/nautobot/nautobot/issues/9524) - Fixed the export field picker's "Match the list view" button appearing to do nothing for a content type that has no list view, such as `users | token`; it now says so rather than returning an empty selection.
- [#9547](https://github.com/nautobot/nautobot/issues/9547) - Fixed the `Import Objects` system Job failing, before importing anything, for object types whose manager doesn't support object permissions, such as users.
- [#9554](https://github.com/nautobot/nautobot/issues/9554) - Fixed spurious change-log entries being recorded when clearing a many-to-many field (such as an interface's tagged VLANs or a VRF's assigned devices) that was already empty.
- [#9576](https://github.com/nautobot/nautobot/issues/9576) - Fixed incorrect widget for the `type` field when creating/editing Prefixes.
- [#9587](https://github.com/nautobot/nautobot/issues/9587) - Fixed an export field selection naming a related object reached through another one, such as `device_type__manufacturer`, exporting that object's ID instead of the fields that identify it.
- [#9588](https://github.com/nautobot/nautobot/issues/9588) - Fixed the `ExportObjectList` system Job running out of memory when exporting large numbers of records.
- [#9642](https://github.com/nautobot/nautobot/issues/9642) - Fixed webhooks and job hooks accepting a condition on a field path that cannot be referenced in a condition for their content types, such as `location.parent.name` or a deleted custom field or unknown field.
- [#9670](https://github.com/nautobot/nautobot/issues/9670) - Fixed the Redoc REST API documentation page loading the Redocly logo from an external CDN; the logo is now bundled with Nautobot's static files.
- [#9746](https://github.com/nautobot/nautobot/issues/9746) - Fixed navbar favorites accepting external links and malformed data.
- [#9754](https://github.com/nautobot/nautobot/issues/9754) - Fixed the REST API ignoring a `namespace` given when updating an existing IP Address or IP Address Range. The object is now moved into that Namespace and its parent Prefix is resolved again within it, as the edit form already does.
- [#9761](https://github.com/nautobot/nautobot/issues/9761) - Fixed tag links, and the header's search help link,  being too small to satisfy the WCAG 2.2 pointer target minimum.
- [#9763](https://github.com/nautobot/nautobot/issues/9763) - Fixed exported Job console log timestamps not being rendered in the requesting user's configured timezone.

### Dependencies in v3.3.0a0

- [#9315](https://github.com/nautobot/nautobot/issues/9315) - Updated dependency `djangorestframework` to `>=3.18.0,<3.19`.
- [#9315](https://github.com/nautobot/nautobot/issues/9315) - Updated dependencies `opentelemetry-sdk` and `opentelemetry-exporter-otlp` to `>=1.44.0,<1.45`, and updated all associated `opentelemetry-instrumentation-*` dependencies to `>=0.65b0,<0.66`.
- [#9315](https://github.com/nautobot/nautobot/issues/9315) - Updated dependency `prometheus-client` to `>=0.26.0,<0.27`.
- [#9316](https://github.com/nautobot/nautobot/issues/9316) - Updated dependency `django-filter` to `>=26.1,<26.2`.
- [#9456](https://github.com/nautobot/nautobot/issues/9456) - Dropped support for Python 3.10 as it approaches end-of-life. Python 3.11 will be the minimum version for Nautobot 3.3.
- [#9456](https://github.com/nautobot/nautobot/issues/9456) - Updated dependency `django-tables2` to `>=3.0.1,<3.1`.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated dependency `django-silk` to `>=5.6.0,<5.7`.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated dependency `django-tree-queries` to `>=0.26.1,<0.27`.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated dependency `djangorestframework` to `>=3.18.1,<3.19`.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated dependency `emoji` to `>=2.16.0,<2.17`.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated dependency `Markdown` to `>=3.11,<3.12`.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated dependency `mysqlclient` to `>=2.3.0,<2.4`.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated OpenTelemetry dependencies to `>=1.45.0,<1.46` and `>=0.66b0,<0.67` as a group.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated dependency `social-auth-app-django` to `>=6.1.0,<6.2`.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated dependency `social-auth-core` to `>=5.2.0,<5.3`.
- [#9611](https://github.com/nautobot/nautobot/issues/9611) - Updated dependency `Markdown` to `>=3.11.2,<3.12`.
- [#9611](https://github.com/nautobot/nautobot/issues/9611) - Updated optional dependency `django-auth-ldap` to `>=5.4.0,<5.5`.
- [#9611](https://github.com/nautobot/nautobot/issues/9611) - Updated dependency `django-constance` to `>=4.5.0,<4.6`.
- [#9611](https://github.com/nautobot/nautobot/issues/9611) - Updated dependency `django-filter` to `>=26.2,<26.3`.
- [#9611](https://github.com/nautobot/nautobot/issues/9611) - Updated dependency `django-tree-queries` to `>=0.28.0,<0.29`.
- [#9612](https://github.com/nautobot/nautobot/issues/9612) - Updated dependency `django-structlog` to `>=11.0,<11.1`.
- [#9612](https://github.com/nautobot/nautobot/issues/9612) - Updated dependency `kubernetes` to `>=37.0.1,<38`.
- [#9612](https://github.com/nautobot/nautobot/issues/9612) - Updated dependency `python-slugify` to `>=9.1.3,<9.2`.
- [#9670](https://github.com/nautobot/nautobot/issues/9670) - Replaced dependency `drf-spectacular-sidecar` with the `swagger-ui-dist` and `redoc` NPM packages, bundled into Nautobot's static files, for the Swagger UI and Redoc REST API documentation pages. Static files under `drf_spectacular_sidecar/` are no longer available to apps or custom templates.
- [#9670](https://github.com/nautobot/nautobot/issues/9670) - Updated Swagger UI to version 5.34.0.

### Documentation in v3.3.0a0

- [#9416](https://github.com/nautobot/nautobot/issues/9416) - Added initial documentation for CSV/JSON/YAML import/export functionality as enhanced in v3.3.
- [#9428](https://github.com/nautobot/nautobot/issues/9428) - Added documentation for the `humanize_duration` template filter.
- [#9448](https://github.com/nautobot/nautobot/issues/9448) - Added documentation for the `export_fields` parameter when exporting records to JSON, YAML, or CSV.
- [#9455](https://github.com/nautobot/nautobot/issues/9455) - Added [Conditions](../user-guide/feature-guides/conditions.md) documentation.
- [#9521](https://github.com/nautobot/nautobot/issues/9521) - Added documentation of conditions to the [Webhooks](../user-guide/platform-functionality/webhook.md) and [Job Hooks](../user-guide/platform-functionality/jobs/jobhook.md) pages.
- [#9521](https://github.com/nautobot/nautobot/issues/9521) - Documented what happens when a condition cannot be checked, in [Conditions](../user-guide/feature-guides/conditions.md).
- [#9576](https://github.com/nautobot/nautobot/issues/9576) - Added notes about form-field `placeholder` values and the use of Select2 widgets to the core developer documentation.
- [#9587](https://github.com/nautobot/nautobot/issues/9587) - Documented what an export contains when no fields are selected.
- [#9603](https://github.com/nautobot/nautobot/issues/9603) - Improved the conditions guide and removed the note about the dry run, which is not available yet.
- [#9638](https://github.com/nautobot/nautobot/issues/9638) - Added documentation for rate limiting.
- [#9638](https://github.com/nautobot/nautobot/issues/9638) - Added documentation for request performance measurements.

### Housekeeping in v3.3.0a0

- [#9111](https://github.com/nautobot/nautobot/issues/9111) - Refactored IPAddress model related UI views to use `NautobotUIViewSet`.
- [#9315](https://github.com/nautobot/nautobot/issues/9315) - Updated development dependency `django-debug-toolbar` to `~7.1.1`.
- [#9315](https://github.com/nautobot/nautobot/issues/9315) - Updated development dependency `time-machine` to `~3.4.0`.
- [#9409](https://github.com/nautobot/nautobot/issues/9409) - Moved the existing Selenium integration tests from `nautobot/<app>/tests/integration/` to `nautobot/<app>/tests/selenium/`.
- [#9457](https://github.com/nautobot/nautobot/issues/9457) - Fixed support for running parallel tests under Python 3.14.
- [#9457](https://github.com/nautobot/nautobot/issues/9457) - Changed the default development environment Python version from 3.13 to 3.14.
- [#9457](https://github.com/nautobot/nautobot/issues/9457) - Updated CI to use Python 3.14 for tests where applicable.
- [#9462](https://github.com/nautobot/nautobot/issues/9462) - Consolidated the duplicated `non_filter_params` declarations and `get_filter_params()` implementations in `ObjectListView`, `ObjectListViewMixin` and the `ExportObjectList` system Job into `nautobot.core.utils.requests.NON_FILTER_PARAMS` and `resolve_filter_params()`.
- [#9469](https://github.com/nautobot/nautobot/issues/9469) - Added `change_has_consumers()`, which answers whether any enabled webhook, job hook, or event broker would act on a given content type and action, so that work done only for those consumers can be skipped.
- [#9470](https://github.com/nautobot/nautobot/issues/9470) - Fixed omission of `pytest` and `playwright` Python packages from the Docker `dev` image.
- [#9479](https://github.com/nautobot/nautobot/issues/9479) - Moved Playwright login out of the auth fixture and into a helper with documentation for using it in a script.
- [#9511](https://github.com/nautobot/nautobot/issues/9511) - Changed Playwright browser contexts to send the `X-Disable-Debug-Toolbar` header, and the development configuration to keep django-debug-toolbar off pages that carry it or when `NAUTOBOT_SHOW_DJDT_TOOLBAR` is set to a falsy value.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated development dependency `faker` to `^40.40.0`.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated development dependency `djlint` to `~1.46.4` and addressed all new warnings.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated development dependency `pylint` to `~4.1.1` and addressed all new warnings.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated development dependency `coverage` to `~7.16.2`.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated development dependency `django-test-migrations` to `~1.7.0`.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated development dependency `time-machine` to `~3.5.1`.
- [#9518](https://github.com/nautobot/nautobot/issues/9518) - Updated development dependency `playwright` to `~1.63.0`.
- [#9519](https://github.com/nautobot/nautobot/issues/9519) - Updated development dependency `django-debug-toolbar` to `~8.0.0`.
- [#9519](https://github.com/nautobot/nautobot/issues/9519) - Updated development dependency `towncrier` to `~26.9.0` and simplified its configuration in `pyproject.toml`.
- [#9520](https://github.com/nautobot/nautobot/issues/9520) - Replaced the Device detail Selenium tests with Playwright tests and added a shared `DetailPage` page object for detail views.
- [#9529](https://github.com/nautobot/nautobot/issues/9529) - Added a Playwright `AuthenticationEnforcedTestCase` and moved the Django test-client view-authentication sweep into `test_views.py` as a unit test.
- [#9542](https://github.com/nautobot/nautobot/issues/9542) - Ported the radio profile bulk edit Selenium test to Playwright.
- [#9547](https://github.com/nautobot/nautobot/issues/9547) - Added support for `invoke tests --no-color` parameter.
- [#9557](https://github.com/nautobot/nautobot/issues/9557) - Replaced the Selenium computed-field tests with a Playwright `ComputedFieldsTestCase`, added tab helpers to the shared `DetailPage`, table-configuration helpers to the shared `ListPage`, and a shared `created_device` fixture.
- [#9562](https://github.com/nautobot/nautobot/issues/9562) - Fixed a nondeterministic ordering in the Object Metadata `assigned_object_type` filter test.
- [#9564](https://github.com/nautobot/nautobot/issues/9564) - Ported the Notes create and update tests from Selenium to Playwright and added `BasePage.expect_flash_message`.
- [#9605](https://github.com/nautobot/nautobot/issues/9605) - Replaced the Dynamic Group create and edit Selenium test with Playwright tests that verify the group's member count after refreshing its members.
- [#9605](https://github.com/nautobot/nautobot/issues/9605) - Ported the Selenium test for "Update Group Assignment for All" on a filtered device list to Playwright.
- [#9605](https://github.com/nautobot/nautobot/issues/9605) - Added a Celery worker to the Playwright CI job so that tests can run jobs started from the UI, such as Refresh Members.
- [#9611](https://github.com/nautobot/nautobot/issues/9611) - Updated development dependency `coverage` to `~7.17.0`.
- [#9611](https://github.com/nautobot/nautobot/issues/9611) - Updated development dependency `djlint` to `~1.47.1`.
- [#9611](https://github.com/nautobot/nautobot/issues/9611) - Updated development dependency `mkdocs-material` to `~9.8.0`.
- [#9611](https://github.com/nautobot/nautobot/issues/9611) - Updated development dependency `playwright` to `~1.64.1`.
- [#9611](https://github.com/nautobot/nautobot/issues/9611) - Updated development dependency `pylint` to `~4.1.3`.
- [#9611](https://github.com/nautobot/nautobot/issues/9611) - Updated development dependency `pytest` to `~9.2.0`.
- [#9611](https://github.com/nautobot/nautobot/issues/9611) - Updated development dependency `pytest-playwright` to `~0.10.0`.
- [#9611](https://github.com/nautobot/nautobot/issues/9611) - Updated development dependency `ruff` to `~0.17.3`.
- [#9611](https://github.com/nautobot/nautobot/issues/9611) - Updated development dependency `time-machine` to `~3.6.0`.
- [#9612](https://github.com/nautobot/nautobot/issues/9612) - Updated development dependency `watchdog` to `~7.0.0`.
- [#9615](https://github.com/nautobot/nautobot/issues/9615) - Ported the Device create test from Selenium to Playwright.
- [#9620](https://github.com/nautobot/nautobot/issues/9620) - Added a Playwright test asserting the Power Utilization panel is not rendered on a device without power components.
- [#9630](https://github.com/nautobot/nautobot/issues/9630) - Added Playwright tests for the conditions editor on the webhook form.
- [#9647](https://github.com/nautobot/nautobot/issues/9647) - Changed the `playwright` dependency group back to optional, so that a plain `poetry install` works on platforms that Playwright does not publish a wheel for, such as Alpine.
- [#9651](https://github.com/nautobot/nautobot/issues/9651) - Set the toast autohide delay to 5 seconds.
- [#9671](https://github.com/nautobot/nautobot/issues/9671) - Replaced the Selenium accessibility tests with their Playwright equivalents, and made the `playwright-test` job a precondition of the `all-tests-passed` CI check.
- [#9774](https://github.com/nautobot/nautobot/issues/9774) - Updated CI tests to run with `--no-color` flag.
