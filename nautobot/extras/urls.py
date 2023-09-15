from django.urls import path

from nautobot.core.views.routers import NautobotUIViewSetRouter
from nautobot.extras import views
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    CustomField,
    CustomLink,
    DynamicGroup,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    Job,
    JobHook,
    Note,
    Relationship,
    Secret,
    SecretsGroup,
    Status,
    Tag,
    Webhook,
)

app_name = "extras"

router = NautobotUIViewSetRouter()
router.register("job-buttons", views.JobButtonUIViewSet)
router.register("roles", views.RoleUIViewSet)

urlpatterns = [
    # Change logging
    path("object-changes/", views.ObjectChangeListView.as_view(), name="objectchange_list"),
    path("object-changes/<uuid:pk>/", views.ObjectChangeView.as_view(), name="objectchange"),
    # Computed Fields
    path("computed-fields/", views.ComputedFieldListView.as_view(), name="computedfield_list"),
    path("computed-fields/add/", views.ComputedFieldEditView.as_view(), name="computedfield_add"),
    path(
        "computed-fields/delete/",
        views.ComputedFieldBulkDeleteView.as_view(),
        name="computedfield_bulk_delete",
    ),
    path("computed-fields/<uuid:pk>/", views.ComputedFieldView.as_view(), name="computedfield"),
    path(
        "computed-fields/<uuid:pk>/edit/",
        views.ComputedFieldEditView.as_view(),
        name="computedfield_edit",
    ),
    path(
        "computed-fields/<uuid:pk>/delete/",
        views.ComputedFieldDeleteView.as_view(),
        name="computedfield_delete",
    ),
    path(
        "computed-fields/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="computedfield_changelog",
        kwargs={"model": ComputedField},
    ),
    path(
        "computed-fields/<uuid:pk>/notes/",
        views.ObjectNotesView.as_view(),
        name="computedfield_notes",
        kwargs={"model": ComputedField},
    ),
    # Config contexts
    path(
        "config-contexts/",
        views.ConfigContextListView.as_view(),
        name="configcontext_list",
    ),
    path(
        "config-contexts/add/",
        views.ConfigContextEditView.as_view(),
        name="configcontext_add",
    ),
    path(
        "config-contexts/edit/",
        views.ConfigContextBulkEditView.as_view(),
        name="configcontext_bulk_edit",
    ),
    path(
        "config-contexts/delete/",
        views.ConfigContextBulkDeleteView.as_view(),
        name="configcontext_bulk_delete",
    ),
    path(
        "config-contexts/<uuid:pk>/",
        views.ConfigContextView.as_view(),
        name="configcontext",
    ),
    path(
        "config-contexts/<uuid:pk>/edit/",
        views.ConfigContextEditView.as_view(),
        name="configcontext_edit",
    ),
    path(
        "config-contexts/<uuid:pk>/delete/",
        views.ConfigContextDeleteView.as_view(),
        name="configcontext_delete",
    ),
    path(
        "config-contexts/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="configcontext_changelog",
        kwargs={"model": ConfigContext},
    ),
    path(
        "config-contexts/<uuid:pk>/notes/",
        views.ObjectNotesView.as_view(),
        name="configcontext_notes",
        kwargs={"model": ConfigContext},
    ),
    # Config context schema
    path(
        "config-context-schemas/",
        views.ConfigContextSchemaListView.as_view(),
        name="configcontextschema_list",
    ),
    path(
        "config-context-schemas/add/",
        views.ConfigContextSchemaEditView.as_view(),
        name="configcontextschema_add",
    ),
    path(
        "config-context-schemas/edit/",
        views.ConfigContextSchemaBulkEditView.as_view(),
        name="configcontextschema_bulk_edit",
    ),
    path(
        "config-context-schemas/delete/",
        views.ConfigContextSchemaBulkDeleteView.as_view(),
        name="configcontextschema_bulk_delete",
    ),
    path(
        "config-context-schemas/<uuid:pk>/",
        views.ConfigContextSchemaView.as_view(),
        name="configcontextschema",
    ),
    path(
        "config-context-schemas/<uuid:pk>/validation/",
        views.ConfigContextSchemaObjectValidationView.as_view(),
        name="configcontextschema_object_validation",
    ),
    path(
        "config-context-schemas/<uuid:pk>/edit/",
        views.ConfigContextSchemaEditView.as_view(),
        name="configcontextschema_edit",
    ),
    path(
        "config-context-schemas/<uuid:pk>/delete/",
        views.ConfigContextSchemaDeleteView.as_view(),
        name="configcontextschema_delete",
    ),
    path(
        "config-context-schemas/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="configcontextschema_changelog",
        kwargs={"model": ConfigContextSchema},
    ),
    path(
        "config-context-schemas/<uuid:pk>/notes/",
        views.ObjectNotesView.as_view(),
        name="configcontextschema_notes",
        kwargs={"model": ConfigContextSchema},
    ),
    # Custom fields
    path("custom-fields/", views.CustomFieldListView.as_view(), name="customfield_list"),
    path("custom-fields/add/", views.CustomFieldEditView.as_view(), name="customfield_add"),
    path(
        "custom-fields/delete/",
        views.CustomFieldBulkDeleteView.as_view(),
        name="customfield_bulk_delete",
    ),
    path("custom-fields/<uuid:pk>/", views.CustomFieldView.as_view(), name="customfield"),
    path(
        "custom-fields/<uuid:pk>/edit/",
        views.CustomFieldEditView.as_view(),
        name="customfield_edit",
    ),
    path(
        "custom-fields/<uuid:pk>/delete/",
        views.CustomFieldDeleteView.as_view(),
        name="customfield_delete",
    ),
    path(
        "custom-fields/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="customfield_changelog",
        kwargs={"model": CustomField},
    ),
    path(
        "custom-fields/<uuid:pk>/notes/",
        views.ObjectNotesView.as_view(),
        name="customfield_notes",
        kwargs={"model": CustomField},
    ),
    # Custom links
    path("custom-links/", views.CustomLinkListView.as_view(), name="customlink_list"),
    path("custom-links/add/", views.CustomLinkEditView.as_view(), name="customlink_add"),
    path(
        "custom-links/delete/",
        views.CustomLinkBulkDeleteView.as_view(),
        name="customlink_bulk_delete",
    ),
    path("custom-links/<uuid:pk>/", views.CustomLinkView.as_view(), name="customlink"),
    path(
        "custom-links/<uuid:pk>/edit/",
        views.CustomLinkEditView.as_view(),
        name="customlink_edit",
    ),
    path(
        "custom-links/<uuid:pk>/delete/",
        views.CustomLinkDeleteView.as_view(),
        name="customlink_delete",
    ),
    path(
        "custom-links/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="customlink_changelog",
        kwargs={"model": CustomLink},
    ),
    path(
        "custom-links/<uuid:pk>/notes/",
        views.ObjectNotesView.as_view(),
        name="customlink_notes",
        kwargs={"model": CustomLink},
    ),
    # Dynamic Groups
    path("dynamic-groups/", views.DynamicGroupListView.as_view(), name="dynamicgroup_list"),
    path("dynamic-groups/add/", views.DynamicGroupEditView.as_view(), name="dynamicgroup_add"),
    path(
        "dynamic-groups/delete/",
        views.DynamicGroupBulkDeleteView.as_view(),
        name="dynamicgroup_bulk_delete",
    ),
    path("dynamic-groups/<uuid:pk>/", views.DynamicGroupView.as_view(), name="dynamicgroup"),
    path("dynamic-groups/<uuid:pk>/edit/", views.DynamicGroupEditView.as_view(), name="dynamicgroup_edit"),
    path("dynamic-groups/<uuid:pk>/delete/", views.DynamicGroupDeleteView.as_view(), name="dynamicgroup_delete"),
    path(
        "dynamic-groups/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="dynamicgroup_changelog",
        kwargs={"model": DynamicGroup},
    ),
    path(
        "dynamic-groups/<uuid:pk>/notes/",
        views.ObjectNotesView.as_view(),
        name="dynamicgroup_notes",
        kwargs={"model": DynamicGroup},
    ),
    # Export Templates
    path(
        "export-templates/",
        views.ExportTemplateListView.as_view(),
        name="exporttemplate_list",
    ),
    path(
        "export-templates/add/",
        views.ExportTemplateEditView.as_view(),
        name="exporttemplate_add",
    ),
    path(
        "export-templates/delete/",
        views.ExportTemplateBulkDeleteView.as_view(),
        name="exporttemplate_bulk_delete",
    ),
    path(
        "export-templates/<uuid:pk>/",
        views.ExportTemplateView.as_view(),
        name="exporttemplate",
    ),
    path(
        "export-templates/<uuid:pk>/edit/",
        views.ExportTemplateEditView.as_view(),
        name="exporttemplate_edit",
    ),
    path(
        "export-templates/<uuid:pk>/delete/",
        views.ExportTemplateDeleteView.as_view(),
        name="exporttemplate_delete",
    ),
    path(
        "export-templates/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="exporttemplate_changelog",
        kwargs={"model": ExportTemplate},
    ),
    path(
        "export-templates/<uuid:pk>/notes/",
        views.ObjectNotesView.as_view(),
        name="exporttemplate_notes",
        kwargs={"model": ExportTemplate},
    ),
    # Git repositories
    path(
        "git-repositories/",
        views.GitRepositoryListView.as_view(),
        name="gitrepository_list",
    ),
    path(
        "git-repositories/add/",
        views.GitRepositoryEditView.as_view(),
        name="gitrepository_add",
    ),
    path(
        "git-repositories/delete/",
        views.GitRepositoryBulkDeleteView.as_view(),
        name="gitrepository_bulk_delete",
    ),
    path(
        "git-repositories/edit/",
        views.GitRepositoryBulkEditView.as_view(),
        name="gitrepository_bulk_edit",
    ),
    path(
        "git-repositories/import/",
        views.GitRepositoryBulkImportView.as_view(),
        name="gitrepository_import",
    ),
    path(
        "git-repositories/<uuid:pk>/",
        views.GitRepositoryView.as_view(),
        name="gitrepository",
    ),
    path(
        "git-repositories/<uuid:pk>/edit/",
        views.GitRepositoryEditView.as_view(),
        name="gitrepository_edit",
    ),
    path(
        "git-repositories/<uuid:pk>/delete/",
        views.GitRepositoryDeleteView.as_view(),
        name="gitrepository_delete",
    ),
    path(
        "git-repositories/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="gitrepository_changelog",
        kwargs={"model": GitRepository},
    ),
    path(
        "git-repositories/<uuid:pk>/notes/",
        views.ObjectNotesView.as_view(),
        name="gitrepository_notes",
        kwargs={"model": GitRepository},
    ),
    path(
        "git-repositories/<uuid:pk>/result/",
        views.GitRepositoryResultView.as_view(),
        name="gitrepository_result",
    ),
    path(
        "git-repositories/<uuid:pk>/sync/",
        views.GitRepositorySyncView.as_view(),
        name="gitrepository_sync",
    ),
    path(
        "git-repositories/<uuid:pk>/dry-run/",
        views.GitRepositoryDryRunView.as_view(),
        name="gitrepository_dryrun",
    ),
    # GraphQL Queries
    path("graphql-queries/", views.GraphQLQueryListView.as_view(), name="graphqlquery_list"),
    path("graphql-queries/add/", views.GraphQLQueryEditView.as_view(), name="graphqlquery_add"),
    path(
        "graphql-queries/delete/",
        views.GraphQLQueryBulkDeleteView.as_view(),
        name="GraphQLQuery_bulk_delete",
    ),
    path("graphql-queries/<uuid:pk>/", views.GraphQLQueryView.as_view(), name="graphqlquery"),
    path(
        "graphql-queries/<uuid:pk>/edit/",
        views.GraphQLQueryEditView.as_view(),
        name="graphqlquery_edit",
    ),
    path(
        "graphql-queries/<uuid:pk>/delete/",
        views.GraphQLQueryDeleteView.as_view(),
        name="graphqlquery_delete",
    ),
    path(
        "graphql-queries/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="graphqlquery_changelog",
        kwargs={"model": GraphQLQuery},
    ),
    path(
        "graphql-queries/<uuid:pk>/notes/",
        views.ObjectNotesView.as_view(),
        name="graphqlquery_notes",
        kwargs={"model": GraphQLQuery},
    ),
    # Image attachments
    path(
        "image-attachments/<uuid:pk>/edit/",
        views.ImageAttachmentEditView.as_view(),
        name="imageattachment_edit",
    ),
    path(
        "image-attachments/<uuid:pk>/delete/",
        views.ImageAttachmentDeleteView.as_view(),
        name="imageattachment_delete",
    ),
    # Jobs
    path("jobs/", views.JobListView.as_view(), name="job_list"),
    path("jobs/scheduled-jobs/", views.ScheduledJobListView.as_view(), name="scheduledjob_list"),
    path("jobs/scheduled-jobs/<uuid:pk>/", views.ScheduledJobView.as_view(), name="scheduledjob"),
    path("jobs/scheduled-jobs/<uuid:pk>/delete/", views.ScheduledJobDeleteView.as_view(), name="scheduledjob_delete"),
    path(
        "jobs/scheduled-jobs/delete/",
        views.ScheduledJobBulkDeleteView.as_view(),
        name="scheduledjob_bulk_delete",
    ),
    path(
        "jobs/scheduled-jobs/approval-queue/",
        views.ScheduledJobApprovalQueueListView.as_view(),
        name="scheduledjob_approval_queue_list",
    ),
    path(
        "jobs/scheduled-jobs/approval-queue/<uuid:pk>/",
        views.JobApprovalRequestView.as_view(),
        name="scheduledjob_approval_request_view",
    ),
    path(
        "jobs/<uuid:pk>/",
        views.JobView.as_view(),
        name="job",
    ),
    path("jobs/<uuid:pk>/edit/", views.JobEditView.as_view(), name="job_edit"),
    path("jobs/<uuid:pk>/delete/", views.JobDeleteView.as_view(), name="job_delete"),
    path(
        "jobs/<uuid:pk>/changelog/",
        views.JobObjectChangeLogView.as_view(),
        name="job_changelog",
        kwargs={"model": Job},
    ),
    path(
        "jobs/<uuid:pk>/notes/",
        views.JobObjectNotesView.as_view(),
        name="job_notes",
        kwargs={"model": Job},
    ),
    path("jobs/<uuid:pk>/run/", views.JobRunView.as_view(), name="job_run"),
    path("jobs/<str:class_path>/run/", views.JobRunView.as_view(), name="job_run_by_class_path"),
    # Job hooks
    path("job-hooks/", views.JobHookListView.as_view(), name="jobhook_list"),
    path("job-hooks/add/", views.JobHookEditView.as_view(), name="jobhook_add"),
    path(
        "job-hooks/delete/",
        views.JobHookBulkDeleteView.as_view(),
        name="jobhook_bulk_delete",
    ),
    path("job-hooks/<uuid:pk>/", views.JobHookView.as_view(), name="jobhook"),
    path("job-hooks/<uuid:pk>/edit/", views.JobHookEditView.as_view(), name="jobhook_edit"),
    path(
        "job-hooks/<uuid:pk>/delete/",
        views.JobHookDeleteView.as_view(),
        name="jobhook_delete",
    ),
    path(
        "job-hooks/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="jobhook_changelog",
        kwargs={"model": JobHook},
    ),
    # Generic job results
    path("job-results/", views.JobResultListView.as_view(), name="jobresult_list"),
    path("job-results/<uuid:pk>/", views.JobResultView.as_view(), name="jobresult"),
    path("job-results/<uuid:pk>/log-table/", views.JobLogEntryTableView.as_view(), name="jobresult_log-table"),
    path(
        "job-results/delete/",
        views.JobResultBulkDeleteView.as_view(),
        name="jobresult_bulk_delete",
    ),
    path(
        "job-results/<uuid:pk>/delete/",
        views.JobResultDeleteView.as_view(),
        name="jobresult_delete",
    ),
    # Job Button Run
    path("job-button/<uuid:pk>/run/", views.JobButtonRunView.as_view(), name="jobbutton_run"),
    # Notes
    path("notes/add/", views.NoteEditView.as_view(), name="note_add"),
    path("notes/<uuid:pk>/", views.NoteView.as_view(), name="note"),
    path(
        "notes/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="note_changelog",
        kwargs={"model": Note},
    ),
    path("notes/<uuid:pk>/edit/", views.NoteEditView.as_view(), name="note_edit"),
    path("notes/<uuid:pk>/delete/", views.NoteDeleteView.as_view(), name="note_delete"),
    # Custom relationships
    path("relationships/", views.RelationshipListView.as_view(), name="relationship_list"),
    path(
        "relationships/add/",
        views.RelationshipEditView.as_view(),
        name="relationship_add",
    ),
    path(
        "relationships/delete/",
        views.RelationshipBulkDeleteView.as_view(),
        name="relationship_bulk_delete",
    ),
    path(
        "relationships/<uuid:pk>/",
        views.RelationshipView.as_view(),
        name="relationship",
    ),
    path(
        "relationships/<uuid:pk>/edit/",
        views.RelationshipEditView.as_view(),
        name="relationship_edit",
    ),
    path(
        "relationships/<uuid:pk>/delete/",
        views.RelationshipDeleteView.as_view(),
        name="relationship_delete",
    ),
    path(
        "relationships/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="relationship_changelog",
        kwargs={"model": Relationship},
    ),
    path(
        "relationships/<uuid:pk>/notes/",
        views.ObjectNotesView.as_view(),
        name="relationship_notes",
        kwargs={"model": Relationship},
    ),
    path(
        "relationship-associations/",
        views.RelationshipAssociationListView.as_view(),
        name="relationshipassociation_list",
    ),
    path(
        "relationship-associations/delete/",
        views.RelationshipAssociationBulkDeleteView.as_view(),
        name="relationshipassociation_bulk_delete",
    ),
    path(
        "relationship-associations/<uuid:pk>/delete/",
        views.RelationshipAssociationDeleteView.as_view(),
        name="relationshipassociation_delete",
    ),
    # Secrets
    path("secrets/", views.SecretListView.as_view(), name="secret_list"),
    path("secrets/add/", views.SecretEditView.as_view(), name="secret_add"),
    path("secrets/delete/", views.SecretBulkDeleteView.as_view(), name="secret_bulk_delete"),
    path("secrets/import/", views.SecretBulkImportView.as_view(), name="secret_import"),
    path(
        "secrets/provider/<str:provider_slug>/form/",
        views.SecretProviderParametersFormView.as_view(),
        name="secret_provider_parameters_form",
    ),
    path("secrets/<uuid:pk>/", views.SecretView.as_view(), name="secret"),
    path("secrets/<uuid:pk>/edit/", views.SecretEditView.as_view(), name="secret_edit"),
    path("secrets/<uuid:pk>/delete/", views.SecretDeleteView.as_view(), name="secret_delete"),
    path(
        "secrets/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="secret_changelog",
        kwargs={"model": Secret},
    ),
    path(
        "secrets/<uuid:pk>/notes/",
        views.ObjectNotesView.as_view(),
        name="secret_notes",
        kwargs={"model": Secret},
    ),
    path("secrets-groups/", views.SecretsGroupListView.as_view(), name="secretsgroup_list"),
    path("secrets-groups/add/", views.SecretsGroupEditView.as_view(), name="secretsgroup_add"),
    path("secrets-groups/delete/", views.SecretsGroupBulkDeleteView.as_view(), name="secretsgroup_bulk_delete"),
    path("secrets-groups/<uuid:pk>/", views.SecretsGroupView.as_view(), name="secretsgroup"),
    path("secrets-groups/<uuid:pk>/edit/", views.SecretsGroupEditView.as_view(), name="secretsgroup_edit"),
    path("secrets-groups/<uuid:pk>/delete/", views.SecretsGroupDeleteView.as_view(), name="secretsgroup_delete"),
    path(
        "secrets-groups/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="secretsgroup_changelog",
        kwargs={"model": SecretsGroup},
    ),
    path(
        "secrets-groups/<uuid:pk>/notes/",
        views.ObjectNotesView.as_view(),
        name="secretsgroup_notes",
        kwargs={"model": SecretsGroup},
    ),
    # Custom statuses
    path("statuses/", views.StatusListView.as_view(), name="status_list"),
    path("statuses/add/", views.StatusEditView.as_view(), name="status_add"),
    path("statuses/edit/", views.StatusBulkEditView.as_view(), name="status_bulk_edit"),
    path(
        "statuses/delete/",
        views.StatusBulkDeleteView.as_view(),
        name="status_bulk_delete",
    ),
    path("statuses/import/", views.StatusBulkImportView.as_view(), name="status_import"),
    path("statuses/<uuid:pk>/", views.StatusView.as_view(), name="status"),
    path("statuses/<uuid:pk>/edit/", views.StatusEditView.as_view(), name="status_edit"),
    path(
        "statuses/<uuid:pk>/delete/",
        views.StatusDeleteView.as_view(),
        name="status_delete",
    ),
    path(
        "statuses/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="status_changelog",
        kwargs={"model": Status},
    ),
    path(
        "statuses/<uuid:pk>/notes/",
        views.ObjectNotesView.as_view(),
        name="status_notes",
        kwargs={"model": Status},
    ),
    # Tags
    path("tags/", views.TagListView.as_view(), name="tag_list"),
    path("tags/add/", views.TagEditView.as_view(), name="tag_add"),
    path("tags/import/", views.TagBulkImportView.as_view(), name="tag_import"),
    path("tags/edit/", views.TagBulkEditView.as_view(), name="tag_bulk_edit"),
    path("tags/delete/", views.TagBulkDeleteView.as_view(), name="tag_bulk_delete"),
    path("tags/<uuid:pk>/", views.TagView.as_view(), name="tag"),
    path("tags/<uuid:pk>/edit/", views.TagEditView.as_view(), name="tag_edit"),
    path("tags/<uuid:pk>/delete/", views.TagDeleteView.as_view(), name="tag_delete"),
    path(
        "tags/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="tag_changelog",
        kwargs={"model": Tag},
    ),
    path(
        "tags/<uuid:pk>/notes/",
        views.ObjectNotesView.as_view(),
        name="tag_notes",
        kwargs={"model": Tag},
    ),
    # Webhook
    path("webhooks/", views.WebhookListView.as_view(), name="webhook_list"),
    path("webhooks/add/", views.WebhookEditView.as_view(), name="webhook_add"),
    path(
        "webhooks/delete/",
        views.WebhookBulkDeleteView.as_view(),
        name="webhook_bulk_delete",
    ),
    path("webhooks/<uuid:pk>/", views.WebhookView.as_view(), name="webhook"),
    path("webhooks/<uuid:pk>/edit/", views.WebhookEditView.as_view(), name="webhook_edit"),
    path(
        "webhooks/<uuid:pk>/delete/",
        views.WebhookDeleteView.as_view(),
        name="webhook_delete",
    ),
    path(
        "webhooks/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="webhook_changelog",
        kwargs={"model": Webhook},
    ),
    path(
        "webhooks/<uuid:pk>/notes/",
        views.ObjectNotesView.as_view(),
        name="webhook_notes",
        kwargs={"model": Webhook},
    ),
]

urlpatterns += router.urls
