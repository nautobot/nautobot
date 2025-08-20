from django.urls import path

from nautobot.core.views.routers import NautobotUIViewSetRouter
from nautobot.extras import views
from nautobot.extras.models import (
    DynamicGroup,
    GitRepository,
    Job,
    Relationship,
)

app_name = "extras"

router = NautobotUIViewSetRouter()
router.register("computed-fields", views.ComputedFieldUIViewSet)
router.register("config-context-schemas", views.ConfigContextSchemaUIViewSet)
router.register("config-contexts", views.ConfigContextUIViewSet)
router.register("contacts", views.ContactUIViewSet)
router.register("contact-associations", views.ContactAssociationUIViewSet)
router.register("custom-fields", views.CustomFieldUIViewSet)
router.register("custom-links", views.CustomLinkUIViewSet)
router.register("export-templates", views.ExportTemplateUIViewSet)
router.register("external-integrations", views.ExternalIntegrationUIViewSet)
router.register("graphql-queries", views.GraphQLQueryUIViewSet)
router.register("job-buttons", views.JobButtonUIViewSet)
router.register("job-hooks", views.JobHookUIViewSet)
router.register("job-queues", views.JobQueueUIViewSet)
router.register("job-results", views.JobResultUIViewSet)
router.register("metadata-types", views.MetadataTypeUIViewSet)
router.register("notes", views.NoteUIViewSet)
router.register("object-metadata", views.ObjectMetadataUIViewSet)
router.register("relationship-associations", views.RelationshipAssociationUIViewSet)
router.register("relationships", views.RelationshipUIViewSet)
router.register("roles", views.RoleUIViewSet)
router.register("saved-views", views.SavedViewUIViewSet)
router.register("secrets", views.SecretUIViewSet)
router.register("secrets-groups", views.SecretsGroupUIViewSet)
router.register("static-group-associations", views.StaticGroupAssociationUIViewSet)
router.register("statuses", views.StatusUIViewSet)
router.register("tags", views.TagUIViewSet)
router.register("teams", views.TeamUIViewSet)
router.register("webhooks", views.WebhookUIViewSet)

urlpatterns = [
    # Change logging
    path("object-changes/", views.ObjectChangeListView.as_view(), name="objectchange_list"),
    path("object-changes/<uuid:pk>/", views.ObjectChangeView.as_view(), name="objectchange"),
    # Config context schema
    path(
        "config-context-schemas/<uuid:pk>/validation/",
        views.ConfigContextSchemaObjectValidationView.as_view(),
        name="configcontextschema_object_validation",
    ),
    # contacts
    path("contact-associations/add-new-contact/", views.ObjectNewContactView.as_view(), name="object_contact_add"),
    path("contact-associations/add-new-team/", views.ObjectNewTeamView.as_view(), name="object_team_add"),
    path(
        "contact-associations/assign-contact-team/",
        views.ObjectAssignContactOrTeamView.as_view(),
        name="object_contact_team_assign",
    ),
    # Dynamic Groups
    path("dynamic-groups/", views.DynamicGroupListView.as_view(), name="dynamicgroup_list"),
    path("dynamic-groups/add/", views.DynamicGroupEditView.as_view(), name="dynamicgroup_add"),
    path("dynamic-groups/assign-members/", views.DynamicGroupBulkAssignView.as_view(), name="dynamicgroup_bulk_assign"),
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
        views.GitRepositoryBulkImportView.as_view(),  # 3.0 TODO: remove, unused
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
    path("jobs/edit/", views.JobBulkEditView.as_view(), name="job_bulk_edit"),
    path("jobs/delete/", views.JobBulkDeleteView.as_view(), name="job_bulk_delete"),
    # Custom relationships
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
    # Secrets
    path(
        "secrets/provider/<str:provider_slug>/form/",
        views.SecretProviderParametersFormView.as_view(),
        name="secret_provider_parameters_form",
    ),
]

urlpatterns += router.urls
