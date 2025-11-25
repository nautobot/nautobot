from django.urls import path
from django.views.generic.base import RedirectView

from nautobot.core.views.routers import NautobotUIViewSetRouter
from nautobot.extras import views
from nautobot.extras.models import (
    Job,
    ScheduledJob,
)

app_name = "extras"

router = NautobotUIViewSetRouter()
router.register("approval-workflows", views.ApprovalWorkflowUIViewSet)
router.register("approval-workflow-definitions", views.ApprovalWorkflowDefinitionUIViewSet)
router.register("approval-workflow-stages", views.ApprovalWorkflowStageUIViewSet)
router.register("approval-workflow-stage-definitions", views.ApprovalWorkflowStageDefinitionUIViewSet)
router.register("approval-workflow-stage-responses", views.ApprovalWorkflowStageResponseUIViewSet)
router.register("computed-fields", views.ComputedFieldUIViewSet)
router.register("config-context-schemas", views.ConfigContextSchemaUIViewSet)
router.register("config-contexts", views.ConfigContextUIViewSet)
router.register("contacts", views.ContactUIViewSet)
router.register("contact-associations", views.ContactAssociationUIViewSet)
router.register("custom-fields", views.CustomFieldUIViewSet)
router.register("custom-links", views.CustomLinkUIViewSet)
router.register("dynamic-groups", views.DynamicGroupUIViewSet)
router.register("export-templates", views.ExportTemplateUIViewSet)
router.register("external-integrations", views.ExternalIntegrationUIViewSet)
router.register("git-repositories", views.GitRepositoryUIViewSet)
router.register("graphql-queries", views.GraphQLQueryUIViewSet)
router.register("job-buttons", views.JobButtonUIViewSet)
router.register("job-hooks", views.JobHookUIViewSet)
router.register("job-queues", views.JobQueueUIViewSet)
router.register("job-results", views.JobResultUIViewSet)
router.register("metadata-types", views.MetadataTypeUIViewSet)
router.register("object-changes", views.ObjectChangeUIViewSet)
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
    # Approver Dashboard
    path("approver-dashboard/", views.ApproverDashboardView.as_view({"get": "list"}), name="approver_dashboard"),
    # Approvee Dashboard
    path("approvee-dashboard/", views.ApproveeDashboardView.as_view({"get": "list"}), name="approvee_dashboard"),
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
    path("jobs/scheduled-jobs/", RedirectView.as_view(url="/extras/scheduled-jobs/"), name="scheduledjob_list_legacy"),
    path(
        "jobs/scheduled-jobs/<uuid:pk>/",
        RedirectView.as_view(url="/extras/scheduled-jobs/%(pk)s/"),
        name="scheduledjob_legacy",
    ),
    path(
        "jobs/scheduled-jobs/<uuid:pk>/delete/",
        RedirectView.as_view(url="/extras/scheduled-jobs/%(pk)s/delete/"),
        name="scheduledjob_delete_legacy",
    ),
    path(
        "jobs/scheduled-jobs/delete/",
        RedirectView.as_view(url="/extras/scheduled-jobs/delete/"),
        name="scheduledjob_bulk_delete_legacy",
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
    # ScheduledJobs
    path("scheduled-jobs/", views.ScheduledJobListView.as_view(), name="scheduledjob_list"),
    path("scheduled-jobs/<uuid:pk>/", views.ScheduledJobView.as_view(), name="scheduledjob"),
    path("scheduled-jobs/<uuid:pk>/delete/", views.ScheduledJobDeleteView.as_view(), name="scheduledjob_delete"),
    path(
        "scheduled-jobs/delete/",
        views.ScheduledJobBulkDeleteView.as_view(),
        name="scheduledjob_bulk_delete",
    ),
    path(
        "scheduled-jobs/<uuid:pk>/approval-workflow/",
        views.ObjectApprovalWorkflowView.as_view(),
        name="scheduledjob_approvalworkflow",
        kwargs={"model": ScheduledJob},
    ),
    # Secrets
    path(
        "secrets/provider/<str:provider_slug>/form/",
        views.SecretProviderParametersFormView.as_view(),
        name="secret_provider_parameters_form",
    ),
]

urlpatterns += router.urls
