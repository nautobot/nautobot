from django.urls import path

from nautobot.extras import views
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    CustomLink,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    Tag,
    Status,
    Webhook,
)


app_name = "extras"
urlpatterns = [
    # Tags
    path("tags/", views.TagListView.as_view(), name="tag_list"),
    path("tags/add/", views.TagEditView.as_view(), name="tag_add"),
    path("tags/import/", views.TagBulkImportView.as_view(), name="tag_import"),
    path("tags/edit/", views.TagBulkEditView.as_view(), name="tag_bulk_edit"),
    path("tags/delete/", views.TagBulkDeleteView.as_view(), name="tag_bulk_delete"),
    path("tags/<str:slug>/", views.TagView.as_view(), name="tag"),
    path("tags/<str:slug>/edit/", views.TagEditView.as_view(), name="tag_edit"),
    path("tags/<str:slug>/delete/", views.TagDeleteView.as_view(), name="tag_delete"),
    path(
        "tags/<str:slug>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="tag_changelog",
        kwargs={"model": Tag},
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
        "config-context-schemas/<slug:slug>/",
        views.ConfigContextSchemaView.as_view(),
        name="configcontextschema",
    ),
    path(
        "config-context-schemas/<slug:slug>/validation/",
        views.ConfigContextSchemaObjectValidationView.as_view(),
        name="configcontextschema_object_validation",
    ),
    path(
        "config-context-schemas/<slug:slug>/edit/",
        views.ConfigContextSchemaEditView.as_view(),
        name="configcontextschema_edit",
    ),
    path(
        "config-context-schemas/<slug:slug>/delete/",
        views.ConfigContextSchemaDeleteView.as_view(),
        name="configcontextschema_delete",
    ),
    path(
        "config-context-schemas/<slug:slug>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="configcontextschema_changelog",
        kwargs={"model": ConfigContextSchema},
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
        "git-repositories/<str:slug>/",
        views.GitRepositoryView.as_view(),
        name="gitrepository",
    ),
    path(
        "git-repositories/<str:slug>/edit/",
        views.GitRepositoryEditView.as_view(),
        name="gitrepository_edit",
    ),
    path(
        "git-repositories/<str:slug>/delete/",
        views.GitRepositoryDeleteView.as_view(),
        name="gitrepository_delete",
    ),
    path(
        "git-repositories/<str:slug>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="gitrepository_changelog",
        kwargs={"model": GitRepository},
    ),
    path(
        "git-repositories/<str:slug>/result/",
        views.GitRepositoryResultView.as_view(),
        name="gitrepository_result",
    ),
    path(
        "git-repositories/<str:slug>/sync/",
        views.GitRepositorySyncView.as_view(),
        name="gitrepository_sync",
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
    # Change logging
    path("changelog/", views.ObjectChangeListView.as_view(), name="objectchange_list"),
    path("changelog/<uuid:pk>/", views.ObjectChangeView.as_view(), name="objectchange"),
    # Jobs
    path("jobs/", views.JobListView.as_view(), name="job_list"),
    path(
        "jobs/results/<uuid:pk>/",
        views.JobJobResultView.as_view(),
        name="job_jobresult",
    ),
    path("jobs/<path:class_path>/", views.JobView.as_view(), name="job"),
    # Generic job results
    path("job-results/", views.JobResultListView.as_view(), name="jobresult_list"),
    path("job-results/<uuid:pk>/", views.JobResultView.as_view(), name="jobresult"),
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
    path("statuses/<str:slug>/", views.StatusView.as_view(), name="status"),
    path("statuses/<str:slug>/edit/", views.StatusEditView.as_view(), name="status_edit"),
    path(
        "statuses/<str:slug>/delete/",
        views.StatusDeleteView.as_view(),
        name="status_delete",
    ),
    path(
        "statuses/<str:slug>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="status_changelog",
        kwargs={"model": Status},
    ),
    # Custom relationships
    path("relationships/", views.RelationshipListView.as_view(), name="relationship_list"),
    path(
        "relationships/add/",
        views.RelationshipEditView.as_view(),
        name="relationship_add",
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
        "relationships/associations/",
        views.RelationshipAssociationListView.as_view(),
        name="relationshipassociation_list",
    ),
    path(
        "relationships/associations/<uuid:pk>/delete/",
        views.RelationshipAssociationDeleteView.as_view(),
        name="relationshipassociation_delete",
    ),
    # GraphQL Queries
    path("graphql-queries/", views.GraphQLQueryListView.as_view(), name="graphqlquery_list"),
    path("graphql-queries/add/", views.GraphQLQueryEditView.as_view(), name="graphqlquery_add"),
    path(
        "graphql-queries/delete/",
        views.GraphQLQueryBulkDeleteView.as_view(),
        name="GraphQLQuery_bulk_delete",
    ),
    path("graphql-queries/<str:slug>/", views.GraphQLQueryView.as_view(), name="graphqlquery"),
    path(
        "graphql-queries/<str:slug>/edit/",
        views.GraphQLQueryEditView.as_view(),
        name="graphqlquery_edit",
    ),
    path(
        "graphql-queries/<str:slug>/delete/",
        views.GraphQLQueryDeleteView.as_view(),
        name="graphqlquery_delete",
    ),
    path(
        "graphql-queries/<uuid:pk>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="graphqlquery_changelog",
        kwargs={"model": GraphQLQuery},
    ),
    # Computed Fields
    path("computed-fields/", views.ComputedFieldListView.as_view(), name="computedfield_list"),
    path("computed-fields/add/", views.ComputedFieldEditView.as_view(), name="computedfield_add"),
    path(
        "computed-fields/delete/",
        views.ComputedFieldBulkDeleteView.as_view(),
        name="computedfield_bulk_delete",
    ),
    path("computed-fields/<slug:slug>/", views.ComputedFieldView.as_view(), name="computedfield"),
    path(
        "computed-fields/<slug:slug>/edit/",
        views.ComputedFieldEditView.as_view(),
        name="computedfield_edit",
    ),
    path(
        "computed-fields/<slug:slug>/delete/",
        views.ComputedFieldDeleteView.as_view(),
        name="computedfield_delete",
    ),
    path(
        "computed-fields/<slug:slug>/changelog/",
        views.ObjectChangeLogView.as_view(),
        name="computedfield_changelog",
        kwargs={"model": ComputedField},
    ),
]
