from nautobot.core.celery import app, register_jobs
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

        self.logger.info(f'Creating/refreshing local copy of Git repository "{repository.name}"...')

        try:
            ensure_git_repository(repository, logger=self.logger)
            refresh_datasource_content("extras.gitrepository", repository, user, job_result, delete=False)
            # Given that the above succeeded, tell all workers (including ourself) to call ensure_git_repository()
            app.control.broadcast("refresh_git_repository", repository_pk=repository.pk, head=repository.current_head)
        finally:
            self.logger.info(f"Repository synchronization completed in {job_result.duration}")


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
        self.logger.info(f'Performing a Dry Run on Git repository "{repository.name}"...')

        try:
            git_repository_dry_run(repository, logger=self.logger)
        finally:
            self.logger.info(f"Repository dry run completed in {job_result.duration}")


jobs = [GitRepositorySync, GitRepositoryDryRun]
register_jobs(*jobs)
