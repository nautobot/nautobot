"""Models for representing external data sources."""
from importlib.util import find_spec
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import URLValidator
from django.db import models

from nautobot.core.models.fields import AutoSlugField, slugify_dashes_to_underscores
from nautobot.core.models.generics import PrimaryModel
from nautobot.extras.utils import extras_features, check_if_key_is_graphql_safe


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
    slug = AutoSlugField(
        populate_from="name",
        help_text="Internal field name. Please use underscores rather than dashes in this key.",
        slugify_function=slugify_dashes_to_underscores,
    )

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

    def clean(self):
        super().clean()

        # Autogenerate slug now, rather than in pre_save(), if not set already, as we need to check it below.
        if self.slug == "":
            self._meta.get_field("slug").create_slug(self, add=(not self.present_in_database))

        if self.present_in_database and self.slug != self.__initial_slug:
            raise ValidationError(
                f"Slug cannot be changed once set. Current slug is {self.__initial_slug}, "
                f"requested slug is {self.slug}"
            )

        if not self.present_in_database:
            check_if_key_is_graphql_safe(self.__class__.__name__, self.slug, "slug")
            # Check on create whether the proposed slug conflicts with a module name already in the Python environment.
            # Because we add GIT_ROOT to the end of sys.path, trying to import this repository will instead
            # import the earlier-found Python module in its place, which would be undesirable.
            if find_spec(self.slug) is not None:
                raise ValidationError(
                    f'Please choose a different slug, as "{self.slug}" is an installed Python package or module.'
                )

        if self.provided_contents:
            q = models.Q()
            for item in self.provided_contents:
                q |= models.Q(provided_contents__contains=item)
            duplicate_repos = GitRepository.objects.filter(remote_url=self.remote_url).exclude(id=self.id).filter(q)
            if duplicate_repos.exists():
                raise ValidationError(
                    f"Another Git repository already configured for remote URL {self.remote_url} "
                    "provides contents overlapping with this repository."
                )

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
