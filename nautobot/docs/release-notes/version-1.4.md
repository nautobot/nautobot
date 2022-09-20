<!-- markdownlint-disable MD012 MD024 -->

# Nautobot v1.4

This document describes all new features and changes in Nautobot 1.4.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Custom Field Extended Filtering ([#1498](https://github.com/nautobot/nautobot/issues/1498))

Objects with custom fields now support [filter lookup expressions](../rest-api/filtering.md#lookup-expressions) for filtering by custom field values, such as `cf_date_field__gte=2022-08-11` to select objects whose `date_field` custom field has a date of 2022-08-11 or later.

#### Custom Field Slugs ([#1962](https://github.com/nautobot/nautobot/issues/1962))

Custom fields now have a distinct `slug` field. The custom field `name` attribute should be considered deprecated, and will be removed in a future major release (see also [#824](https://github.com/nautobot/nautobot/issues/824).) Additionally, the `label` attribute, while currently optional in the database, will become mandatory in that same future release as a consequence. When migrating from an earlier Nautobot release to version 1.4 or later, the `slug` and `label` for all existing custom fields will be automatically populated if not previously defined.

A new version of the `/api/extras/custom-fields/` REST API endpoints has been implemented. By default this endpoint continues to demonstrate the pre-1.4 behavior (`name` required, `slug` and `label` optional; if unspecified, the `slug` and `label` will receive default values based on the provided `name`). A REST API client can request API version 1.4, in which case the updated API will require `slug` and `label` parameters in place of `name`.

Additionally, REST API serialization of custom field data is itself now versioned. For _all_ object endpoints that include custom field data under the `custom_fields` key, REST API versions 1.3 and earlier will continue the previous behavior of indexing the `custom_fields` dictionary by fields' `name` values, but when REST API version 1.4 or later is requested, the `custom_fields` data will be indexed by `slug` instead.

For technical reasons of backwards-compatibility, the database (ORM) and GraphQL interfaces continue to access and store object custom field data exclusively under the `name` key; this will change to use the `slug` in a future major release. Again, watch [#824](https://github.com/nautobot/nautobot/issues/824) for plans in that regard.

#### Custom Tabs in Object Detail Views ([#1000](https://github.com/nautobot/nautobot/issues/1000))

A plugin may now define extra tabs which will be appended to the object view's list of tabs.

You can refer to the [plugin development guide](../plugins/development.md#adding-extra-tabs) on how to add tabs to existing object detail views.

#### Custom Template (CSS, HTML, JavaScript) on Job Forms ([#1865](https://github.com/nautobot/nautobot/issues/1865))

Jobs can now specify a `template_name` property and provide a custom template with additional JavaScript and CSS to help with user input on the Job submission form.

You can refer to the [Job class metadata attribute documentation](../additional-features/jobs.md#template_name) on how to build and define this template.

#### Dynamic Groups Support Additional Models ([#2200](https://github.com/nautobot/nautobot/pull/2200))

Cluster, IP Address, Prefix, and Rack models can now be filtered on in Dynamic Groups and can also support nested or groups of Dynamic Groups. Some fields have been excluded from filtering until a sensible widget can be provided.

#### Dark Mode UI ([#729](https://github.com/nautobot/nautobot/issues/729))

Nautobot's UI now supports dark mode, both explicitly and via browser preference selection.

The "Theme" link in the footer provides a modal popup to select the preferred theme. This preference is saved per browser via `localStorage`.

#### Improved Filter Coverage for DCIM and Virtualization Models

- DCIM: [#1729](https://github.com/nautobot/nautobot/issues/1729)
- Virtualization: [#1735](https://github.com/nautobot/nautobot/issues/1735)

The DCIM, Virtualization FilterSets have been updated with over 150 new filters, including hybrid filters that support filtering on both `pk` and `slug` (or `pk` and `name` where `slug` is not available). A new filter class `NaturalKeyOrPKMultipleChoiceFilter` was added to `nautobot.utilities.filters` to support filtering on multiple fields of a related object.

Please see the documentation on [best practices for mapping model fields to filters](../development/best-practices.md#mapping-model-fields-to-filters) for more information.

#### Job Hooks ([#1878](https://github.com/nautobot/nautobot/issues/1878))

Jobs can now be configured to run automatically when a change event occurs on a Nautobot object. Job hooks associate jobs to content types and actions to run jobs when a create, update or delete action occurs on the selected content type. A new job base class `JobHookReceiver` was introduced that jobs must subclass to be associated with a job hook.

Please see the documentation on [Job Hooks](../models/extras/jobhook.md) for more information.

#### Job Re-Runs ([#1875](https://github.com/nautobot/nautobot/issues/1875))

JobResult records now save the arguments with which the Job was called, allowing for easy re-execution of the Job with the same arguments as before. A "re-run" button has been added to the JobResult list view and detail view.

#### Location Data Model ([#1052](https://github.com/nautobot/nautobot/issues/1052))

To locate network information more precisely than a Site defines, you can now define a hierarchy of Location Types (for example, `Building` ← `Floor` ← `Room`) and then create Locations corresponding to these types within each Site. Data objects such as devices, prefixes, VLAN groups, etc. can thus be mapped or assigned to Location representing a specific building, wing, floor, room, etc. as appropriate to your needs.

!!! info
    At present, Locations fill the conceptual space between the more abstract Region and Site models and the more concrete Rack Group model. In a future Nautobot release, some or all of these other models may be collapsed into Locations. That is to say, in the future you might not deal with Regions and Sites as distinct models, but instead your Location Type hierarchy might include these higher-level categories, becoming something like Country ← City ← Site ← Building ← Floor ← Room.

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

Visit the documentation on [REST API versioning](../rest-api/overview.md#versioning) for more information on using the versioned APIs.

#### NautobotUIViewSet ([#1812](https://github.com/nautobot/nautobot/issues/1812))

New in Nautobot 1.4 is the debut of `NautobotUIViewSet`: A powerful plugin development tool that can save plugin developer hundreds of lines of code compared to using legacy `generic.views`. Using it to gain access to default functionalities previous provided by `generic.views` such as `create()`, `bulk_create()`, `update()`, `partial_update()`, `bulk_update()`, `destroy()`, `bulk_destroy()`, `retrieve()` and `list()` actions.

Note that this ViewSet is catered specifically to the UI, not the API.

Concrete examples on how to use `NautobotUIViewSet` resides in `nautobot.circuits.views`.

Please visit the [plugin development guide on `NautobotViewSet`](../plugins/development.md#nautobotuiviewset) for more information.

#### Notes ([#767](https://github.com/nautobot/nautobot/issues/767))

Primary and Organizational models now support notes. A notes tab has been added to the Object Detail view for all models that inherit the Primary or Organizational base abstract models.

!!! warning
    Any plugin that inherits from one of these two models and uses the `ViewTestCases.PrimaryObjectViewTestCase` or `ViewTestCases.OrganizationalObjectViewTestCase` for their test will need to add the `NotesObjectView` to the objects URLs.

Notes can also be used via the REST API at endpoint `/api/extras/notes/` or per object detail endpoint at the object's nested `/notes/` endpoint.

!!! info
    For implementers of REST API views (core and/or plugins), a new `nautobot.extras.api.views.NautobotModelViewSet` base class has been added. Use of this class ensures that all features from `PrimaryModel` or `OrganizationalModel` are accessible through the API. This includes custom fields and notes.

Please see the on [plugin development guide on Notes](../plugins/development.md#note-url-endpoint) for more details.

### Changed

#### Dynamic Groups of Dynamic Groups ([#1614](https://github.com/nautobot/nautobot/issues/1614))

Dynamic Groups may now be nested in parent/child relationships. The Dynamic Group edit view now has a "Child Groups" tab that allows one to make other Dynamic Groups of the same content type children of the parent group. Any filters provided by the child groups are used to filter the members from the parent group using one of three operators: "Restrict (AND)", "Include (OR)", or "Exclude (NOT)". This allows for logical parenthetical grouping of nested groups by the operator you choose for that child group association to the parent.

!!! warning
    The default behavior of Dynamic Groups with an empty filter (`{}`) has been inverted to include all objects matching the content type by default instead of matching no objects. This was necessary to implement the progressive layering of child filters similarly to how we use filters to reduce desired objects from basic list view filters.

Please see the greatly-expanded documentation on [Dynamic Groups](../models/extras/dynamicgroup.md) for more information.

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
    Setting [`STRICT_FILTERING`](../configuration/optional-settings.md#strict_filtering) to `False` can result in unexpected filtering results in the case of user error, for example a request to `/api/dcim/devices/?has_primry_ip=false` (note the typo `primry`) will result in a list of all devices, rather than the intended list of only devices that lack a primary IP address. In the case of Jobs or external automation making use of such a filter, this could have wide-ranging consequences.

#### Moved Registry Template Context ([#1945](https://github.com/nautobot/nautobot/issues/1945))

The `settings_and_registry` default context processor was changed to purely `settings` - the (large) Nautobot application registry dictionary is no longer provided as part of the render context for all templates by default. Added a new `registry` template tag that can be invoked by specific templates to provide this variable where needed.

<!-- towncrier release notes start -->
## v1.4.3 (2022-09-19)

### Added

- [#2327](https://github.com/nautobot/nautobot/issues/2327) - Added help text to the Job scheduling datetime picker to indicate the applicable time zone.
- [#2362](https://github.com/nautobot/nautobot/issues/2362) - Added documentation and automation for Nautobot Github project to use `towncrier` for changelog fragments.
- [#2431](https://github.com/nautobot/nautobot/issues/2431) - Add section to the custom field documentation on ORM filtering.

### Changed

- [#1619](https://github.com/nautobot/nautobot/issues/1619) - Updated `drf-spectacular` dependency to version 0.24.
- [#2223](https://github.com/nautobot/nautobot/issues/2223) - Augment `get_route_for_model()` to support REST API routes.
- [#2340](https://github.com/nautobot/nautobot/issues/2340) - Improved rendering of badges, labels, buttons, and color selection menus in dark mode.
- [#2383](https://github.com/nautobot/nautobot/issues/2383) - Updated documentation link for Nautobot ChatOps plugin.
- [#2392](https://github.com/nautobot/nautobot/issues/2392) - Un-group Renovate `next` updates to address code changes per package.
- [#2400](https://github.com/nautobot/nautobot/issues/2400) - Improved formatting of version changes in the documentation.
- [#2417](https://github.com/nautobot/nautobot/issues/2417) - Reworked Docker builds in CI to publish an intermediate "dependencies-only" image to speed up rebuild times.
- [#2447](https://github.com/nautobot/nautobot/issues/2447) - Moved Dynamic Groups tab on object detail view to it's own view as a generic `ObjectDynamicGroupsView`.

### Fixed

- [#138](https://github.com/nautobot/nautobot/issues/138) - Fixed lack of user-facing message when an exception occurs while discovering Jobs from a Git repository.
- [#950](https://github.com/nautobot/nautobot/issues/950) - Fixed database concurrency issues with uWSGI pre-forking.
- [#1619](https://github.com/nautobot/nautobot/issues/1619) - Improved accuracy of OpenAPI schema for bulk REST API operations.
- [#2299](https://github.com/nautobot/nautobot/issues/2299) - Remove `render_filter()` method and `filter` field from table columns
- [#2309](https://github.com/nautobot/nautobot/issues/2309) - Fixed 404 on ScheduledJobView, `job_class` no longer found behavior.
- [#2324](https://github.com/nautobot/nautobot/issues/2324) - Fixed errors encountered when a job model is deleted while a job is running.
- [#2338](https://github.com/nautobot/nautobot/issues/2338) - Fixed whitespace issue with Text File secrets and they are now stripped of leading/trailing whitespace and newlines.
- [#2364](https://github.com/nautobot/nautobot/issues/2364) - Allow `invoke` tasks to be run even if `rich` is not installed.
- [#2378](https://github.com/nautobot/nautobot/issues/2378) - Fix Job Result redirection on submit.
- [#2382](https://github.com/nautobot/nautobot/issues/2382) - Removed extraneous cache and temporary files from the `dev` and `final-dev` Docker images to reduce image size.
- [#2389](https://github.com/nautobot/nautobot/issues/2389) - Removed extraneous `inspect.getsource()` call from Job class.
- [#2407](https://github.com/nautobot/nautobot/issues/2407) - Corrected SSO Backend reference for Azure AD Tenant.
- [#2449](https://github.com/nautobot/nautobot/issues/2449) - CI: Moved dependency build to be a job, not a step.


## v1.4.2 (2022-09-05)

### Added

- [#983](https://github.com/nautobot/nautobot/issues/983) - Added functionalities to specify `args` and `kwargs` to `NavMenuItem`.
- [#2250](https://github.com/nautobot/nautobot/issues/2250) - Added "Stats" and "Rack Groups" to Location detail view, added "Locations" to Site detail view.
- [#2273](https://github.com/nautobot/nautobot/issues/2273) - Added custom markdownlint rule to check for invalid relative links in the documentation.
- [#2307](https://github.com/nautobot/nautobot/issues/2307) - Added `dynamic_groups` field in GraphQL on objects that can belong to dynamic groups.
- [#2314](https://github.com/nautobot/nautobot/pull/2314) - Added `pylint` to linting suite and CI.
- [#2339](https://github.com/nautobot/nautobot/pull/2339) - Enabled and addressed additional `pylint` checkers.
- [#2360](https://github.com/nautobot/nautobot/pull/2360) - Added Django natural key to `extras.Tag`.

### Changed

- [#2011](https://github.com/nautobot/nautobot/issues/2011) - replaced all .format() strings and C format strings with fstrings.
- [#2293](https://github.com/nautobot/nautobot/pull/2293) - Updated GitHub bug report template.
- [#2296](https://github.com/nautobot/nautobot/pull/2296) - Updated `netutils` dependency from 1.1.x to 1.2.x.
- [#2347](https://github.com/nautobot/nautobot/pull/2347) - Revamped documentation look and feel.
- [#2349](https://github.com/nautobot/nautobot/pull/2349) - Docker images are now built with Poetry 1.2.0.
- [#2360](https://github.com/nautobot/nautobot/pull/2360) - Django natural key for Status is now `name` rather than `slug`.
- [#2363](https://github.com/nautobot/nautobot/pull/2363) - Update app icons for consistency
- [#2365](https://github.com/nautobot/nautobot/pull/2365) - Update Network to Code branding name
- [#2367](https://github.com/nautobot/nautobot/pull/2367) - Remove coming soon from projects that exists

### Fixed

- [#449](https://github.com/nautobot/nautobot/issues/449) - Improved error checking and reporting when syncing Git repositories.
- [#1227](https://github.com/nautobot/nautobot/issues/1227) - The NAUTOBOT_DOCKER_SKIP_INIT environment variable can now be set to "false" (case-insensitive),
- [#1807](https://github.com/nautobot/nautobot/issues/1807) - Fixed post_run method fails to add exceptions to job log.
- [#2085](https://github.com/nautobot/nautobot/issues/2085) - The log entries table on a job result page can now be filtered by log level or message and hitting the return key has no effect.
- [#2107](https://github.com/nautobot/nautobot/issues/2107) - Fixed a TypeError when a view defines `action_buttons = None`.
- [#2237](https://github.com/nautobot/nautobot/issues/2237) - Fixed several issues with permissions enforcement for Note creation and viewing.
- [#2268](https://github.com/nautobot/nautobot/pull/2268) - Fixed broken links in documentation.
- [#2269](https://github.com/nautobot/nautobot/issues/2269) - Fixed missing JS code causing rendering errors on GraphQL Query and Rack Reservation detail views.
- [#2278](https://github.com/nautobot/nautobot/issues/2278) - Fixed incorrect permissions check on "Installed Plugins" menu item.
- [#2290](https://github.com/nautobot/nautobot/issues/2290) - Fixed inheritance of ObjectListViewMixin for CircuitTypeUIViewSet.
- [#2311](https://github.com/nautobot/nautobot/issues/2311) - Fixed autopopulation of "Parent" selection when editing an existing Location.
- [#2341](https://github.com/nautobot/nautobot/issues/2341) - Fixed omission of docs from published Python packages.
- [#2342](https://github.com/nautobot/nautobot/issues/2342) - Reduced file size of `nautobot-dev` Docker images by clearing Poetry cache
- [#2350](https://github.com/nautobot/nautobot/issues/2350) - Fixed potential Redis deadlock if Nautobot server restarts at an unfortunate time.

## v1.4.1 (2022-08-22)

### Added

- [#1809](https://github.com/nautobot/nautobot/issues/1809) - Added Django natural key to `extras.Status` to simplify exporting and importing of database dumps for `Status` objects.
- [#2202](https://github.com/nautobot/nautobot/pull/2202) - Added `validate_models` management command to validate each instance in the database.
- [#2213](https://github.com/nautobot/nautobot/issues/2213) - Added a new `--pull` parameter for `invoke build` to tell Docker to pull images when building containers.

### Changed

- [#2206](https://github.com/nautobot/nautobot/issues/2206) - Changed Run button on Job Result to always be displayed, "Re-Run" if available.
- [#2252](https://github.com/nautobot/nautobot/pull/2252) - Updated Poetry install command for Development Getting Started guide.

### Fixed

- [#2209](https://github.com/nautobot/nautobot/issues/2209) - Fixed lack of dark-mode support in GraphiQL page.
- [#2215](https://github.com/nautobot/nautobot/issues/2215) - Fixed error seen in migration from 1.3.x if certain default Statuses had been modified.
- [#2218](https://github.com/nautobot/nautobot/pull/2218) - Fixed typos/links in release notes and Dynamic Groups docs.
- [#2219](https://github.com/nautobot/nautobot/pull/2219) - Fixed broken pagination in Dynamic Group detail "Members" tab.
- [#2220](https://github.com/nautobot/nautobot/pull/2220) - Narrowed scope of auto-formatting in VSCode to only apply to Python files.
- [#2222](https://github.com/nautobot/nautobot/issues/2222) - Fixed missing app headings in Swagger UI.
- [#2229](https://github.com/nautobot/nautobot/issues/2229) - Fixed `render_form.html` include template to not render a duplicate `object_note` field.
- [#2232](https://github.com/nautobot/nautobot/issues/2232) - Fixed incorrect API URLs and incorrect inclusion of Circuits UI URLs in Swagger UI.
- [#2241](https://github.com/nautobot/nautobot/issues/2241) - Fixed `DynamicGroup.objects.get_for_model()` to support nested Dynamic Groups.
- [#2259](https://github.com/nautobot/nautobot/issues/2259) - Fixed footer not bound to bottom of Device View.

## v1.4.0 (2022-08-15)

### Added

- [#1812](https://github.com/nautobot/nautobot/issues/1812) - Added `NautobotViewSet` and accompanying helper methods, documentation.
- [#2173](https://github.com/nautobot/nautobot/pull/2173) - Added flake8 linting and black formatting settings to vscode workspace settings.
- [#2105](https://github.com/nautobot/nautobot/issues/2105) - Added support for Notes in NautobotBulkEditForm and NautobotEditForm.
- [#2200](https://github.com/nautobot/nautobot/pull/2200) - Added Dynamic Groups support for Cluster, IP Address, Prefix, and Rack.

### Changed

- [#1812](https://github.com/nautobot/nautobot/issues/1812) - Changed Circuit app models to use `NautobotViewSet`s.
- [#2029](https://github.com/nautobot/nautobot/pull/2029) - Updated optional settings docs to call out environment variable only settings.
- [#2176](https://github.com/nautobot/nautobot/pull/2176) - Update invoke task output to use rich formatting, print full Docker Compose commands.
- [#2183](https://github.com/nautobot/nautobot/pull/2183) - Update dependency django to ~3.2.15.
- [#2193](https://github.com/nautobot/nautobot/issues/2193) - Updated Postgres/MySQL `dumpdata` docs to exclude `django_rq` exports.
- [#2200](https://github.com/nautobot/nautobot/pull/2200) - Group of dynamic group membership links now link to the group's membership table view.

### Fixed

- [#1304](https://github.com/nautobot/nautobot/issues/1304) - Fixed incorrect display of connection counts on home page.
- [#1845](https://github.com/nautobot/nautobot/issues/1845) - Fixed not being able to schedule job with 'immediate' schedule via API.
- [#1996](https://github.com/nautobot/nautobot/issues/1996) - Fixed Menu Item `link_text` render on top of buttons.
- [#2178](https://github.com/nautobot/nautobot/issues/2178) - Fixed "invalid filter" error when filtering JobResults in the UI.
- [#2184](https://github.com/nautobot/nautobot/issues/2184) - Fixed job re-run not honoring `has_sensitive_variables`.
- [#2190](https://github.com/nautobot/nautobot/pull/2190) - Fixed tags missing from Location forms.
- [#2191](https://github.com/nautobot/nautobot/pull/2191) - Fix widget for boolean filters fields when generating filter form for a Dynamic Group
- [#2192](https://github.com/nautobot/nautobot/issues/2178) - Fixed job.request removed from job instance in `v1.4.0b1`.
- [#2197](https://github.com/nautobot/nautobot/pull/2197) - Fixed some display issues in the Dynamic Groups detail view.

## v1.4.0rc1 (2022-08-10)

### Added

- [#767](https://github.com/nautobot/nautobot/issues/767) - Added notes field to Primary and Organizational models.
- [#1498](https://github.com/nautobot/nautobot/issues/1498) - Added extended lookup expression filters to custom fields.
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
- [#1614](https://github.com/nautobot/nautobot/issues/1614) - Added support for nesting of Dynamic Groups, allowing inclusion/exclusion rules of sub-group members.
- [#1735](https://github.com/nautobot/nautobot/issues/1735) - Added missing filters to model FilterSets for Virtualization models.
- [#1865](https://github.com/nautobot/nautobot/issues/1865) - Added support for a custom template on Job forms.
- [#1875](https://github.com/nautobot/nautobot/issues/1875) - Add ability to quickly re-submit a previously run `Job` with the same parameters.
- [#1877](https://github.com/nautobot/nautobot/issues/1877) - Add new job base class JobHookReceiver to support triggering job execution from change events.
- [#1878](https://github.com/nautobot/nautobot/issues/1878) - Add job hooks feature.
- [#1883](https://github.com/nautobot/nautobot/issues/1883) - Add ability to filter objects by their relationships into the existing FilterSet.
- [#1884](https://github.com/nautobot/nautobot/issues/1884) - Add ability to set the relationship filter via the filter form.
- [#2035](https://github.com/nautobot/nautobot/pull/2035) - Added change source context to object change context manager.
- [#2051](https://github.com/nautobot/nautobot/issues/2051) - Add changelog url for Relationships.
- [#2061](https://github.com/nautobot/nautobot/pull/2061) - Add draggable child groups to Dynamic Groups edit view in UI, recompute and hide weights.
- [#2072](https://github.com/nautobot/nautobot/pull/2072) - Expand on `query_params` for `ObjectVar` in Jobs documentation.

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
    The  `next` and `develop` branches introduced conflicting migration numbers during the release cycle. This necessitates reordering the migration in `next`. If you installed `v1.4.0a1`, you will need to roll back a migration before upgrading/installing `v1.4.0a2` and newer. If you have not installed `v1.4.0a` this will not be an issue.

    Before upgrading, run: `nautobot-server migrate extras 0033_add__optimized_indexing`. This will revert the reordered migration `0034_configcontextschema__remove_name_unique__create_constraint_unique_name_owner`, which is now number `0035`.

    Perform the Nautobot upgrade as usual and proceed with post-installation migration.

    No data loss is expected as the reordered migration only modified indexing on existing fields.

### Added

- [#1000](https://github.com/nautobot/nautobot/issues/1000) - Object detail views can now have extra UI tabs which are defined by a plugin.
- [#1052](https://github.com/nautobot/nautobot/issues/1052) - Initial prototype implementation of Location data model.
- [#1318](https://github.com/nautobot/nautobot/issues/1318) - Added `nautobot.extras.forms.NautobotBulkEditForm` base class. All bulk-edit forms for models that support both custom fields and relationships now inherit from this class.
- [#1466](https://github.com/nautobot/nautobot/issues/1466) - Plugins can now override views.
- [#1729](https://github.com/nautobot/nautobot/issues/1729) - Add new filter class `NaturalKeyOrPKMultipleChoiceFilter` to `nautobot.utilities.filters`.
- [#1729](https://github.com/nautobot/nautobot/issues/1729) - Add 137 new filters to `nautobot.dcim.filters` FilterSets.
- [#1729](https://github.com/nautobot/nautobot/issues/1729) - Add `cable_terminations` to the `model_features` registry.
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
- [#1833](https://github.com/nautobot/nautobot/pull/1833) - Added `hyperlinked_object` template filter to consistently reference objects in templates.

### Changed

- [#1736](https://github.com/nautobot/nautobot/issues/1736) - `STRICT_FILTERING` setting is added and enabled by default.
- [#1793](https://github.com/nautobot/nautobot/pull/1793) - Added index notes to fields from analysis, relaxed ConfigContextSchema constraint (unique on `name`, `owner_content_type`, `owner_object_id` instead of just `name`).

### Fixed

- [#1815](https://github.com/nautobot/nautobot/issues/1815) - Fix theme link style in footer.
- [#1831](https://github.com/nautobot/nautobot/issues/1831) - Fixed missing `parent_interface` and `bridge` from 1.4 serializer of Interfaces.
- [#1831](https://github.com/nautobot/nautobot/issues/2380) - Fix job from with `approval_required=True` and `has_sensitive_variables=True` can be scheduled.
.
