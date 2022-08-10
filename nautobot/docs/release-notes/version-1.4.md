<!-- markdownlint-disable MD024 -->
# Nautobot v1.4

This document describes all new features and changes in Nautobot 1.4.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Custom Field Slugs ([#1962](https://github.com/nautobot/nautobot/issues/1962))

Custom fields now have a distinct `slug` field. The custom field `name` attribute should be considered deprecated, and will be removed in a future major release (see also [#824](https://github.com/nautobot/nautobot/issues/824).) Additionally, the `label` attribute, while currently optional in the database, will become mandatory in that same future release as a consequence. When migrating from an earlier Nautobot release to version 1.4 or later, the `slug` and `label` for all existing custom fields will be automatically populated if not previously defined.

A new version of the `/api/extras/custom-fields/` REST API endpoints has been implemented. By default this endpoint continues to demonstrate the pre-1.4 behavior (`name` required, `slug` and `label` optional; if unspecified, the `slug` and `label` will receive default values based on the provided `name`). A REST API client can request API version 1.4, in which case the updated API will require `slug` and `label` parameters in place of `name`.

Additionally, REST API serialization of custom field data is itself now versioned. For _all_ object endpoints that include custom field data under the `custom_fields` key, REST API versions 1.3 and earlier will continue the previous behavior of indexing the `custom_fields` dictionary by fields' `name` values, but when REST API version 1.4 or later is requested, the `custom_fields` data will be indexed by `slug` instead.

For technical reasons of backwards-compatibility, the database (ORM) and GraphQL interfaces continue to access and store object custom field data exclusively under the `name` key; this will change to use the `slug` in a future major release. Again, watch [#824](https://github.com/nautobot/nautobot/issues/824) for plans in that regard.

#### Custom Template (CSS, HTML, JavaScript) on Job Forms ([#1865](https://github.com/nautobot/nautobot/issues/1865))

Jobs can now specify a `template_name` property and provide a custom template with additional JavaScript and CSS to help with user input on the Job submission form.

You can refer to the [Job class metadata attribute documentation](../additional-features/jobs.md#template_name) on how to build and define this template.

#### Dark Mode UI ([#729](https://github.com/nautobot/nautobot/issues/729))

Nautobot's UI now supports dark mode, both explicitly and via browser preference selection.

The "Theme" link in the footer provides a modal popup to select the preferred theme. This preference is saved per browser via `localStorage`.

#### Improved Filter Coverage for DCIM, Virtualization Models

- DCIM: [#1729](https://github.com/nautobot/nautobot/issues/1729)
- Virtualization: [#1735](https://github.com/nautobot/nautobot/issues/1735)

The DCIM, Virtualization FilterSets have been updated with over 150 new filters, including hybrid filters that support filtering on both `pk` and `slug` (or `pk` and `name` where `slug` is not available). A new filter class `NaturalKeyOrPKMultipleChoiceFilter` was added to `nautobot.utilities.filters` to support filtering on multiple fields of a related object. See the [Best Practices](../development/best-practices/#mapping-model-fields-to-filters) documentation for more information.

#### Job Hooks ([#2103](https://github.com/nautobot/nautobot/pull/2103))

Jobs can now be configured to run automatically when a change event occurs on a Nautobot object. Job hooks associate jobs to content types and actions to run jobs when a create, update or delete action occurs on the selected content type. A new job base class `JobHookReceiver` was introduced that jobs must subclass to be associated with a job hook. See the [Job Hooks](../additional-features/job-hooks/) documentation for more information.

#### Job Re-Runs ([#1875](https://github.com/nautobot/nautobot/issues/1875))

JobResult records now save the arguments with which the Job was called, allowing for easy re-execution of the Job with the same arguments as before. A "re-run" button has been added to the JobResult list view and detail view.

#### Location Data Model ([#1052](https://github.com/nautobot/nautobot/issues/1052))

To locate network information more precisely than a Site defines, you can now define a hierarchy of Location Types (for example, `Building` ← `Floor` ← `Room`) and then create Locations corresponding to these types within each Site. Data objects such as devices, prefixes, VLAN groups, etc. can thus be mapped or assigned to Location representing a specific building, wing, floor, room, etc. as appropriate to your needs.

!!! info
    At present, Locations fill the conceptual space between the more abstract Region and Site models and the more concrete Rack Group model. In a future Nautobot release, some or all of these other models may be collapsed into Locations. That is to say, in the future you might not deal with Regions and Sites as distinct models, but instead your Location Type hierarchy might include these higher-level categories, becoming something like Country ← City ← Site ← Building ← Floor ← Room.

#### Object Detail Tabs ([#1000](https://github.com/nautobot/nautobot/issues/1000))

A plugin may now define extra tabs which will be appended to the object view's list of tabs.

You can refer to the [plugin development guide](../plugins/development.md##adding-extra-tabs) on how to add tabs to existing object detail views.

#### Parent Interfaces and Bridge Interfaces ([#1455](https://github.com/nautobot/nautobot/issues/1455))

Interface and VMInterface models now have `parent_interface` and `bridge` keys. An interface of type `Virtual` can now associate to a parent physical interface on the same device, virtual chassis, or virtual machine, and an interface of any type can specify another interface as its associated bridge interface. (A new `Bridge` interface type has also been added, but the `bridge` interface property is not restricted to interfaces of this type.)

#### Rackview UI - Add Option to Truncate Device Name ([#1119](https://github.com/nautobot/nautobot/issues/1119))

Users can now toggle device full name and truncated name in the rack elevation view. The truncating function is customizable in `nautobot_config.py` via defining `UI_RACK_VIEW_TRUNCATE_FUNCTION`. Default behavior is to split on `.` and return the first item in the list.

"Save SVG" link presents the same view as what is currently displayed on screen

Current preferred toggle state is preserved across tabs (requires refresh) and persists in-browser until local storage is cleared. This presents a consistent behavior when browsing between multiple racks.

#### REST API Enhancements ([#1463](https://github.com/nautobot/nautobot/issues/1463))

- For all models that support Relationships, their corresponding list and detail REST API endpoints now include the option to include data on their associated Relationships and related objects by specifying `include=relationships` as a query parameter.
- Relationship associations on a model can be edited by a PATCH to the appropriate nested value, such as `"relationships" -> <relationship-slug> -> "source"` or `"relationships" -> <relationship-slug> -> "destination"`.
- For implementers of REST API serializers (core and/or plugins), a new `nautobot.extras.api.serializers.NautobotModelSerializer` base class has been added. Using this class guarantees support for relationships, custom fields, and computed fields on the serializer, and provides for a streamlined developer experience.

#### Status Field on Interface, VMInterface Models ([#984](https://github.com/nautobot/nautobot/issues/984))

Interface and VMInterface models now support a status. Default statuses that are available to be set are: Active, Planned, Maintenance, Failed, and Decommissioned. During migration all existing interfaces will be set to the status of "Active".

A new version of the `/dcim/interfaces/*` REST API endpoints have been implemented. By default this endpoint continues to demonstrate the pre-1.4 behavior unless the REST API client explicitly requests API version=1.4. If you continue to use the pre-1.4 API endpoints, status is defaulted to "Active".

Visit the documentation on [REST API versioning](../rest-api/overview/#versioning) for more information on using the versioned APIs.

#### Notes ([#767](https://github.com/nautobot/nautobot/issues/767))

Primary and Organizational models now support notes. A notes tab has been added to the Object Detail view for all models that inherit the Primary or Organizational base abstract models.

!!! warning
    Any plugin that inherits from one of these two models and uses the `ViewTestCases.PrimaryObjectViewTestCase` or `ViewTestCases.OrganizationalObjectViewTestCase` for their test will need to add the `NotesObjectView` to the objects URLs. See [Plugin Development](../plugins/development.md#note-url-endpoint) for more details.

Notes can also be used via the REST API at endpoint `/api/extras/notes` or per object at the object's `/notes` endpoint.

!!! info
    For implementers of REST API views (core and/or plugins), a new `nautobot.extras.api.views.NautobotModelViewSet` base class has been added. Use of this class ensures that all features from `PrimaryModel` or `OrganizationalModel` are accessible through the API. This includes custom fields and notes.

### Changed

#### Dynamic Groups of Dynamic Groups ([#1614](https://github.com/nautobot/nautobot/issues/1614))

Dynamic Groups may now be nested in parent/child relationships. The Dynamic Group edit view now has a "Child Groups" tab that allows one to make other Dynamic Groups of the same content type children of the parent group. Any filters provided by the child groups are used to filter the members from the parent group using one of three operators: "Restrict (AND)", "Include (OR)", or "Exclude (NOT)". This allows for logical parenthetical grouping of nested groups by the operator you choose for that child group association to the parent.

!!! warning
    The default behavior of Dynamic Groups with an empty filter (`{}`) has been inverted to include all objects matching the content type by default instead of matching no objects. This was necessary to implement the progressive layering of child filters similarly to how we use filters to reduce desired objects from basic list view filters.

#### Renamed Mixin Classes ([#2135](https://github.com/nautobot/nautobot/issues/2135))

A number of mixin classes have been renamed for improved self-consistency and clarity of usage. The former names of these mixins are still available for now as aliases, but inheriting from these mixins will raise a `DeprecationWarning`, and these aliases will be removed in a future major release.

| Former Name                 | New Name                            |
| --------------------------- | ----------------------------------- |
| `AddRemoveTagsForm`         | `TagsBulkEditFormMixin`             |
| `CustomFieldBulkCreateForm` | `CustomFieldModelBulkEditFormMixin` |
| `CustomFieldBulkEditForm`   | `CustomFieldModelBulkEditFormMixin` |
| `CustomFieldFilterForm`     | `CustomFieldModelFilterFormMixin`   |
| `CustomFieldModelForm`      | `CustomFieldModelFormMixin`         |
| `RelationshipModelForm`     | `RelationshipModelFormMixin`        |
| `StatusBulkEditFormMixin`   | `StatusModelBulkEditFormMixin`      |
| `StatusFilterFormMixin`     | `StatusModelFilterFormMixin`        |

#### Strict Filter Validation by Default ([#1736](https://github.com/nautobot/nautobot/issues/1736))

Filtering of object lists in the UI and in the REST API will now report an error if an unknown or unrecognized filter parameter is specified. _This is a behavior change from previous Nautobot releases, in which unknown filter parameters would be silently discarded and ignored._

A new configuration setting, [`STRICT_FILTERING`](../configuration/optional-settings.md#strict_filtering) has been added. It defaults to `True`, enabling strict validation of filter parameters, but can be set to `False` to disable this validation.

!!! warning
    Setting `STRICT_FILTERING` to `False` can result in unexpected filtering results in the case of user error, for example a request to `/api/dcim/devices/?has_primry_ip=false` (note the typo `primry`) will result in a list of all devices, rather than the intended list of only devices that lack a primary IP address. In the case of Jobs or external automation making use of such a filter, this could have wide-ranging consequences.

#### Moved Registry Template Context ([#1945](https://github.com/nautobot/nautobot/issues/1945))

The `settings_and_registry` default context processor was changed to purely `settings` - the (large) Nautobot application registry dictionary is no longer provided as part of the render context for all templates by default. Added a new `registry` template tag that can be invoked by specific templates to provide this variable where needed.

## v1.4.0rc1 (2022-08-10)

### Added

- [#1962](https://github.com/nautobot/nautobot/issues/1962) - Added `slug` field to Custom Field model, added 1.4 REST API version of the `api/extras/custom-fields/` endpoints.
- [#2106](https://github.com/nautobot/nautobot/issues/2106) - Added support for listing/creating Notes via REST API.

### Changed

- [#2156](https://github.com/nautobot/nautobot/pull/2156) - Update network automation apps listed on overview of docs.
- [#2168](https://github.com/nautobot/nautobot/pull/2168) - Added model toggle to skip adding missing Dynamic Group filter fields for use in easing integration of new models into Dynamic Groups.

### Fixed

- [#2090](https://github.com/nautobot/nautobot/issues/2090) - Fixed an issue where a REST API PATCH of a Tag could inadvertently reset its associated content-types.
- [#2150](https://github.com/nautobot/nautobot/issues/2150) - Fixed unit tests performance degradation.
- [#2132](https://github.com/nautobot/nautobot/pull/2132) - Updated job hooks to use slugs in urls instead of pk.
- [#2133](https://github.com/nautobot/nautobot/pull/2133) - Update documentation for job hooks, make it reachable from the Nautobot UI.
- [#2135](https://github.com/nautobot/nautobot/issues/2135) - Fixed ImportError on `RelationshipModelForm`, renamed other mixins and added aliases for backwards compatibility.
- [#2137](https://github.com/nautobot/nautobot/issues/2137) - Fixed incorrect parameter name in `NaturalKeyOrPKMultipleChoiceFilter` documentation.
- [#2142](https://github.com/nautobot/nautobot/pull/2142) - Fixed incorrect URL field in REST API nested relationship representation.
- [#2165](https://github.com/nautobot/nautobot/pull/2165) - Fix up relationship-association API test issue.

## v1.4.0b1 (2022-07-30)

### Added

- [#1463](https://github.com/nautobot/nautobot/issues/1463) - Added REST API support for opt-in `relationships` data on model endpoints; added `NautobotModelSerializer` base class.
- [#1614](https://github.com/nautobot/nautobot/issues/1614) - Added support for nesting of Dynamic Groupsallowing inclusion/exclusion rules of sub-group members
- [#1735](https://github.com/nautobot/nautobot/issues/1735) - Added missing filters to model FilterSets for Virtualization models.
- [#1865](https://github.com/nautobot/nautobot/issues/1865) - Added support for a custom template on Job forms.
- [#1877](https://github.com/nautobot/nautobot/issues/1877) - Add new job base class JobHookReceiver to support triggering job execution from change events.
- [#1883](https://github.com/nautobot/nautobot/issues/1883) - Add ability to filter objects by their relationships into the existing FilterSet.
- [#1884](https://github.com/nautobot/nautobot/issues/1884) - Add ability to set the relationship filter via the filter form.
- [#2035](https://github.com/nautobot/nautobot/pull/2035) - Added change source context to object change context manager.
- [#2051](https://github.com/nautobot/nautobot/issues/2051) - Add changelog url for Relationships.
- [#2061](https://github.com/nautobot/nautobot/pulls/2061) - Add draggable child groups to Dynamic Groups edit view in UI, recompute and hide weights.
- [#2103](https://github.com/nautobot/nautobot/pull/2103) - Add job hooks feature.

### Changed

- [#2049](https://github.com/nautobot/nautobot/pull/2049) - Moved `get_changelog_url` to a method on objects that support changelogs, updated template context.
- [#2116](https://github.com/nautobot/nautobot/pull/2116) - Updated package dependencies: Pillow `~9.1.1` -> `~9.2.0`, black `~22.3.0` -> `~22.6.0`, coverage `6.4.1` -> `6.4.2`, django-cacheops `6.0` -> `6.1`, django-cryptography `1.0` -> `1.1`, django-debug-toolbar `~3.4.0` -> `~3.5.0`, django-extensions `~3.1.5` -> `~3.2.0`, drf-yasg `~1.20.0` -> `^1.20.0`, importlib-metadata `~4.4` -> `^4.4.0`, jsonschema `~4.4.0` -> `~4.8.0`, mkdocs `1.3.0` -> `1.3.1`, mkdocs `==1.3.0` -> `==1.3.1`, mkdocs-include-markdown-plugin `~3.2.3` -> `~3.6.0`, mkdocs-include-markdown-plugin `==3.2.3` -> `==3.6.1`, social-auth-core `~4.2.0` -> `~4.3.0`, svgwrite `1.4.2` -> `1.4.3`

### Fixed

- [#1710](https://github.com/nautobot/nautobot/issues/1710) - Fixed invalid CSS when clicking "Add another" row buttons for formsets on Secrets Groups, Dynamic Groups edit view in the UI.
- [#2069](https://github.com/nautobot/nautobot/issues/2069) - Addressed numerous UX improvements for Dynamic Groups of Dynamic Groups feature to ease usability of this feature.
- [#2109](https://github.com/nautobot/nautobot/issues/2109) - Fixed Relationship Filters are not Applied with "And" Operator.
- [#2111](https://github.com/nautobot/nautobot/issues/2111) - Fixed Invalid filter error thrown for `__source` with message: "" is not a valid UUID.

## v1.4.0a2 (2022-07-11)

!!! attention
    `next` and `develop` introduced conflicting migration numbers during the release cycle. This necessitates reordering the migration in `next`. If you installed `v1.4.0a1`, you will need to roll back a migration before upgrading/installing `v1.4.0a2` and newer. If you have not installed `v1.4.0a` this will not be an issue.

    Before upgrading, run: `nautobot-server migrate extras 0033_add__optimized_indexing`. This will revert the reordered migration `0034_configcontextschema__remove_name_unique__create_constraint_unique_name_owner`, which is now number `0035`.

    Perform the Nautobot upgrade as usual and proceed with post-installation migration.

    No data loss is expected as the reordered migration only modified indexing on existing fields.

### Added

- [#1000](https://github.com/nautobot/nautobot/issues/1000) - Object detail views can now have extra UI tabs which are defined by a plugin.
- [#1052](https://github.com/nautobot/nautobot/issues/1052) - Initial prototype implementation of Location data model
- [#1318](https://github.com/nautobot/nautobot/issues/1318) - Added `nautobot.extras.forms.NautobotBulkEditForm` base class. All bulk-edit forms for models that support both custom fields and relationships now inherit from this class.
- [#1466](https://github.com/nautobot/nautobot/issues/1466) - Plugins can now override views.
- [#1729](https://github.com/nautobot/nautobot/issues/1729) - Add new filter class `NaturalKeyOrPKMultipleChoiceFilter` to `nautobot.utilities.filters`.
- [#1729](https://github.com/nautobot/nautobot/issues/1729) - Add 137 new filters to `nautobot.dcim.filters` FilterSets.
- [#1729](https://github.com/nautobot/nautobot/issues/1729) - Add `cable_terminations` to the `model_features` registry.
- [#1875](https://github.com/nautobot/nautobot/issues/1875) - Add ability to quickly re-submit a previously run `Job` with the same parameters.
- [#1893](https://github.com/nautobot/nautobot/issues/1893) - Added an object detail view for Relationships.
- [#1949](https://github.com/nautobot/nautobot/issues/1949) - Added TestCaseMixin for Helper Functions across all test case bases.

### Changed

- [#1908](https://github.com/nautobot/nautobot/pull/1908) - Update dependency Markdown to ~3.3.7
- [#1909](https://github.com/nautobot/nautobot/pull/1909) - Update dependency MarkupSafe to ~2.1.1
- [#1912](https://github.com/nautobot/nautobot/pull/1912) - Update dependency celery to ~5.2.7
- [#1913](https://github.com/nautobot/nautobot/pull/1913) - Update dependency django-jinja to ~2.10.2
- [#1915](https://github.com/nautobot/nautobot/pull/1915) - Update dependency invoke to ~1.7.1
- [#1917](https://github.com/nautobot/nautobot/pull/1917) - Update dependency svgwrite to ~1.4.2
- [#1919](https://github.com/nautobot/nautobot/pull/1919) - Update dependency Pillow to ~9.1.1
- [#1920](https://github.com/nautobot/nautobot/pull/1920) - Update dependency coverage to ~6.4.1
- [#1921](https://github.com/nautobot/nautobot/pull/1921) - Update dependency django-auth-ldap to ~4.1.0
- [#1924](https://github.com/nautobot/nautobot/pull/1924) - Update dependency django-cors-headers to ~3.13.0
- [#1925](https://github.com/nautobot/nautobot/pull/1925) - Update dependency django-debug-toolbar to ~3.4.0
- [#1928](https://github.com/nautobot/nautobot/pull/1928) - Update dependency napalm to ~3.4.1
- [#1929](https://github.com/nautobot/nautobot/pull/1929) - Update dependency selenium to ~4.2.0
- [#1945](https://github.com/nautobot/nautobot/issues/1945) - Change the `settings_and_registry` default context processor to purely `settings`, moving registry dictionary to be accessible via `registry` template tag.
- [#2072](https://github.com/nautobot/nautobot/pull/2072) - Expand on `query_params` for `ObjectVar` in Jobs documentation.

### Fixed

- [#1898](https://github.com/nautobot/nautobot/issues/1898) - Browsable API is now properly styled as the rest of the app.

### Removed

- [#1462](https://github.com/nautobot/nautobot/issues/1462) - Removed job source tab from Job and Job Result view.
- [#2002](https://github.com/nautobot/nautobot/issues/2002) - Removed rqworker container from default Docker development environment.

## v1.4.0a1 (2022-06-13)

### Added

- [#729](https://github.com/nautobot/nautobot/issues/729) - Added UI dark mode.
- [#984](https://github.com/nautobot/nautobot/issues/984) - Added status field to Interface, VMInterface models.
- [#1119](https://github.com/nautobot/nautobot/issues/1119) - Added truncated device name functionality to Rackview UI.
- [#1455](https://github.com/nautobot/nautobot/issues/1455) - Added `parent_interface` and `bridge` fields to Interface and VMInterface models.

### Changed

- [#1736](https://github.com/nautobot/nautobot/issues/1736) - `STRICT_FILTERING` setting is added and enabled by default.
- [#1793](https://github.com/nautobot/nautobot/pull/1793) - Added index notes to fields from analysis, relaxed ConfigContextSchema constraint (unique on `name`, `owner_content_type`, `owner_object_id` instead of just `name`).

### Fixed

- [#1815](https://github.com/nautobot/nautobot/issues/1815) - Fix theme link style in footer.
- [#1831](https://github.com/nautobot/nautobot/issues/1831) - Fixed missing `parent_interface` and `bridge` from 1.4 serializer of Interfaces.
