# Collapse utilities app into core

In version 2.0, we have ported all code from the utilities app to the core app. The following table shows the old import paths and the corresponding new import paths:

| Parent          | Replaced Import Path                                                                 | Replaced With                                                                   |
|-----------------|--------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| Api             | `nautobot.utilities.api.TreeModelSerializerMixin`                                    | `nautobot.core.api.mixins.TreeModelSerializerMixin`                             |
|                 | `nautobot.utilities.api.get_serializer_for_model`                                    | `nautobot.core.api.utils.get_serializer_for_model`                              |
|                 | `nautobot.utilities.api.is_api_request`                                              | `nautobot.core.api.utils.is_api_request`                                        |
|                 | `nautobot.utilities.api.rest_api_server_error`                                       | `nautobot.core.api.utils.rest_api_server_error`                                 |
| Choices         | `nautobot.utilities.choices`                                                         | `nautobot.core.choices`                                                         |
|                 | `nautobot.utilities.choices.ButtonActionColorChoices`                                | `nautobot.core.choices.ButtonActionColorChoices`                                |
|                 | `nautobot.utilities.choices.ButtonActionIconChoices`                                 | `nautobot.core.choices.ButtonActionIconChoices`                                 |
|                 | `nautobot.utilities.choices.ButtonColorChoices`                                      | `nautobot.core.choices.ButtonColorChoices`                                      |
|                 | `nautobot.utilities.choices.ChoiceSet`                                               | `nautobot.core.choices.ChoiceSet`                                               |
|                 | `nautobot.utilities.choices.ColorChoices`                                            | `nautobot.core.choices.ColorChoices`                                            |
| Config          | `nautobot.utilities.config`                                                          | `nautobot.core.utils.get_settings_or_config`                                    |
|                 | `nautobot.utilities.config.get_settings_or_config`                                   | `nautobot.core.utils.get_settings_or_config`                                    |
| Constants       | `nautobot.utilities.constants`                                                       | `nautobot.core.constants`                                                       |
|                 | `nautobot.utilities.constants.FILTER_CHAR_BASED_LOOKUP_MAP`                          | `nautobot.core.constants.FILTER_CHAR_BASED_LOOKUP_MAP`                          |
|                 | `nautobot.utilities.constants.FILTER_NUMERIC_BASED_LOOKUP_MAP`                       | `nautobot.core.constants.FILTER_NUMERIC_BASED_LOOKUP_MAP`                       |
| Deprecation     | `nautobot.utilities.deprecation.class_deprecated_in_favor_of`                        | `nautobot.core.deprecation.class_deprecated_in_favor_of`                        |
| Error_handlers  | `nautobot.utilities.error_handlers.handle_protectederror`                            | `nautobot.core.utils.error_handlers.handle_protectederror`                      |
| Exceptions      | `nautobot.utilities.exceptions`                                                      | `nautobot.core.exceptions`                                                      |
|                 | `nautobot.utilities.exceptions.AbortTransaction`                                     | `nautobot.core.exceptions.AbortTransaction`                                     |
|                 | `nautobot.utilities.exceptions.CeleryWorkerNotRunningException`                      | `nautobot.core.exceptions.CeleryWorkerNotRunningException`                      |
|                 | `nautobot.utilities.exceptions.FilterSetFieldNotFound`                               | `nautobot.core.exceptions.FilterSetFieldNotFound`                               |
| Factory         | `nautobot.utilities.factory.UniqueFaker`                                             | `nautobot.core.factory.UniqueFaker`                                             |
|                 | `nautobot.utilities.factory.get_random_instances`                                    | `nautobot.core.factory.utils.get_random_instances`                              |
|                 | `nautobot.utilities.factory.random_instance`                                         | `nautobot.core.factory.utils.random_instance`                                   |
| Fields          | `nautobot.utilities.fields`                                                          | `nautobot.core.fields`                                                          |
|                 | `nautobot.utilities.fields.ColorField`                                               | `nautobot.core.fields.ColorField`                                               |
|                 | `nautobot.utilities.fields.JSONArrayField`                                           | `nautobot.core.fields.JSONArrayField`                                           |
|                 | `nautobot.utilities.fields.NaturalOrderingField`                                     | `nautobot.core.fields.NaturalOrderingField`                                     |
| Filters         | `nautobot.utilities.filters`                                                         | `nautobot.core.filters`                                                         |
|                 | `nautobot.utilities.filters.BaseFilterSet`                                           | `nautobot.core.filters.BaseFilterSet`                                           |
|                 | `nautobot.utilities.filters.ContentTypeFilter`                                       | `nautobot.core.filters.ContentTypeFilter`                                       |
|                 | `nautobot.utilities.filters.ContentTypeMultipleChoiceFilter`                         | `nautobot.core.filters.ContentTypeMultipleChoiceFilter`                         |
|                 | `nautobot.utilities.filters.MultiValueBigNumberFilter`                               | `nautobot.core.filters.MultiValueBigNumberFilter`                               |
|                 | `nautobot.utilities.filters.MultiValueCharFilter`                                    | `nautobot.core.filters.MultiValueCharFilter`                                    |
|                 | `nautobot.utilities.filters.MultiValueDateFilter`                                    | `nautobot.core.filters.MultiValueDateFilter`                                    |
|                 | `nautobot.utilities.filters.MultiValueMACAddressFilter`                              | `nautobot.core.filters.MultiValueMACAddressFilter`                              |
|                 | `nautobot.utilities.filters.MultiValueNumberFilter`                                  | `nautobot.core.filters.MultiValueNumberFilter`                                  |
|                 | `nautobot.utilities.filters.MultiValueUUIDFilter`                                    | `nautobot.core.filters.MultiValueUUIDFilter`                                    |
|                 | `nautobot.utilities.filters.NameSlugSearchFilterSet`                                 | `nautobot.core.filters.NameSlugSearchFilterSet`                                 |
|                 | `nautobot.utilities.filters.NaturalKeyOrPKMultipleChoiceFilter`                      | `nautobot.core.filters.NaturalKeyOrPKMultipleChoiceFilter`                      |
|                 | `nautobot.utilities.filters.NumericArrayFilter`                                      | `nautobot.core.filters.NumericArrayFilter`                                      |
|                 | `nautobot.utilities.filters.RelatedMembershipBooleanFilter`                          | `nautobot.core.filters.RelatedMembershipBooleanFilter`                          |
|                 | `nautobot.utilities.filters.SearchFilter`                                            | `nautobot.core.filters.SearchFilter`                                            |
|                 | `nautobot.utilities.filters.TagFilter`                                               | `nautobot.core.filters.TagFilter`                                               |
|                 | `nautobot.utilities.filters.TreeNodeMultipleChoiceFilter`                            | `nautobot.core.filters.TreeNodeMultipleChoiceFilter`                            |
| Forms           | `nautobot.utilities.forms`                                                           | `nautobot.core.forms`                                                           |
|                 | `nautobot.utilities.forms.APISelect`                                                 | `nautobot.core.forms.APISelect`                                                 |
|                 | `nautobot.utilities.forms.APISelectMultiple`                                         | `nautobot.core.forms.APISelectMultiple`                                         |
|                 | `nautobot.utilities.forms.BootstrapMixin`                                            | `nautobot.core.forms.BootstrapMixin`                                            |
|                 | `nautobot.utilities.forms.BulkEditForm`                                              | `nautobot.core.forms.BulkEditForm`                                              |
|                 | `nautobot.utilities.forms.BulkEditNullBooleanSelect`                                 | `nautobot.core.forms.BulkEditNullBooleanSelect`                                 |
|                 | `nautobot.utilities.forms.BulkRenameForm`                                            | `nautobot.core.forms.BulkRenameForm`                                            |
|                 | `nautobot.utilities.forms.CSVChoiceField`                                            | `nautobot.core.forms.CSVChoiceField`                                            |
|                 | `nautobot.utilities.forms.CSVContentTypeField`                                       | `nautobot.core.forms.CSVContentTypeField`                                       |
|                 | `nautobot.utilities.forms.CSVDataField`                                              | `nautobot.core.forms.CSVDataField`                                              |
|                 | `nautobot.utilities.forms.CSVFileField`                                              | `nautobot.core.forms.CSVFileField`                                              |
|                 | `nautobot.utilities.forms.CSVModelChoiceField`                                       | `nautobot.core.forms.CSVModelChoiceField`                                       |
|                 | `nautobot.utilities.forms.CSVModelForm`                                              | `nautobot.core.forms.CSVModelForm`                                              |
|                 | `nautobot.utilities.forms.CSVMultipleChoiceField`                                    | `nautobot.core.forms.CSVMultipleChoiceField`                                    |
|                 | `nautobot.utilities.forms.CSVMultipleContentTypeField`                               | `nautobot.core.forms.CSVMultipleContentTypeField`                               |
|                 | `nautobot.utilities.forms.ColorSelect`                                               | `nautobot.core.forms.ColorSelect`                                               |
|                 | `nautobot.utilities.forms.CommentField`                                              | `nautobot.core.forms.CommentField`                                              |
|                 | `nautobot.utilities.forms.ConfirmationForm`                                          | `nautobot.core.forms.ConfirmationForm`                                          |
|                 | `nautobot.utilities.forms.DatePicker`                                                | `nautobot.core.forms.DatePicker`                                                |
|                 | `nautobot.utilities.forms.DatePicker`                                                | `nautobot.core.forms.widgets.DatePicker`                                        |
|                 | `nautobot.utilities.forms.DateTimePicker`                                            | `nautobot.core.forms.DateTimePicker`                                            |
|                 | `nautobot.utilities.forms.DateTimePicker`                                            | `nautobot.core.forms.widgets.DateTimePicker`                                    |
|                 | `nautobot.utilities.forms.DynamicModelChoiceField`                                   | `nautobot.core.forms.DynamicModelChoiceField`                                   |
|                 | `nautobot.utilities.forms.DynamicModelMultipleChoiceField`                           | `nautobot.core.forms.DynamicModelMultipleChoiceField`                           |
|                 | `nautobot.utilities.forms.DynamicModelMultipleChoiceField`                           | `nautobot.core.forms.fields.DynamicModelMultipleChoiceField`                    |
|                 | `nautobot.utilities.forms.ExpandableIPAddressField`                                  | `nautobot.core.forms.ExpandableIPAddressField`                                  |
|                 | `nautobot.utilities.forms.ExpandableNameField`                                       | `nautobot.core.forms.ExpandableNameField`                                       |
|                 | `nautobot.utilities.forms.ImportForm`                                                | `nautobot.core.forms.ImportForm`                                                |
|                 | `nautobot.utilities.forms.JSONField`                                                 | `nautobot.core.forms.JSONField`                                                 |
|                 | `nautobot.utilities.forms.LaxURLField`                                               | `nautobot.core.forms.LaxURLField`                                               |
|                 | `nautobot.utilities.forms.MultipleContentTypeField`                                  | `nautobot.core.forms.CSVMultipleContentTypeField`                               |
|                 | `nautobot.utilities.forms.MultipleContentTypeField`                                  | `nautobot.core.forms.fields.MultipleContentTypeField`                           |
|                 | `nautobot.utilities.forms.NullableDateField`                                         | `nautobot.core.forms.NullableDateField`                                         |
|                 | `nautobot.utilities.forms.NumericArrayField`                                         | `nautobot.core.forms.NumericArrayField`                                         |
|                 | `nautobot.utilities.forms.ReturnURLForm`                                             | `nautobot.core.forms.ReturnURLForm`                                             |
|                 | `nautobot.utilities.forms.SelectWithPK`                                              | `nautobot.core.forms.SelectWithPK`                                              |
|                 | `nautobot.utilities.forms.SlugField`                                                 | `nautobot.core.forms.SlugField`                                                 |
|                 | `nautobot.utilities.forms.SmallTextarea`                                             | `nautobot.core.forms.SmallTextarea`                                             |
|                 | `nautobot.utilities.forms.StaticSelect2`                                             | `nautobot.core.forms.StaticSelect2`                                             |
|                 | `nautobot.utilities.forms.StaticSelect2`                                             | `nautobot.core.forms.widgets.StaticSelect2`                                     |
|                 | `nautobot.utilities.forms.StaticSelect2Multiple`                                     | `nautobot.core.forms.StaticSelect2Multiple`                                     |
|                 | `nautobot.utilities.forms.StaticSelect2Multiple`                                     | `nautobot.core.forms.widgets.StaticSelect2Multiple`                             |
|                 | `nautobot.utilities.forms.TableConfigForm`                                           | `nautobot.core.forms.TableConfigForm`                                           |
|                 | `nautobot.utilities.forms.TagFilterField`                                            | `nautobot.core.forms.TagFilterField`                                            |
|                 | `nautobot.utilities.forms.TimePicker`                                                | `nautobot.core.forms.widgets.DateTimePicker`                                    |
|                 | `nautobot.utilities.forms.add_blank_choice`                                          | `nautobot.core.forms.add_blank_choice`                                          |
|                 | `nautobot.utilities.forms.add_blank_choice`                                          | `nautobot.core.forms.utils.add_blank_choice`                                    |
|                 | `nautobot.utilities.forms.constants.BOOLEAN_WITH_BLANK_CHOICES`                      | `nautobot.core.constants.BOOLEAN_WITH_BLANK_CHOICES`                            |
|                 | `nautobot.utilities.forms.fields.CSVModelChoiceField`                                | `nautobot.core.forms.CSVModelChoiceField`                                       |
|                 | `nautobot.utilities.forms.fields.DynamicModelChoiceField`                            | `nautobot.core.forms.DynamicModelChoiceField`                                   |
|                 | `nautobot.utilities.forms.fields.DynamicModelChoiceField`                            | `nautobot.core.forms.fields.DynamicModelChoiceField`                            |
|                 | `nautobot.utilities.forms.fields.DynamicModelMultipleChoiceField`                    | `nautobot.core.forms.DynamicModelMultipleChoiceField`                           |
|                 | `nautobot.utilities.forms.fields.DynamicModelMultipleChoiceField`                    | `nautobot.core.forms.fields.DynamicModelMultipleChoiceField`                    |
|                 | `nautobot.utilities.forms.fields.MultiMatchModelMultipleChoiceField`                 | `nautobot.core.forms.fields.MultiMatchModelMultipleChoiceField`                 |
|                 | `nautobot.utilities.forms.fields.MultiValueCharField`                                | `nautobot.core.forms.fields.MultiValueCharField`                                |
|                 | `nautobot.utilities.forms.fields.TagFilterField`                                     | `nautobot.core.forms.TagFilterField`                                            |
|                 | `nautobot.utilities.forms.form_from_model`                                           | `nautobot.core.forms.form_from_model`                                           |
|                 | `nautobot.utilities.forms.forms.DynamicFilterFormSet`                                | `nautobot.core.forms.DynamicFilterFormSet`                                      |
|                 | `nautobot.utilities.forms.forms.DynamicFilterFormSet`                                | `nautobot.core.forms.forms.DynamicFilterFormSet`                                |
|                 | `nautobot.utilities.forms.restrict_form_fields`                                      | `nautobot.core.forms.restrict_form_fields`                                      |
|                 | `nautobot.utilities.forms.utils`                                                     | `nautobot.core.forms.utils`                                                     |
|                 | `nautobot.utilities.forms.utils.add_field_to_filter_form_class`                      | `nautobot.core.forms.utils.add_field_to_filter_form_class`                      |
|                 | `nautobot.utilities.forms.widgets`                                                   | `nautobot.core.forms.widgets`                                                   |
|                 | `nautobot.utilities.forms.widgets.APISelectMultiple`                                 | `nautobot.core.forms.widgets.APISelectMultiple`                                 |
|                 | `nautobot.utilities.forms.widgets.DatePicker`                                        | `nautobot.core.forms.DatePicker`                                                |
|                 | `nautobot.utilities.forms.widgets.DateTimePicker`                                    | `nautobot.core.forms.DateTimePicker`                                            |
|                 | `nautobot.utilities.forms.widgets.MultiValueCharInput`                               | `nautobot.core.forms.widgets.MultiValueCharInput`                               |
|                 | `nautobot.utilities.forms.widgets.StaticSelect2`                                     | `nautobot.core.forms.widgets.StaticSelect2`                                     |
|                 | `nautobot.utilities.forms.widgets.TimePicker`                                        | `nautobot.core.forms.DateTimePicker`                                            |
| Git             | `nautobot.utilities.git.GitRepo`                                                     | `nautobot.core.git.GitRepo`                                                     |
|                 | `nautobot.utilities.git.convert_git_diff_log_to_list`                                | `nautobot.core.git.convert_git_diff_log_to_list`                                |
| Logging         | `nautobot.utilities.logging`                                                         | `nautobot.core.utils.logging`                                                   |
|                 | `nautobot.utilities.logging.sanitize`                                                | `nautobot.core.utils.logging.sanitize`                                          |
| Management      | `nautobot.utilities.management.commands`                                             | `nautobot.core.management.commands`                                             |
| Ordering        | `nautobot.utilities.ordering`                                                        | `nautobot.core.ordering`                                                        |
|                 | `nautobot.utilities.ordering.naturalize_interface`                                   | `nautobot.core.ordering.naturalize_interface`                                   |
| Paginator       | `nautobot.utilities.paginator`                                                       | `nautobot.core.paginator`                                                       |
|                 | `nautobot.utilities.paginator.EnhancedPaginator`                                     | `nautobot.core.paginator.EnhancedPaginator`                                     |
|                 | `nautobot.utilities.paginator.get_paginate_count`                                    | `nautobot.core.paginator.get_paginate_count`                                    |
| Permissions     | `nautobot.utilities.permissions.get_permission_for_model`                            | `nautobot.core.permissions.get_permission_for_model`                            |
|                 | `nautobot.utilities.permissions.permission_is_exempt`                                | `nautobot.core.permissions.permission_is_exempt`                                |
|                 | `nautobot.utilities.permissions.resolve_permission`                                  | `nautobot.core.permissions.resolve_permission`                                  |
|                 | `nautobot.utilities.permissions.resolve_permission_ct`                               | `nautobot.core.permissions.resolve_permission_ct`                               |
| Query_functions | `nautobot.utilities.query_functions.CollateAsChar`                                   | `nautobot.core.models.utils.CollateAsChar`                                      |
|                 | `nautobot.utilities.query_functions.EmptyGroupByJSONBAgg`                            | `nautobot.core.models.utils.EmptyGroupByJSONBAgg`                               |
| Querysets       | `nautobot.utilities.querysets`                                                       | `nautobot.core.querysets`                                                       |
|                 | `nautobot.utilities.querysets.RestrictedQuerySet`                                    | `nautobot.core.querysets.RestrictedQuerySet`                                    |
| Tables          | `nautobot.utilities.tables.BaseTable`                                                | `nautobot.core.tables.BaseTable`                                                |
|                 | `nautobot.utilities.tables.BooleanColumn`                                            | `nautobot.core.tables.BooleanColumn`                                            |
|                 | `nautobot.utilities.tables.ButtonsColumn`                                            | `nautobot.core.tables.ButtonsColumn`                                            |
|                 | `nautobot.utilities.tables.ChoiceFieldColumn`                                        | `nautobot.core.tables.ChoiceFieldColumn`                                        |
|                 | `nautobot.utilities.tables.ColorColumn`                                              | `nautobot.core.tables.ColorColumn`                                              |
|                 | `nautobot.utilities.tables.ColoredLabelColumn`                                       | `nautobot.core.tables.ColoredLabelColumn`                                       |
|                 | `nautobot.utilities.tables.ContentTypesColumn`                                       | `nautobot.core.tables.ContentTypesColumn`                                       |
|                 | `nautobot.utilities.tables.CustomFieldColumn`                                        | `nautobot.core.tables.CustomFieldColumn`                                        |
|                 | `nautobot.utilities.tables.LinkedCountColumn`                                        | `nautobot.core.tables.LinkedCountColumn`                                        |
|                 | `nautobot.utilities.tables.RelationshipColumn`                                       | `nautobot.core.tables.RelationshipColumn`                                       |
|                 | `nautobot.utilities.tables.TagColumn`                                                | `nautobot.core.tables.TagColumn`                                                |
|                 | `nautobot.utilities.tables.ToggleColumn`                                             | `nautobot.core.tables.ToggleColumn`                                             |
| Tasks           | `nautobot.utilities.tasks.get_releases`                                              | `nautobot.core.tasks.get_releases`                                              |
| Templatetags    | `nautobot.utilities.templatetags.helpers`                                            | `nautobot.core.templatetags.helpers`                                            |
|                 | `nautobot.utilities.templatetags.helpers.bettertitle`                                | `nautobot.core.templatetags.helpers.bettertitle`                                |
|                 | `nautobot.utilities.templatetags.helpers.render_boolean`                             | `nautobot.core.templatetags.helpers.render_boolean`                             |
|                 | `nautobot.utilities.templatetags.helpers.render_markdown`                            | `nautobot.core.templatetags.helpers.render_markdown`                            |
|                 | `nautobot.utilities.templatetags.helpers.validated_viewname`                         | `nautobot.core.templatetags.helpers.validated_viewname`                         |
| Testing         | `nautobot.utilities.testing`                                                         | `nautobot.core.testing`                                                         |
|                 | `nautobot.utilities.testing.APITestCase`                                             | `nautobot.core.testing.APITestCase`                                             |
|                 | `nautobot.utilities.testing.APITestCase`                                             | `nautobot.core.testing.api.APITestCase`                                         |
|                 | `nautobot.utilities.testing.APIViewTestCases`                                        | `nautobot.core.testing.APIViewTestCases`                                        |
|                 | `nautobot.utilities.testing.APIViewTestCases`                                        | `nautobot.core.testing.api.APIViewTestCases`                                    |
|                 | `nautobot.utilities.testing.CeleryTestCase`                                          | `nautobot.core.testing.CeleryTestCase`                                          |
|                 | `nautobot.utilities.testing.FilterTestCases`                                         | `nautobot.core.testing.FilterTestCases`                                         |
|                 | `nautobot.utilities.testing.ModelViewTestCase`                                       | `nautobot.core.testing.ModelViewTestCase`                                       |
|                 | `nautobot.utilities.testing.TestCase`                                                | `nautobot.core.testing.APITestCase`                                             |
|                 | `nautobot.utilities.testing.TestCase`                                                | `nautobot.core.testing.CeleryTestCase`                                          |
|                 | `nautobot.utilities.testing.TestCase`                                                | `nautobot.core.testing.TestCase`                                                |
|                 | `nautobot.utilities.testing.TestCase`                                                | `nautobot.core.testing.views.TestCase`                                          |
|                 | `nautobot.utilities.testing.TransactionTestCase`                                     | `nautobot.core.testing.TransactionTestCase`                                     |
|                 | `nautobot.utilities.testing.ViewTestCases`                                           | `nautobot.core.testing.APIViewTestCases`                                        |
|                 | `nautobot.utilities.testing.ViewTestCases`                                           | `nautobot.core.testing.ViewTestCases`                                           |
|                 | `nautobot.utilities.testing.api.APITestCase`                                         | `nautobot.core.testing.APITestCase`                                             |
|                 | `nautobot.utilities.testing.api.APITestCase`                                         | `nautobot.core.testing.api.APITestCase`                                         |
|                 | `nautobot.utilities.testing.api.APITransactionTestCase`                              | `nautobot.core.testing.APITransactionTestCase`                                  |
|                 | `nautobot.utilities.testing.api.APIViewTestCases`                                    | `nautobot.core.testing.APIViewTestCases`                                        |
|                 | `nautobot.utilities.testing.api.APIViewTestCases`                                    | `nautobot.core.testing.api.APIViewTestCases`                                    |
|                 | `nautobot.utilities.testing.create_test_user`                                        | `nautobot.core.testing.create_test_user`                                        |
|                 | `nautobot.utilities.testing.disable_warnings`                                        | `nautobot.core.testing.disable_warnings`                                        |
|                 | `nautobot.utilities.testing.extract_form_failures`                                   | `nautobot.core.testing.extract_form_failures`                                   |
|                 | `nautobot.utilities.testing.extract_page_body`                                       | `nautobot.core.testing.extract_page_body`                                       |
|                 | `nautobot.utilities.testing.filters.FilterTestCases`                                 | `nautobot.core.testing.FilterTestCases`                                         |
|                 | `nautobot.utilities.testing.filters.FilterTestCases`                                 | `nautobot.core.testing.filters.FilterTestCases`                                 |
|                 | `nautobot.utilities.testing.integration.SeleniumTestCase`                            | `nautobot.core.testing.integration.SeleniumTestCase`                            |
|                 | `nautobot.utilities.testing.mixins`                                                  | `nautobot.core.testing.mixins`                                                  |
|                 | `nautobot.utilities.testing.mixins.NautobotTestCaseMixin`                            | `nautobot.core.testing.mixins.NautobotTestCaseMixin`                            |
|                 | `nautobot.utilities.testing.post_data`                                               | `nautobot.core.testing.post_data`                                               |
|                 | `nautobot.utilities.testing.run_job_for_testing`                                     | `nautobot.core.testing.run_job_for_testing`                                     |
|                 | `nautobot.utilities.testing.utils.create_test_user`                                  | `nautobot.core.testing.utils.create_test_user`                                  |
|                 | `nautobot.utilities.testing.utils.disable_warnings`                                  | `nautobot.core.testing.disable_warnings`                                        |
|                 | `nautobot.utilities.testing.utils.disable_warnings`                                  | `nautobot.core.testing.utils.disable_warnings`                                  |
|                 | `nautobot.utilities.testing.utils.extract_form_failures`                             | `nautobot.core.testing.utils.extract_form_failures`                             |
|                 | `nautobot.utilities.testing.utils.extract_page_body`                                 | `nautobot.core.testing.extract_page_body`                                       |
|                 | `nautobot.utilities.testing.utils.extract_page_body`                                 | `nautobot.core.testing.utils.extract_page_body`                                 |
|                 | `nautobot.utilities.testing.utils.post_data`                                         | `nautobot.core.testing.post_data`                                               |
|                 | `nautobot.utilities.testing.utils.post_data`                                         | `nautobot.core.testing.utils.post_data`                                         |
|                 | `nautobot.utilities.testing.views`                                                   | `nautobot.core.testing.views`                                                   |
|                 | `nautobot.utilities.testing.views.ModelTestCase`                                     | `nautobot.core.testing.views.ModelTestCase`                                     |
|                 | `nautobot.utilities.testing.views.ModelViewTestCase`                                 | `nautobot.core.testing.ModelViewTestCase`                                       |
|                 | `nautobot.utilities.testing.views.ModelViewTestCase`                                 | `nautobot.core.testing.views.ModelViewTestCase`                                 |
|                 | `nautobot.utilities.testing.views.TestCase`                                          | `nautobot.core.testing.api.APITestCase`                                         |
|                 | `nautobot.utilities.testing.views.ViewTestCases`                                     | `nautobot.core.testing.APIViewTestCases`                                        |
|                 | `nautobot.utilities.testing.views.ViewTestCases`                                     | `nautobot.core.testing.api.APIViewTestCases`                                    |
| Tree_queries    | `nautobot.utilities.tree_queries.TreeModel`                                          | `nautobot.core.models.TreeModel`                                                |
|                 | `nautobot.utilities.tree_queries.TreeModel`                                          | `nautobot.core.models.tree_query.TreeModel`                                     |
|                 | `nautobot.utilities.tree_queries.TreeQuerySet`                                       | `nautobot.core.models.utils.TreeQuerySet`                                       |
| Utils           | `nautobot.utilities.utils`                                                           | `nautobot.core.utils`                                                           |
|                 | `nautobot.utilities.utils.SerializerForAPIVersions`                                  | `nautobot.core.utils.SerializerForAPIVersions`                                  |
|                 | `nautobot.utilities.utils.UtilizationData`                                           | `nautobot.core.utils.UtilizationData`                                           |
|                 | `nautobot.utilities.utils.array_to_string`                                           | `nautobot.core.utils.array_to_string`                                           |
|                 | `nautobot.utilities.utils.convert_querydict_to_factory_formset_acceptable_querydict` | `nautobot.core.utils.convert_querydict_to_factory_formset_acceptable_querydict` |
|                 | `nautobot.utilities.utils.copy_safe_request`                                         | `nautobot.core.utils.copy_safe_request`                                         |
|                 | `nautobot.utilities.utils.count_related`                                             | `nautobot.core.utils.count_related`                                             |
|                 | `nautobot.utilities.utils.csv_format`                                                | `nautobot.core.utils.csv_format`                                                |
|                 | `nautobot.utilities.utils.curry`                                                     | `nautobot.core.utils.curry`                                                     |
|                 | `nautobot.utilities.utils.deepmerge`                                                 | `nautobot.core.utils.deepmerge`                                                 |
|                 | `nautobot.utilities.utils.dict_to_filter_params`                                     | `nautobot.core.utils.dict_to_filter_params`                                     |
|                 | `nautobot.utilities.utils.ensure_content_type_and_field_name_inquery_params`         | `nautobot.core.utils.ensure_content_type_and_field_name_inquery_params`         |
|                 | `nautobot.utilities.utils.flatten_dict`                                              | `nautobot.core.utils.flatten_dict`                                              |
|                 | `nautobot.utilities.utils.flatten_iterable`                                          | `nautobot.core.utils.flatten_iterable`                                          |
|                 | `nautobot.utilities.utils.foreground_color`                                          | `nautobot.core.utils.foreground_color`                                          |
|                 | `nautobot.utilities.utils.get_all_lookup_expr_for_field`                             | `nautobot.core.utils.get_all_lookup_expr_for_field`                             |
|                 | `nautobot.utilities.utils.get_changes_for_model`                                     | `nautobot.core.utils.get_changes_for_model`                                     |
|                 | `nautobot.utilities.utils.get_filterable_params_from_filter_params`                  | `nautobot.core.utils.get_filterable_params_from_filter_params`                  |
|                 | `nautobot.utilities.utils.get_filterset_for_model`                                   | `nautobot.core.utils.get_filterset_for_model`                                   |
|                 | `nautobot.utilities.utils.get_filterset_parameter_form_field`                        | `nautobot.core.utils.get_filterset_parameter_form_field`                        |
|                 | `nautobot.utilities.utils.get_form_for_model`                                        | `nautobot.core.utils.get_form_for_model`                                        |
|                 | `nautobot.utilities.utils.get_route_for_model`                                       | `nautobot.core.utils.get_route_for_model`                                       |
|                 | `nautobot.utilities.utils.get_table_for_model`                                       | `nautobot.core.utils.get_table_for_model`                                       |
|                 | `nautobot.utilities.utils.hex_to_rgb`                                                | `nautobot.core.utils.hex_to_rgb`                                                |
|                 | `nautobot.utilities.utils.is_taggable`                                               | `nautobot.core.utils.is_taggable`                                               |
|                 | `nautobot.utilities.utils.is_uuid`                                                   | `nautobot.core.utils.is_uuid`                                                   |
|                 | `nautobot.utilities.utils.lighten_color`                                             | `nautobot.core.utils.lighten_color`                                             |
|                 | `nautobot.utilities.utils.normalize_querydict`                                       | `nautobot.core.utils.normalize_querydict`                                       |
|                 | `nautobot.utilities.utils.prepare_cloned_fields`                                     | `nautobot.core.utils.prepare_cloned_fields`                                     |
|                 | `nautobot.utilities.utils.pretty_print_query`                                        | `nautobot.core.utils.pretty_print_query`                                        |
|                 | `nautobot.utilities.utils.render_jinja2`                                             | `nautobot.core.utils.render_jinja2`                                             |
|                 | `nautobot.utilities.utils.rgb_to_hex`                                                | `nautobot.core.utils.rgb_to_hex`                                                |
|                 | `nautobot.utilities.utils.serialize_object`                                          | `nautobot.core.utils.serialize_object`                                          |
|                 | `nautobot.utilities.utils.serialize_object_v2`                                       | `nautobot.core.utils.serialize_object_v2`                                       |
|                 | `nautobot.utilities.utils.shallow_compare_dict`                                      | `nautobot.core.utils.shallow_compare_dict`                                      |
|                 | `nautobot.utilities.utils.slugify_dashes_to_underscores`                             | `nautobot.core.utils.slugify_dashes_to_underscores`                             |
|                 | `nautobot.utilities.utils.slugify_dots_to_dashes`                                    | `nautobot.core.utils.slugify_dots_to_dashes`                                    |
|                 | `nautobot.utilities.utils.to_meters`                                                 | `nautobot.core.utils.to_meters`                                                 |
|                 | `nautobot.utilities.utils.versioned_serializer_selector`                             | `nautobot.core.utils.versioned_serializer_selector`                             |
| Validators      | `nautobot.utilities.validators`                                                      | `nautobot.core.validators`                                                      |
|                 | `nautobot.utilities.validators.ExclusionValidator`                                   | `nautobot.core.validators.ExclusionValidator`                                   |
|                 | `nautobot.utilities.validators.validate_regex`                                       | `nautobot.core.validators.validate_regex`                                       |
| Views           | `nautobot.utilities.views.AdminRequiredMixin`                                        | `nautobot.core.views.mixins.AdminRequiredMixin`                                 |
|                 | `nautobot.utilities.views.GetReturnURLMixin`                                         | `nautobot.core.views.mixins.GetReturnURLMixin`                                  |
|                 | `nautobot.utilities.views.ObjectPermissionRequiredMixin`                             | `nautobot.core.views.mixins.ObjectPermissionRequiredMixin`                      |