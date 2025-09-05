from nautobot.core.api.routers import OrderedDefaultRouter

from . import views

router = OrderedDefaultRouter(view_name="Extras")

# Computed Fields
router.register("computed-fields", views.ComputedFieldViewSet)

# Config contexts
router.register("config-contexts", views.ConfigContextViewSet)

# Config context schemas
router.register("config-context-schemas", views.ConfigContextSchemaViewSet)

# Contacts
router.register("contacts", views.ContactViewSet)
router.register("contact-associations", views.ContactAssociationViewSet)

# ContentTypes
router.register("content-types", views.ContentTypeViewSet)

# Custom fields
router.register("custom-fields", views.CustomFieldViewSet)
router.register("custom-field-choices", views.CustomFieldChoiceViewSet)

# Custom Links
router.register("custom-links", views.CustomLinkViewSet)

# Dynamic Groups
router.register("dynamic-groups", views.DynamicGroupViewSet)
router.register("dynamic-group-memberships", views.DynamicGroupMembershipViewSet)

# Saved Views
router.register("saved-views", views.SavedViewViewSet)
router.register("user-saved-view-associations", views.UserSavedViewAssociationViewSet)

# Static Groups
router.register("static-group-associations", views.StaticGroupAssociationViewSet)

# Export templates
router.register("export-templates", views.ExportTemplateViewSet)

# External integrations
router.register("external-integrations", views.ExternalIntegrationViewSet)

# File proxies
router.register("file-proxies", views.FileProxyViewSet)

# Git repositories
router.register("git-repositories", views.GitRepositoryViewSet)

# GraphQL Queries
router.register("graphql-queries", views.GraphQLQueryViewSet)

# Image attachments
router.register("image-attachments", views.ImageAttachmentViewSet)

# Jobs
router.register("jobs", views.JobViewSet)
router.register("jobs", views.JobByNameViewSet)

# Job Buttons
router.register("job-buttons", views.JobButtonViewSet)

# Job hooks
router.register("job-hooks", views.JobHooksViewSet)

# Job Log Entries
router.register("job-logs", views.JobLogEntryViewSet)

# Job Queues
router.register("job-queues", views.JobQueueViewSet)
router.register("job-queue-assignments", views.JobQueueAssignmentViewSet)

# Job Results
router.register("job-results", views.JobResultViewSet)

# Scheduled Jobs
router.register("scheduled-jobs", views.ScheduledJobViewSet)

# Metadata
router.register("metadata-types", views.MetadataTypeViewSet)
router.register("metadata-choices", views.MetadataChoiceViewSet)
router.register("object-metadata", views.ObjectMetadataViewSet)

# Notes
router.register("notes", views.NoteViewSet)

# Change logging
router.register("object-changes", views.ObjectChangeViewSet)

# Relationships
router.register("relationships", views.RelationshipViewSet)
router.register("relationship-associations", views.RelationshipAssociationViewSet)

# Roles
router.register("roles", views.RoleViewSet)

# Secrets
router.register("secrets", views.SecretsViewSet)
router.register("secrets-groups", views.SecretsGroupViewSet)
router.register("secrets-groups-associations", views.SecretsGroupAssociationViewSet)

# Statuses
router.register("statuses", views.StatusViewSet)

# Tags
router.register("tags", views.TagViewSet)

# Teams
router.register("teams", views.TeamViewSet)

# Webhooks
router.register("webhooks", views.WebhooksViewSet)


app_name = "extras-api"
urlpatterns = router.urls
