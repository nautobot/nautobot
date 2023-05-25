"""Models for representing external data sources."""
import os

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import URLValidator
from django.db import models

from nautobot.core.models.fields import AutoSlugField
from nautobot.core.models.generics import PrimaryModel
from nautobot.extras.utils import extras_features


@extras_features(
    "config_context_owners",
    "export_template_owners",
    "job_results",
    "webhooks",
)
class GitRepository(PrimaryModel):
    """Representation of a Git repository used as an external data source."""

    name = models.CharField(
        max_length=100,
        unique=True,
    )
    slug = AutoSlugField(populate_from="name")

    remote_url = models.URLField(
        max_length=255,
        # For the moment we don't support ssh:// and git:// URLs
        help_text="Only HTTP and HTTPS URLs are presently supported",
        validators=[URLValidator(schemes=["http", "https"])],
    )
    branch = models.CharField(
        max_length=64,
        default="main",
    )

    current_head = models.CharField(
        help_text="Commit hash of the most recent fetch from the selected branch. Used for syncing between workers.",
        max_length=48,
        default="",
        blank=True,
    )

    secrets_group = models.ForeignKey(
        to="extras.SecretsGroup",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
        related_name="git_repositories",
    )

    # Data content types that this repo is a source of. Valid options are dynamically generated based on
    # the data types registered in registry['datasource_contents'].
    provided_contents = models.JSONField(encoder=DjangoJSONEncoder, default=list, blank=True)

    clone_fields = ["remote_url", "secrets_group", "provided_contents"]

    class Meta:
        ordering = ["name"]
        verbose_name = "Git repository"
        verbose_name_plural = "Git repositories"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Store the initial repo slug so we can check for changes on save().
        self.__initial_slug = self.slug

    def __str__(self):
        return self.name

    def get_latest_sync(self):
        """
        Return a `JobResult` for the latest sync operation.

        Returns:
            JobResult
        """
        from nautobot.extras.models import JobResult

        # This will match all "GitRepository" jobs (pull/refresh, dry-run, etc.)
        prefix = "nautobot.core.jobs.GitRepository"
        return JobResult.objects.filter(task_name__startswith=prefix, task_kwargs__repository=self.pk).latest()

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.remote_url,
            self.branch,
            self.secrets_group.name if self.secrets_group else None,
            self.provided_contents,
        )

    @property
    def filesystem_path(self):
        return os.path.join(settings.GIT_ROOT, self.slug)

    def sync(self, user, dry_run=False):
        """
        Enqueue a Job to pull the Git repository from the remote and return the sync result.

        Args:
            user (User): The User that will perform the sync.
            dry_run (bool): If set, dry-run the Git sync.

        Returns:
            JobResult
        """
        from nautobot.extras.datasources import (
            enqueue_pull_git_repository_and_refresh_data,
            enqueue_git_repository_diff_origin_and_local,
        )

        if dry_run:
            return enqueue_git_repository_diff_origin_and_local(self, user)
        return enqueue_pull_git_repository_and_refresh_data(self, user)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # TODO(jathan): This should be moved to a callable that can be triggered on a worker event
        # when a repo is "renamed", so that all workers will do it together.
        if self.__initial_slug and self.slug != self.__initial_slug:
            # Rename any previously existing repo directory to the new slug.
            # TODO: In a distributed Nautobot deployment, each Django instance and/or worker instance may
            # have its own clone of this repository on its own local filesystem; we need some way to ensure
            # that all such clones are renamed.
            # For now we just rename the one that we have locally and rely on other methods
            # (notably get_jobs()) to clean up other clones as they're encountered.
            if os.path.exists(os.path.join(settings.GIT_ROOT, self.__initial_slug)):
                os.rename(
                    os.path.join(settings.GIT_ROOT, self.__initial_slug),
                    self.filesystem_path,
                )

        # Update cached values
        self.__initial_slug = self.slug
