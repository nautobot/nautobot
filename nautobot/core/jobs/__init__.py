import os

from django.conf import settings

from nautobot.core.celery import register_jobs
from nautobot.extras.choices import LogLevelChoices
from nautobot.extras.datasources import (
    ensure_git_repository,
    git_repository_dry_run,
    refresh_datasource_content,
)
from nautobot.extras.jobs import Job, ObjectVar
from nautobot.extras.models import GitRepository


name = "System Jobs"


class GitRepositoryPullAndRefreshData(Job):
    """
    System job to clone and/or pull a Git repository, then invoke refresh_datasource_content().
    """

    repository = ObjectVar(
        description="Git Repository to pull and refresh",
        label="Git Repository",
        model=GitRepository,
    )

    class Meta:
        name = "Git Repository: Sync"
        has_sensitive_variables = False

    def run(self, repository):
        job_result = self.get_job_result()
        user = job_result.user

        job_result.log(
            f'Creating/refreshing local copy of Git repository "{repository.name}"...',
            logger=self.logger,
        )

        try:
            if not os.path.exists(settings.GIT_ROOT):
                os.makedirs(settings.GIT_ROOT)

            ensure_git_repository(
                repository,
                job_result=job_result,
                logger=self.logger,
            )

            job_result.log(
                f'The current Git repository hash is "{repository.current_head}"',
            )

            refresh_datasource_content("extras.gitrepository", repository, user, job_result, delete=False)

        except Exception as exc:
            job_result.log(
                f"Error while refreshing {repository.name}: {exc}",
                level_choice=LogLevelChoices.LOG_FAILURE,
                logger=self.logger,
            )
            raise

        finally:
            job_result.log(
                f"Repository synchronization completed in {job_result.duration}",
                level_choice=LogLevelChoices.LOG_INFO,
                logger=self.logger,
            )


class GitRepositoryDiffOriginalAndLocal(Job):
    """System Job to perform a dry run on a Git repository."""

    repository = ObjectVar(
        description="Git Repository to dry-run",
        label="Git Repository",
        model=GitRepository,
    )

    class Meta:
        name = "Git Repository: Dry-Run"
        has_sensitive_variables = False

    def run(self, repository):
        job_result = self.get_job_result()

        job_result.log(f'Running a Dry Run on Git repository "{repository.name}"...', logger=self.logger)

        try:
            if not os.path.exists(settings.GIT_ROOT):
                os.makedirs(settings.GIT_ROOT)

            git_repository_dry_run(repository, job_result=job_result, logger=self.logger)

        except Exception as exc:
            job_result.log(
                f"Error while running a dry run on {repository.name}: {exc}",
                level_choice=LogLevelChoices.LOG_FAILURE,
            )
            raise

        finally:
            job_result.log(
                f"Repository dry run completed in {job_result.duration}",
                level_choice=LogLevelChoices.LOG_INFO,
                logger=self.logger,
            )


jobs = [GitRepositoryPullAndRefreshData, GitRepositoryDiffOriginalAndLocal]
register_jobs(*jobs)
