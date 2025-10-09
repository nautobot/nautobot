# Nautobot v3.0

This document describes all new features and changes in Nautobot 3.0.

## Upgrade Actions

### Administrators

- Job approval permissions have been updated in the UI and API. Approvers must now be granted the `extras.change_approvalworkflowstage` and `extras.view_approvalworkflowstage` permissions, replacing the previous requirement for `extras.approve_job`. This change aligns with updates to the approval workflow implementation and permissions model.
- The `approval_required` field from `extras.Job` model has been removed. This is a breaking change for any custom Jobs or applications that reference this field. This functionality has been replaced by a new approval workflow system. For more information on how the new approach works, see [approval workflow documentation](../user-guide/platform-functionality/approval-workflow.md)
    - If you're upgrading from Nautobot 2.x, a management command named `check_job_approval_status` is available in 2.x to help identify jobs and scheduled jobs that still have `approval_required=True`. Running this command prior to upgrading can help you detect and address these cases by either clearing scheduled jobs or defining approval workflows for Jobs.

### Job Authors & App Developers

- Apps that provide any user interface will likely require updates to account for the [Bootstrap upgrade from v3.4 to v5.3](#bootstrap-upgrade-from-v34-to-v53) described below.
- The Data Compliance feature set from the Data Validation Engine App has been moved directly into core. Import paths that reference `nautobot_data_validation_engine.custom_validators.DataComplianceRule` or `nautobot_data_validation_engine.custom_validators.ComplianceError` should be updated to `nautobot.apps.models.DataComplianceRule` and `nautobot.apps.models.ComplianceError`, respectively.
- Code that calls the GraphQL `execute_query()` and `execute_saved_query()` functions may need to be updated to account for changes to the response object returned by these APIs. Specifically, the `response.to_dict()` method is no longer supported, but instead the returned data and any errors encountered may now be accessed directly as `response.data` and `response.errors` respectively.
- Filtering data that supports a `type` filter in the REST API now also supports a corresponding `type` filter in GraphQL. (In Nautobot v2.x and earlier, the filter had to be referenced in GraphQL as `_type` instead.) Filtering by `_type` is still supported where applicable but should be considered deprecated; please update your GraphQL queries accordingly.
- As a part of adding support for associating a [Device to multiple Clusters](#device-to-multiple-clusters-7203), the Device REST API no longer supports a `cluster` field; the field has been renamed to `clusters` and is now a list of related Clusters rather than a single record. See below for more details.

## Release Overview

### Added

#### UI Updates

Nautobot 3.0 introduces a refreshed user interface, building on the migration from Bootstrap 3 to Bootstrap 5 with several major enhancements:

#### Search

The search experience has been completely reimagined. A single, always-available search bar is now present throughout the application, accessible via `Ctrl+K` or `Command+K`. Advanced search syntax, such as `in:<model name>`, allows you to target specific models directly. The search results page now provides clearer visibility into active search parameters and makes it easy to distinguish between basic and advanced queries.

#### Saved Views

Saved Views have been improved to display their type more prominently, making it easier to identify when a Saved View is active and to understand the filters or configurations being applied. This streamlines workflows and reduces confusion when working with complex data sets.

#### Navigation Bar

The Navigation Bar has been redesigned for greater efficiency and usability. It now features support for marking items as favorites, incorporates intuitive icons, and uses a modern flyout design to maximize space and accessibility. Navigation is more consolidated, helping users quickly find and access key areas of Nautobot.

#### VPN Models

TODO: Fill in

#### Device Uniqueness Flexibility

TODO: Fill in

#### Approval Workflow

[Approval Workflows](../user-guide/platform-functionality/approval-workflow.md) allows for a multi-stage review and approval of processes before making changes, running or creating specific objects in the system. They are defined in advance and attached to specific models based on certain constraints. Use cases include:

- Preventing accidental deletion of critical data by requiring manager approval before deletion jobs run.
- Requiring security team sign-off before enabling network changes in production.
- Ensuring multiple stakeholders approve large-scale bulk edits.
- Mandating peer review for scheduled jobs that affect multiple systems.

#### Data Validation Engine

The [Nautobot Data Validation Engine](../user-guide/platform-functionality/data-validation.md) functionality previously provided as a separate Nautobot App has been migrated into Nautobot as a core feature.

The data validation engine offers a set of user definable rules which are used to enforce business constraints on the data in Nautobot. These rules are tied to models and each rule is meant to enforce one aspect of a business use case.

Supported rule types include:

- Regular expression
- Min/max value
- Required fields
- Unique values

Additionally Data Compliance allows you to create validations on your data without actually enforcing them and easily convert them to enforcements once all of your data is compliant.

#### ECharts

[ECharts](https://echarts.apache.org/en/index.html) is now included in the base image, with abstractions provided to easily add [custom charts using ECharts](../user-guide/platform-functionality/echarts.md).

#### GraphQL

You will notice a fresh new look for the GraphiQL interface, which has been upgraded to version 2.4.7. This update brings a modernized UI, improved usability, and better alignment with Nautobot's theming. Most user workflows remain unchanged, but you may find enhanced features such as improved query editing, autocompletion, and response formatting.

### Changed

#### Bootstrap upgrade from v3.4 to v5.3

Nautobot now uses Bootstrap v5.3 as its underlying theming and layout engine. The base Nautobot UI has been refreshed accordingly. Apps will generally require corresponding updates for their UI to render properly. The impact of this upgrade will be much reduced if the App has already adopted the [UI Component Framework](../development/apps/migration/ui-component-framework/index.md) introduced previously in Nautobot v2.4. A [migration script](../development/apps/migration/from-v2/upgrading-from-bootstrap-v3-to-v5.md#migration-script) is included in Nautobot 3.x to automate many of the HTML and CSS updates for App developers.

#### Device to Multiple Clusters ([#7203](https://github.com/nautobot/nautobot/issues/7203))

The Device model has replaced its single `cluster` foreign-key field with a many-to-many `clusters` field, allowing multiple Clusters to be associatd with a single Device.

To provide a modicum of backwards-compatibility, the Device model and queryset still support a singular `cluster` property which can be retrieved and (in some cases) set for the case of a single associated Cluster, but App authors, Job Authors, and GraphQL users are encouraged to migrate to using `clusters` as soon as possible. The `cluster` property will raise a `MultipleObjectsReturned` exception if the Device in question has more than one associated Cluster.

Note that due to technical limitations, the Device REST API does *not* support a `cluster` field in Nautobot v3, so users of the REST API *must* migrate to reading the `clusters` field where applicable. Assignment of Devices to Clusters via the REST API is now managed via a dedicated endpoint `/api/dcim/device-cluster-assignments/` similar to other many-to-many fields in Nautobot.

### Removed

#### Button on Navbar

Buttons were removed from the NavBar as our research indicated they were infrequently used and caused clutter.

#### Job Approval Process

The Job Approval process was removed and replaced by Workflow Approvals.

### Dependencies

#### GraphQL and GraphiQL Updates

The underlying GraphQL libraries (`graphene`, `graphene-django`, `graphene-django-optimizer`) used by Nautobot have been updated to new major versions, including a new major version of the GraphiQL UI. For the most part this upgrade will be seamless to end users, but the response object returned by Nautobot's `execute_query()` and `execute_saved_query()` Python APIs has changed type -- see [Upgrade Actions](#upgrade-actions) above for specifics.

#### Added Python 3.13 Support and Removed Python 3.9 Support

As Python 3.9 has reached end-of-life, Nautobot 3.0 requires a minimum of Python 3.10. Python 3.13 support was added.

#### Added Echarts

Added the JavaScript Library ECharts version 6.0.0.

<!-- pyml disable-num-lines 2 blanks-around-headers -->

<!-- towncrier release notes start -->

## v3.0.0a2 (2025-10-07)

!!! note
    v3.0.0a1 was inadvertently not published to PyPI and Docker image registries. v3.0.0a2 does not contain any changes to Nautobot code compared to v3.0.0a1, but should fix the publishing failure.

### Housekeeping in v3.0.0a2

- [#7928](https://github.com/nautobot/nautobot/issues/7928) - Enhanced `release` GitHub Actions workflow to include prereleases and removed outdated `prerelease` workflow.

## v3.0.0a1 (2025-10-06)

### Added in v3.0.0a1

- [#1889](https://github.com/nautobot/nautobot/issues/1889) - Added `nautobot.apps.filters.ModelMultipleChoiceFilter` filterset filter class, which is a subclass of `django_filters.ModelMultipleChoiceFilter` with a few enhancements. This is now the default filter class for foreign-key, many-to-many, and one-to-one fields when defining a FilterSet with `fields = '__all__'`.
- [#6814](https://github.com/nautobot/nautobot/issues/6814) - Implemented base Nautobot Bootstrap 5 theme.
- [#6866](https://github.com/nautobot/nautobot/issues/6866) - Migrated the Nautobot Data Validation Engine App into Nautobot Core.
- [#6876](https://github.com/nautobot/nautobot/issues/6876) - Added `DataValidationFormMixin` to indicate on the forms that fields are required due to `RequiredValidationRule` set.
- [#6946](https://github.com/nautobot/nautobot/issues/6946) - Implemented v3 UI global footer.
- [#6946](https://github.com/nautobot/nautobot/issues/6946) - Implemented v3 UI global header.
- [#6947](https://github.com/nautobot/nautobot/issues/6947) - Implemented base v3 UI sidenav.
- [#6999](https://github.com/nautobot/nautobot/issues/6999) - Added a data migration to update the `module_name` of jobs provided by Nautobot Data Validation Engine.
- [#7063](https://github.com/nautobot/nautobot/issues/7063) - Added initial Approval Workflow related models, UI, and API.
- [#7068](https://github.com/nautobot/nautobot/issues/7068) - Added a possibility to set/unset navbar items as favorite and display them in separate navbar flyout.
- [#7079](https://github.com/nautobot/nautobot/issues/7079) - Implemented v3 UI sidenav flyouts.
- [#7117](https://github.com/nautobot/nautobot/issues/7117) - Added support for running Jobs under branches when the Nautobot Version Control app is installed.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Added support for job approvals via approval workflows.
- [#7135](https://github.com/nautobot/nautobot/issues/7135) - Added state transition logic for Approval Workflow related models.
- [#7136](https://github.com/nautobot/nautobot/issues/7136) - Added callbacks to called when a workflow has been initiated, approved or rejected.
- [#7136](https://github.com/nautobot/nautobot/issues/7136) - Added `begin_approval_workflow` to `ApprovableModelMixin` to can use it in save method of models which inherit from `ApprovableModelMixin`.
- [#7136](https://github.com/nautobot/nautobot/issues/7136) - Added ObjectManager with `find_for_model` method in `ApprovalWorkflowDefinition`.
- [#7136](https://github.com/nautobot/nautobot/issues/7136) - Added ApprovalWorkflow table to `ScheduledJobView`.
- [#7142](https://github.com/nautobot/nautobot/issues/7142) - Implemented tabs collapsing behavior.
- [#7171](https://github.com/nautobot/nautobot/issues/7171) - Added data migration to copy existing Nautobot Data Validation Engine app data into the new core Data Validation tables.
- [#7177](https://github.com/nautobot/nautobot/issues/7177) - Implemented Approval Workflow related UI.
- [#7180](https://github.com/nautobot/nautobot/issues/7180) - Added Redis cache to `ValidationRule.objects.get_for_model()` to improve performance of repeated lookups.
- [#7180](https://github.com/nautobot/nautobot/issues/7180) - Added `ValidationRule.objects.get_enabled_for_model()` lookup method (with associated Redis cache for performance).
- [#7180](https://github.com/nautobot/nautobot/issues/7180) - Added `GitRepository.objects.get_for_provided_contents()` lookup method (with associated Redis cache for performance).
- [#7186](https://github.com/nautobot/nautobot/issues/7186) - Added ARM64 build target for `nautobot-dev` images under `next` branch CI.
- [#7203](https://github.com/nautobot/nautobot/issues/7203) - Added support for assigning a Device to more than one Cluster.
- [#7203](https://github.com/nautobot/nautobot/issues/7203) - Added support for editing reverse many-to-many relations in bulk edit forms where applicable.
- [#7226](https://github.com/nautobot/nautobot/issues/7226) - Added `configurable` table property to toggle table config button visibility.
- [#7239](https://github.com/nautobot/nautobot/issues/7239) - Added `prettier` as JavaScript on demand source code formatter.
- [#7256](https://github.com/nautobot/nautobot/issues/7256) - Added new API actions under `api/extras/approval-workflow-stages/`: `approve`, `deny`, `comment` and filterset parameter `pending_my_approvals` on the regular list endpoint.
- [#7256](https://github.com/nautobot/nautobot/issues/7256) - Added `users_that_already_denied` property to `ApprovalWorkflowStage` model.
- [#7256](https://github.com/nautobot/nautobot/issues/7256) - Added `associated_approval_workflows` to the `ScheduledJobSerializer` as a read-only list.
- [#7281](https://github.com/nautobot/nautobot/issues/7281) - Added missing flatpickr styles for both light and dark modes.
- [#7301](https://github.com/nautobot/nautobot/issues/7301) - Added support for tables in cards, including collapsible cards.
- [#7364](https://github.com/nautobot/nautobot/issues/7364) - Added pre-check migration (`extras.0125_approval_workflow_pre_check`) to validate data consistency before removing the `approval_required flag` from Job models. The migration aborts with a clear error message if any scheduled jobs still have `approval_required=True`. If any jobs (but not scheduled jobs) still have the flag set, a warning is printed advising to migrate them to the new approval workflow after the upgrade is completed.
- [#7411](https://github.com/nautobot/nautobot/issues/7411) - Implement v3 search UI.
- [#7415](https://github.com/nautobot/nautobot/issues/7415) - Added `hide_in_diff_view` flag to hide `ObjectChange`, `JobLogEntry` and `JobResult` diffs in version control app.
- [#7415](https://github.com/nautobot/nautobot/issues/7415) - Marked users app as not version controlled - `is_version_controlled=False`.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Added the `runnable` property to the ScheduledJob model.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Added the `has_approval_workflow_definition` method to the ScheduledJob model.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Added support for custom approval templates via a new `get_approval_template()` method on models ScheduledJob. This allows objects to override the default approval UI when specific conditions are met (e.g. one-off jobs scheduled in the past).
- [#7538](https://github.com/nautobot/nautobot/issues/7538) - Improved Select2 styling and implemented Multi-badge component.
- [#7642](https://github.com/nautobot/nautobot/issues/7642) - Added Advanced filters tab indicator that it contains some filters visible only in there.
- [#7668](https://github.com/nautobot/nautobot/issues/7668) - Added Approval Workflow documentation.
- [#7668](https://github.com/nautobot/nautobot/issues/7668) - Added User Groups documentation.
- [#7697](https://github.com/nautobot/nautobot/issues/7697) - Created a small internal Nautobot icon library.
- [#7718](https://github.com/nautobot/nautobot/issues/7718) - Added more icons to `nautobot-icons` library: `refresh-cw`, `sliders-vert` and `sliders-vert-2`.
- [#7726](https://github.com/nautobot/nautobot/issues/7726) - Added EChartsBase class. Base definition for an ECharts chart (no rendering logic). This class transforms input data, applies theme colors, and generates a valid ECharts option config.
- [#7726](https://github.com/nautobot/nautobot/issues/7726) - Added `render_echart` as templatetags.
- [#7726](https://github.com/nautobot/nautobot/issues/7726) - Added EChartsPanel class, thank to that ECharts can be used in UI Component.
- [#7736](https://github.com/nautobot/nautobot/issues/7736) - Implemented sidenav branch picker for version control app.
- [#7741](https://github.com/nautobot/nautobot/issues/7741) - Added `nautobot.apps.utils.construct_cache_key()` function for consistent construction of Redis cache keys.
- [#7741](https://github.com/nautobot/nautobot/issues/7741) - Added awareness of Version Control active branch to various Redis caches.
- [#7837](https://github.com/nautobot/nautobot/issues/7837) - Persist sidenav state in cookies and browser local storage.
- [#7839](https://github.com/nautobot/nautobot/issues/7839) - Added block job_form_wrapper to provide additional customization on Custom Job Forms.
- [#7842](https://github.com/nautobot/nautobot/issues/7842) - Added `Canceled` Approval Workflow State.
- [#7842](https://github.com/nautobot/nautobot/issues/7842) - Added `nautobot.apps.choices.ApprovalWorkflowStateChoices`.
- [#7895](https://github.com/nautobot/nautobot/issues/7895) - Added `ObjectApprovalWorkflowView` to `nautobot.apps.views`.
- [#7902](https://github.com/nautobot/nautobot/issues/7902) - Added `nautobot-migrate-bootstrap-v3-to-v5` helper script that can be run by Apps to streamline their migration to Bootstrap v5.x for Nautobot v3.x compatibility.
- [#7902](https://github.com/nautobot/nautobot/issues/7902) - Added additional DjLint rules to flag various cases where HTML templates had not yet been migrated to Bootstrap v5.x compatibility.

### Changed in v3.0.0a1

- [#1889](https://github.com/nautobot/nautobot/issues/1889) - Changed default handling in Nautobot filterset classes (`BaseFilterSet` and subclasses) for foreign-key and one-to-one fields such that they now default to generating a multi-value filter instead of a single-value filter. This may impact the definition of filter-based Dynamic Groups and of Object Permissions that were making use of single-value filters.
- [#1889](https://github.com/nautobot/nautobot/issues/1889) - Changed `NaturalKeyOrPKMultipleChoiceFilter` and its subclasses to inherit from Nautobot's new `ModelMultipleChoiceFilter` class. The primary effect of this change is that the autogenerated label for such filters will be more descriptive.
- [#5745](https://github.com/nautobot/nautobot/issues/5745) - Upgraded the GraphiQL UI from version 1.x to version 2.4.7, including application of Nautobot UI colors to GraphiQL.
- [#5745](https://github.com/nautobot/nautobot/issues/5745) - Changed the return type for the `execute_query` and `execute_saved_query` GraphQL-related Python APIs as a consequence of updating the underlying GraphQL libraries.
- [#6815](https://github.com/nautobot/nautobot/issues/6815) - Updated UI component-based detail views to Bootstrap 5.
- [#6874](https://github.com/nautobot/nautobot/issues/6874) - Increased `name` fields' length to 255 for RegularExpressionValidationRule, MinMaxValidationRule, RequiredValidationRule, and UniqueValidationRule.
- [#6874](https://github.com/nautobot/nautobot/issues/6874) - Specified a Generic Relation from BaseModel class to DataCompliance class so that if an object is deleted, its associated data compliance objects will also be deleted.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Changed `post` method in `JobRunView` to support job approvals via approval workflows.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Changed `post` method in `JobViewSetBase` to support job approvals via approval workflows.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Added `approval_workflow` parameter to `on_workflow_approved`, `on_workflow_initiated` and `on_workflow_denied` methods.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Changed `ScheduledJob.on_workflow_initiated` by adding set `approval_required = True` when workflow was initiated.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Changed `ScheduledJob.on_workflow_approved` by adding set `approved_at` and publishing an approval event when workflow was approved.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Changed `ScheduledJob.create_schedule` method to accept an additional `validated_save` argument, allowing the option to skip saving the scheduled job object to the database.
- [#7171](https://github.com/nautobot/nautobot/issues/7171) - Renamed the new `nautobot.nautobot_data_validation_engine` app to `nautobot.data_validation`.
- [#7171](https://github.com/nautobot/nautobot/issues/7171) - Regenerated the database schema migrations for `nautobot.data_validation` models.
- [#7183](https://github.com/nautobot/nautobot/issues/7183) - Migrate generic object list view to Bootstrap 5.
- [#7203](https://github.com/nautobot/nautobot/issues/7203) - Removed bespoke "Add Devices to Cluster" and "Remove Devices from Cluster" forms/views and added this functionality into the base Cluster edit and bulk-edit forms/views.
- [#7209](https://github.com/nautobot/nautobot/issues/7209) - Move filter form modal to flyout.
- [#7226](https://github.com/nautobot/nautobot/issues/7226) - Moved table config button from top buttons row to table header and table config form from modal to drawer.
- [#7227](https://github.com/nautobot/nautobot/issues/7227) - Migrated Saved Views dropdown menu to drawer.
- [#7239](https://github.com/nautobot/nautobot/issues/7239) - Replaced `yarn` with `npm`.
- [#7256](https://github.com/nautobot/nautobot/issues/7256) - The `approved_at` field from `extras.ScheduleJob` model has been changed to `decision_date`.
- [#7276](https://github.com/nautobot/nautobot/issues/7276) - Moved table action buttons to dropdown menus.
- [#7276](https://github.com/nautobot/nautobot/issues/7276) - Updated all table action button templates to render as dropdown items rather than flat structure buttons.
- [#7316](https://github.com/nautobot/nautobot/issues/7316) - Make Approval Workflow's active stage clearer in the UI.
- [#7333](https://github.com/nautobot/nautobot/issues/7333) - Migrated homepage to Bootstrap 5.
- [#7333](https://github.com/nautobot/nautobot/issues/7333) - Abstracted out draggable API to a generic and reusable form.
- [#7465](https://github.com/nautobot/nautobot/issues/7465) - Move all form buttons to sticky footers.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Simplified `runnable` property logic in the Job model: removed check for `has_sensitive_variable`s and `approval_required`. Now only depends on `enabled` and `installed` flags.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Changed the `post` method in `JobRunView` and the `run` action in `JobViewSetBase` to check for an approval workflow on the scheduled job instead of using `approval_required`.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Changed `extras/job_approval_confirmation.html` to override `extras/approval_workflow/approve.html` for ScheduledJob instances that meet specific conditions, displaying a warning when the job is past its scheduled start time.
- [#7486](https://github.com/nautobot/nautobot/issues/7486) - Changed Prefix table behavior to not show "utilization" by default, as it has significant performance impact when displayed.
- [#7521](https://github.com/nautobot/nautobot/issues/7521) - Updated tabs injected via `{% block extra_tab_content %}` and tabs generated from plugin to match Bootstrap 5 design.
- [#7521](https://github.com/nautobot/nautobot/issues/7521) - Updated `switch_tab` function in integration tests to work with tabs hiding mechanism.
- [#7525](https://github.com/nautobot/nautobot/issues/7525) - Genericize and standardize the way "Collapse/Expand All" buttons work in the app using data-nb-toggle="collapse-all" data attribute.
- [#7551](https://github.com/nautobot/nautobot/issues/7551) - Implement v3 UI design in table filters drawer Basic tab. Refactor some of the existing Select2 forms code.
- [#7587](https://github.com/nautobot/nautobot/issues/7587) - Implemented v3 table advanced filter form,
- [#7602](https://github.com/nautobot/nautobot/issues/7602) - Prefixed following classes with `nb-*`: `table-headings`, `description`, `style-line` and `sidenav-*`.
- [#7619](https://github.com/nautobot/nautobot/issues/7619) - Implemented saved view form new look and feel.
- [#7635](https://github.com/nautobot/nautobot/issues/7635) - Fix sidenav and drawer height to viewport instead of an entire page.
- [#7673](https://github.com/nautobot/nautobot/issues/7673) - Updated table config drawer.
- [#7679](https://github.com/nautobot/nautobot/issues/7679) - Migrated unauthenticated pages to Bootstrap 5.
- [#7738](https://github.com/nautobot/nautobot/issues/7738) - Use Nautobot standard layout (header, sidenav, footer) in special views (Admin, GraphiQL, DRF API docs, Swagger and Redoc).
- [#7741](https://github.com/nautobot/nautobot/issues/7741) - Changed a number of Redis cache keys to be more standardized.
- [#7800](https://github.com/nautobot/nautobot/issues/7800) - Separate `page_title` block from `breadcrumbs` in base Django templates.
- [#7823](https://github.com/nautobot/nautobot/issues/7823) - Updated titles and breadcrumbs for new views with added header like API Docs, GraphiQL, template renderer and user settings.
- [#7832](https://github.com/nautobot/nautobot/issues/7832) - Improved active nav menu items determination logic and moved it from template to context processor.
- [#7832](https://github.com/nautobot/nautobot/issues/7832) - Changed Scheduled Jobs URL path from `/extras/jobs/scheduled-jobs/` to `/extras/scheduled-jobs/`.
- [#7832](https://github.com/nautobot/nautobot/issues/7832) - Restricted nav menu to highlight only one active item at a time.
- [#7842](https://github.com/nautobot/nautobot/issues/7842) - The `has_approval_workflow_definition` method has been moved to `ApprovableModelMixin` from `ScheduledJob` so that it can be used by any model that will be handled by the approval process.
- [#7842](https://github.com/nautobot/nautobot/issues/7842) - Replaced `APPROVAL_WORKFLOW_MODELS` constant with `FeatureQuery` and `populate_model_features_registry`.
- [#7842](https://github.com/nautobot/nautobot/issues/7842) - Changed rendering Approval Workflow tab in ScheduledJob; now renders only when the scheduled job has any associated approval workflows.
- [#7842](https://github.com/nautobot/nautobot/issues/7842) - Flagged Approval Workflows and their various sub-models as non-versionable.
- [#7872](https://github.com/nautobot/nautobot/issues/7872) - Improved Dropdown and Select2 highlighted items visibility.
- [#7892](https://github.com/nautobot/nautobot/issues/7892) - Removed unnecessary and error-prone cache logic from the `PathEndpoint.connected_endpoint` property.
- [#7898](https://github.com/nautobot/nautobot/issues/7898) - Updated Nautobot theme, most notably dark theme color palette and navbar spacings and colors.
- [#7902](https://github.com/nautobot/nautobot/issues/7902) - Ran `nautobot-migrate-bootstrap-v3-to-v5` against all core HTML templates to auto-migrate many remaining Bootstrap 3 CSS classes and HTML structure to Bootstrap 5 equivalents, as well as identifying various CSS/HTML that needed manual updates.
- [#7902](https://github.com/nautobot/nautobot/issues/7902) - Ran updated DjLint rules against all core HTML templates and manually addressed any identified issues not already covered by the `nautobot-migrate-bootstrap-v3-to-v5` script.
- [#7904](https://github.com/nautobot/nautobot/issues/7904) - Refined page header and tree hierarchy UI.

### Removed in v3.0.0a1

- [#6874](https://github.com/nautobot/nautobot/issues/6874) - Removed unused job `DeleteOrphanedDataComplianceData`.
- [#7136](https://github.com/nautobot/nautobot/issues/7136) - Removed `ApprovableModelMixin` inheritance from Job.
- [#7136](https://github.com/nautobot/nautobot/issues/7136) - Removed job from `APPROVAL_WORKFLOW_MODELS`.
- [#7136](https://github.com/nautobot/nautobot/issues/7136) - Removed ApprovalWorkflow table from `JobView`.
- [#7180](https://github.com/nautobot/nautobot/issues/7180) - Removed `wrap_model_clean_methods` and `custom_validator_clean` methods from the `nautobot.apps` namespace as they should only ever be called by Nautobot itself as part of system startup.
- [#7203](https://github.com/nautobot/nautobot/issues/7203) - Removed `cluster` field from Device REST API serializer. `clusters` is available as a read-only field, and assignment of Devices to Clusters via the REST API is now possible via `/api/dcim/device-cluster-assignments/`.
- [#7226](https://github.com/nautobot/nautobot/issues/7226) - Removed `table_config_button_small` Django template tag.
- [#7256](https://github.com/nautobot/nautobot/issues/7256) - Removed actions from `api/extras/scheduled-job/`: approve, deny
- [#7256](https://github.com/nautobot/nautobot/issues/7256) - Removed `approved_by_user` field from `extras.ScheduleJob` model. Now this information is stored in `ApprovalWorkflowStageResponse` model.
- [#7411](https://github.com/nautobot/nautobot/issues/7411) - Remove v2 search.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Removed `approval_required` and `approval_required_override` flags from the Job model and base implementation class.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Removed the `validate` method from `JobSerializer` that checked `approval_required` against `has_sensitive_variables`.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Removed logic from the `clean` method in the Job model that validated `approval_required` against `has_sensitive_variables`.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Removed HTML code related to the `approval_required` field.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Removed `ScheduledJobApprovalQueueListView` and `JobApprovalRequestView` with all relevant files, methods and tests.
- [#7525](https://github.com/nautobot/nautobot/issues/7525) - Removed `accordion-toggle` and `accordion-toggle-all` legacy CSS classes.
- [#7538](https://github.com/nautobot/nautobot/issues/7538) - Removed legacy CSS classes: `filter-container`, `display-inline`, `filter-selection`, `filter-selection-choice`, `filter-selection-choice-remove`, `filter-selection-rendered` and `remove-filter-param`.
- [#7842](https://github.com/nautobot/nautobot/issues/7842) - Removed job specific fields from `ObjectApprovalWorkflowView`.

### Fixed in v3.0.0a1

- [#7117](https://github.com/nautobot/nautobot/issues/7117) - Fixed an exception when rendering Nautobot Version Control app diffs that include GitRepository or JobResult records.
- [#7131](https://github.com/nautobot/nautobot/issues/7131) - Fixed Graphene v3 handling of `description` filters.
- [#7131](https://github.com/nautobot/nautobot/issues/7131) - Restored GraphQL `_type` filters (as aliases of `type` filters) to preserve backwards compatibility with Nautobot v2.x.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Resolved an issue where approval workflows were not correctly fetched due to querying the wrong relationship (`approval_workflow_instances` instead of `associated_approval_workflows`).
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Fixed approvalworkflowdefinition_update templates.
- [#7171](https://github.com/nautobot/nautobot/issues/7171) - Added handling for the ContactAssociation, MetadataType, ObjectMetadata, and Role models to `nautobot.core.utils.migration.migrate_content_type_references_to_new_model`.
- [#7171](https://github.com/nautobot/nautobot/issues/7171) - Renamed the data-validation model database tables to fit within identifier length limits in Dolt and MySQL.
- [#7171](https://github.com/nautobot/nautobot/issues/7171) - Fixed missing "Data Compliance" tab on relevant models.
- [#7180](https://github.com/nautobot/nautobot/issues/7180) - Fixed an issue in which data-validation-engine checks would incorrectly run repeatedly when calling model `clean()`, causing significant performance degradation.
- [#7180](https://github.com/nautobot/nautobot/issues/7180) - Changed data-validation-engine `BaseValidator.clean()` implementation to use cacheable lookup APIs, improving performance of repeated model `clean()` calls.
- [#7259](https://github.com/nautobot/nautobot/issues/7259) - Fixed not working JavaScript build by converting webpack config from CJS to ESM.
- [#7261](https://github.com/nautobot/nautobot/issues/7261) - Fixed JS imports causing Webpack build failures.
- [#7434](https://github.com/nautobot/nautobot/issues/7434) - Fixed Prefix tabs to properly render without HTTP 500.
- [#7434](https://github.com/nautobot/nautobot/issues/7434) - Fixed module bays details to properly render title and breadcrumbs.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Fixed dryrun functionality in post method of JobRunView.
- [#7480](https://github.com/nautobot/nautobot/issues/7480) - Fixed draggable homepage panels on Firefox.
- [#7524](https://github.com/nautobot/nautobot/issues/7524) - Fixed broken theme preview page.
- [#7525](https://github.com/nautobot/nautobot/issues/7525) - Fixed job list view not rendering jobs.
- [#7563](https://github.com/nautobot/nautobot/issues/7563) - Fixed `data_validation.0002` migration to handle a schema difference between the latest Data Validation Engine App and the version in Nautobot core.
- [#7652](https://github.com/nautobot/nautobot/issues/7652) - Fixed missing "Created/Updated" and action buttons on object detail views.
- [#7653](https://github.com/nautobot/nautobot/issues/7653) - Fixed main tab sometimes incorrectly displayed as active in detail view.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Fixed a bug in CSV rendering of VarbinaryIPField values on Dolt.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Fixed a bug in `settings.py` when using `NAUTOBOT_DB_ENGINE=django_prometheus.db.backends.mysql`.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Fixed a bug in Git repository refreshing where a data failure was not correctly detected under Dolt.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Fixed a bug in `get_celery_queues()` caching.
- [#7659](https://github.com/nautobot/nautobot/issues/7659) - Fixed rendering of progress bars under 30%.
- [#7660](https://github.com/nautobot/nautobot/issues/7660) - Fixed a rendering error in `/ipam/prefixes/<uuid>/prefixes/` child-prefixes view.
- [#7707](https://github.com/nautobot/nautobot/issues/7707) - Fixed bug with Job Execution card always fully visible in Run Job form.
- [#7713](https://github.com/nautobot/nautobot/issues/7713) - Fixed broken banner styles.
- [#7719](https://github.com/nautobot/nautobot/issues/7719) - Fixed theme preview example layouts and components.
- [#7721](https://github.com/nautobot/nautobot/issues/7721) - Fixed an issue where the current tab was not highlighted as active.
- [#7740](https://github.com/nautobot/nautobot/issues/7740) - Fixed bug with invalid reference to Nautobot version control branch list URL.
- [#7839](https://github.com/nautobot/nautobot/issues/7839) - Fixed Import Objects form by using `job_form_wrapper` and tabs on the card-header.
- [#7843](https://github.com/nautobot/nautobot/issues/7843) - Fixed white background flash during page load in system dark color mode.
- [#7881](https://github.com/nautobot/nautobot/issues/7881) - Fixed image rendering in echarts and approval workflow md files.
- [#7894](https://github.com/nautobot/nautobot/issues/7894) - Fixed HTML rendering of numbered lists in the approval workflow documentation.
- [#7896](https://github.com/nautobot/nautobot/issues/7896) - Fixed missing action button left border in case when there is only one action button.
- [#7897](https://github.com/nautobot/nautobot/issues/7897) - Fixed non clickable interactive elements in collapsible card headers.
- [#7912](https://github.com/nautobot/nautobot/issues/7912) - Hid sidenav tabs and groups with no items.

### Dependencies in v3.0.0a1

- [#4769](https://github.com/nautobot/nautobot/issues/4769) - Updated GraphiQL UI to version 2.4.7 (the version supported by `graphene-django` 3.2.0).
- [#5745](https://github.com/nautobot/nautobot/issues/5745) - Updated dependencies `graphene-django` to `~3.2.3` and `graphene-django-optimizer` to `~0.10.0`.
- [#7186](https://github.com/nautobot/nautobot/issues/7186) - Updated `netutils` minimum version to 1.12.0 as older versions do not support Python 3.13.
- [#7200](https://github.com/nautobot/nautobot/issues/7200) - Dropped support for Python 3.9. Python 3.10 is now the minimum version required by Nautobot.
- [#7200](https://github.com/nautobot/nautobot/issues/7200) - Added support for Python 3.13. Python 3.13 is now the maximum version required by Nautobot.
- [#7208](https://github.com/nautobot/nautobot/issues/7208) - Updated `select2` dependency to v4.0.13.
- [#7208](https://github.com/nautobot/nautobot/issues/7208) - Added `select2-bootstrap-5-theme` dependency to make `select2` work with `Bootstrap5`
- [#7431](https://github.com/nautobot/nautobot/issues/7431) - Updated dependency `celery` to `~5.5.3`.
- [#7431](https://github.com/nautobot/nautobot/issues/7431) - Removed direct dependency on `kombu` as the newer version of `celery` includes an appropriate dependency.
- [#7675](https://github.com/nautobot/nautobot/issues/7675) - Replaced `mime-support` with `media-types` in Dockerfile dependencies. The `mime-support` package is no longer available in newer Debian-based `python:slim` images (starting with Debian 13 "Trixie"). For the same reason, the `xmlsec` dependency was upgraded to version `1.3.16` to ensure compatibility with the updated build environment.
- [#7680](https://github.com/nautobot/nautobot/issues/7680) - Added dependency on `htmx` npm package.
- [#7680](https://github.com/nautobot/nautobot/issues/7680) - Removed `django-htmx` from the Python dependencies.
- [#7726](https://github.com/nautobot/nautobot/issues/7726) - Added dependency on `echarts` npm package.

### Documentation in v3.0.0a1

- [#7306](https://github.com/nautobot/nautobot/issues/7306) - Create v2.x to v3.0 UI migration guide.
- [#7716](https://github.com/nautobot/nautobot/issues/7716) - Added docs to communicate about configurable columns performance impact.
- [#7726](https://github.com/nautobot/nautobot/issues/7726) - Added documentation about new feature ECharts.
- [#7730](https://github.com/nautobot/nautobot/issues/7730) - Added Involving Scheduled Job Approval example to Approval Workflow documentation.
- [#7741](https://github.com/nautobot/nautobot/issues/7741) - Corrected formatting of autogenerated docs for various items in `nautobot.apps`.
- [#7811](https://github.com/nautobot/nautobot/issues/7811) - Document UI best practices.
- [#7891](https://github.com/nautobot/nautobot/issues/7891) - Fixed a dead link to the Django documentation.
- [#7899](https://github.com/nautobot/nautobot/issues/7899) - Documented additional HTML changes needed in forms when migrating to Nautobot v3 and Bootstrap 5.

### Housekeeping in v3.0.0a1

- [#1889](https://github.com/nautobot/nautobot/issues/1889) - Removed explicit `label` declarations from many filterset filters where the enhanced automatic labeling should suffice.
- [#6874](https://github.com/nautobot/nautobot/issues/6874) - Refactored Nautobot Data Validation Engine code.
- [#7180](https://github.com/nautobot/nautobot/issues/7180) - Added `--print-sql` option to `invoke nbshell`.
- [#7449](https://github.com/nautobot/nautobot/issues/7449) - Fixed CI failures after the merge of #7433.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Cleaned up legacy logic and tests related to deprecated approval flags.
- [#7497](https://github.com/nautobot/nautobot/issues/7497) - Migrate base.css and dark.css files with existing Nautobot styles into new packaging.
- [#7505](https://github.com/nautobot/nautobot/issues/7505) - Added "npm" manager to Renovate configuration.
- [#7523](https://github.com/nautobot/nautobot/issues/7523) - Added `docker-compose.dolt.yml` and supporting files to enable local development and testing against a Dolt database.
- [#7630](https://github.com/nautobot/nautobot/issues/7630) - Added `ui-build-check` step to pull request and integration CI workflows to check UI src and dist files validity and integrity.
- [#7652](https://github.com/nautobot/nautobot/issues/7652) - Added `test_has_timestamps_and_buttons` generic test case to `GetObjectViewTestCase` base test class.
- [#7657](https://github.com/nautobot/nautobot/issues/7657) - Lint JS code.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Refactored Dolt development `Dockerfile-dolt` and `docker-compose.dolt.yml`.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Updated Dolt version in development environment to 1.58.2.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Removed the `doltdb_stuck` tag from test cases previously failing under Dolt.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Updated test and subtest definitions in `nautobot/dcim/tests/test_filters.py` for clarity and efficiency.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Fixed an intermittent test failure in `nautobot.extras.tests.test_filters.ObjectMetadataTestCase`.
- [#7659](https://github.com/nautobot/nautobot/issues/7659) - Added UI rebuild and tooling to development Docker Compose for developer convenience.
- [#7726](https://github.com/nautobot/nautobot/issues/7726) - Updated example app to use related manager names.
- [#7726](https://github.com/nautobot/nautobot/issues/7726) - Updated UI_COLORS names to match values in colors.scss.
- [#7739](https://github.com/nautobot/nautobot/issues/7739) - Add `0.3125rem` (`5px`) spacer.
- [#7773](https://github.com/nautobot/nautobot/issues/7773) - Updated development dependency `coverage` to `~7.10.6`.
- [#7785](https://github.com/nautobot/nautobot/issues/7785) - Added `invoke` commands and renamed existing `npm` commands for frontend development.
- [#7799](https://github.com/nautobot/nautobot/issues/7799) - Fix broken `ui-build-check` CI job.
- [#7884](https://github.com/nautobot/nautobot/issues/7884) - Added legacy button templates usage check to action buttons presence unit test on detail view page.
- [#7885](https://github.com/nautobot/nautobot/issues/7885) - Removed documentation dependency `mkdocs-include-markdown-plugin` as older versions have a security vulnerability and Nautobot core hasn't actually needed this dependency since v2.0.
- [#7911](https://github.com/nautobot/nautobot/issues/7911) - Moved UI source files out of `project-static` to its own dedicated `ui` directory.
