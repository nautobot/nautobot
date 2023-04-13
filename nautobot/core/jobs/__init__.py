from nautobot.core.celery import register_jobs
from nautobot.extras.choices import LogLevelChoices
from nautobot.extras.datasources import ensure_git_repository, git_repository_dry_run, refresh_datasource_content
from nautobot.extras.jobs import Job, ObjectVar
from nautobot.extras.models import GitRepository

name = "System Jobs"


class GitRepositorySync(Job):
    """
    System job to clone and/or pull a Git repository, then invoke `refresh_datasource_content()`.
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
        job_result = self.job_result
        user = job_result.user

        job_result.log(
            f'Creating/refreshing local copy of Git repository "{repository.name}"...',
            logger=self.logger,
        )

        try:
            ensure_git_repository(repository, job_result=job_result, logger=self.logger)
            refresh_datasource_content("extras.gitrepository", repository, user, job_result, delete=False)
        finally:
            job_result.log(
                f"Repository synchronization completed in {job_result.duration}",
                level_choice=LogLevelChoices.LOG_INFO,
                logger=self.logger,
            )


class GitRepositoryDryRun(Job):
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
        job_result = self.job_result
        job_result.log(f'Performing a Dry Run on Git repository "{repository.name}"...', logger=self.logger)

        try:
            git_repository_dry_run(repository, job_result=job_result, logger=self.logger)
        finally:
            job_result.log(
                f"Repository dry run completed in {job_result.duration}",
                level_choice=LogLevelChoices.LOG_INFO,
                logger=self.logger,
            )


jobs = [GitRepositorySync, GitRepositoryDryRun]
register_jobs(*jobs)
