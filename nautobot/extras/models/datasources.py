"""Models for representing external data sources."""
import os

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import URLValidator
from django.db import models, transaction
from django.urls import reverse
from django_cryptography.fields import encrypt

from nautobot.extras.utils import extras_features
from nautobot.core.fields import AutoSlugField
from nautobot.core.models.generics import PrimaryModel


@extras_features(
    "config_context_owners",
    "custom_fields",
    "export_template_owners",
    "job_results",
    "relationships",
    "webhooks",
)
class GitRepository(PrimaryModel):
    """Representation of a Git repository used as an external data source."""

    TOKEN_PLACEHOLDER = "********"

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

    # Mark field as private so that it doesn't get included in ChangeLogging records!
    _token = encrypt(
        models.CharField(
            max_length=200,
            blank=True,
            default="",
        )
    )

    username = models.CharField(
        max_length=64,
        blank=True,
        default="",
    )

    secrets_group = models.ForeignKey(
        to="extras.SecretsGroup",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
    )

    # Data content types that this repo is a source of. Valid options are dynamically generated based on
    # the data types registered in registry['datasource_contents'].
    provided_contents = models.JSONField(encoder=DjangoJSONEncoder, default=list, blank=True)

    csv_headers = ["name", "slug", "remote_url", "branch", "secrets_group", "provided_contents"]
    clone_fields = ["remote_url", "secrets_group", "provided_contents"]

    class Meta:
        ordering = ["name"]
        verbose_name = "Git repository"
        verbose_name_plural = "Git repositories"

    def __init__(self, *args, **kwargs):
        # If instantiated from the REST API, the originating Request will be passed as a kwarg:
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Store the initial repo slug and token so we can check for changes on save().
        self.__initial_slug = self.slug
        self.__initial_token = self._token

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("extras:gitrepository", kwargs={"slug": self.slug})

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.remote_url,
            self.branch,
            self.provided_contents,
        )

    @property
    def token_rendered(self):
        if self._token:
            return self.TOKEN_PLACEHOLDER
        else:
            return "—"

    @property
    def filesystem_path(self):
        return os.path.join(settings.GIT_ROOT, self.slug)

    def set_dryrun(self):
        """
        Add _dryrun flag.

        The existence of this flag indicates that the next sync of this repo (on save()) should be a dry-run only.
        """
        self._dryrun = True

    def save(self, *args, trigger_resync=True, **kwargs):
        if self.__initial_token and self._token == self.TOKEN_PLACEHOLDER:
            # User edited the repo but did NOT specify a new token value. Make sure we keep the existing value.
            self._token = self.__initial_token

        super().save(*args, **kwargs)

        def on_commit_callback():
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

            dry_run = hasattr(self, "_dryrun")
            if trigger_resync or dry_run:
                assert self.request is not None, "No HTTP request associated with this update!"
                from nautobot.extras.datasources import (
                    enqueue_pull_git_repository_and_refresh_data,
                    enqueue_git_repository_diff_origin_and_local,
                )

                # NOTE: if dry_run is True, there would be no need to trigger a resync
                # regardless of the trigger_resync value (True/False)
                if dry_run:
                    enqueue_git_repository_diff_origin_and_local(self, self.request)
                else:
                    enqueue_pull_git_repository_and_refresh_data(self, self.request)

            # Update cached values
            self.__initial_token = self._token
            self.__initial_slug = self.slug

        transaction.on_commit(on_commit_callback)
