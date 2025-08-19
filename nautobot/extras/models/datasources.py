"""Models for representing external data sources."""

from contextlib import contextmanager
import logging
import os
import shutil
import tempfile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models.fields import AutoSlugField, LaxURLField, slugify_dashes_to_underscores
from nautobot.core.models.generics import PrimaryModel
from nautobot.core.models.validators import EnhancedURLValidator
from nautobot.core.utils.git import GitRepo
from nautobot.core.utils.module_loading import check_name_safe_to_import_privately
from nautobot.extras.utils import extras_features

logger = logging.getLogger(__name__)


@extras_features(
    "config_context_owners",
    "export_template_owners",
    "graphql_query_owners",
    "graphql",
    "job_results",
    "webhooks",
)
class GitRepository(PrimaryModel):
    """Representation of a Git repository used as an external data source."""

    name = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        unique=True,
    )
    slug = AutoSlugField(
        populate_from="name",
        help_text="Internal field name. Please use underscores rather than dashes in this key.",
        slugify_function=slugify_dashes_to_underscores,
    )

    remote_url = LaxURLField(
        max_length=CHARFIELD_MAX_LENGTH,
        # For the moment we don't support ssh:// and git:// URLs
        help_text="Only HTTP and HTTPS URLs are presently supported",
        validators=[EnhancedURLValidator(schemes=["http", "https"])],
    )
    branch = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        default="main",
        help_text="Branch, tag, or commit",
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
                f"Slug cannot be changed once set. Current slug is {self.__initial_slug}, requested slug is {self.slug}"
            )

        if not self.present_in_database:
            permitted, reason = check_name_safe_to_import_privately(self.slug)
            if not permitted:
                raise ValidationError({"slug": f"Please choose a different slug; {self.slug!r} is {reason}"})

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

        # Changing branch or remote_url invalidates current_head
        if self.present_in_database:
            past = GitRepository.objects.get(id=self.id)
            if self.remote_url != past.remote_url or self.branch != past.branch:
                self.current_head = ""

    def get_latest_sync(self):
        """
        Return a `JobResult` for the latest sync operation if one has occurred.

        Returns:
            Returns a `JobResult` if the repo has been synced before, otherwise returns None.
        """
        from nautobot.extras.models import JobResult

        # This will match all "GitRepository" jobs (pull/refresh, dry-run, etc.)
        prefix = "nautobot.core.jobs.GitRepository"

        if JobResult.objects.filter(task_name__startswith=prefix, task_kwargs__repository=self.pk).exists():
            return JobResult.objects.filter(task_name__startswith=prefix, task_kwargs__repository=self.pk).latest()
        else:
            return None

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
            enqueue_git_repository_diff_origin_and_local,
            enqueue_pull_git_repository_and_refresh_data,
        )

        if dry_run:
            return enqueue_git_repository_diff_origin_and_local(self, user)
        return enqueue_pull_git_repository_and_refresh_data(self, user)

    sync.alters_data = True

    @contextmanager
    def clone_to_directory_context(self, path=None, branch=None, head=None, depth=0):
        """
        Context manager to perform a (shallow or full) clone of the Git repository in a temporary directory.

        Args:
            path (str, optional): The absolute directory path to clone into. If not specified, `tempfile.gettempdir()` will be used.
            branch (str, optional): The branch to checkout. If not set, the GitRepository.branch will be used.
            head (str, optional): Git commit hash to check out instead of pulling branch latest.
            depth (int, optional): The depth of the clone. If set to 0, a full clone will be performed.

        Returns:
            Returns the absolute path of the cloned repo if clone was successful, otherwise returns None.
        """

        if branch and head:
            raise ValueError("Cannot specify both branch and head")

        path_name = None
        try:
            path_name = self.clone_to_directory(path=path, branch=branch, head=head, depth=depth)
            yield path_name
        finally:
            # Cleanup the temporary directory
            if path_name:
                self.cleanup_cloned_directory(path_name)

    clone_to_directory_context.alters_data = True

    def clone_to_directory(self, path=None, branch=None, head=None, depth=0):
        """
        Perform a (shallow or full) clone of the Git repository in a temporary directory.

        Args:
            path (str, optional): The absolute directory path to clone into. If not specified, `tempfile.gettempdir()` will be used.
            branch (str, optional): The branch to checkout. If not set, the GitRepository.branch will be used.
            head (str, optional): Git commit hash to check out instead of pulling branch latest.
            depth (int, optional): The depth of the clone. If set to 0, a full clone will be performed.

        Returns:
            Returns the absolute path of the cloned repo if clone was successful, otherwise returns None.
        """
        from nautobot.extras.datasources import get_repo_access_url

        if branch and head:
            raise ValueError("Cannot specify both branch and head")

        try:
            path_name = tempfile.mkdtemp(dir=path, prefix=self.slug)
        except PermissionError as e:
            logger.error(f"Failed to create temporary directory at {path}: {e}")
            raise e

        if not branch:
            branch = self.branch

        try:
            remote_url = get_repo_access_url(self)
            repo_helper = GitRepo(path_name, remote_url, depth=depth, branch=branch)
            if head:
                repo_helper.checkout(branch, head)
        except Exception as e:
            logger.error(f"Failed to clone repository {self.name} to {path_name}: {e}")
            raise e

        logger.info(f"Cloned repository {self.name} to {path_name}")
        return path_name

    clone_to_directory.alters_data = True

    def cleanup_cloned_directory(self, path):
        """
        Cleanup the cloned directory.

        Args:
            path (str): The absolute directory path to cleanup.
        """

        try:
            shutil.rmtree(path)
        except OSError as os_error:
            # log error if the cleanup fails
            logger.error(f"Failed to cleanup temporary directory at {path}: {os_error}")

    cleanup_cloned_directory.alters_data = True
