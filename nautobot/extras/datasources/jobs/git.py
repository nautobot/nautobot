import os

from django.conf import settings

from nautobot.core.celery import register_jobs
from nautobot.extras.choices import LogLevelChoices
from nautobot.extras.datasources import ensure_git_repository, refresh_datasource_content
from nautobot.extras.models import GitRepository
from nautobot.extras.jobs import Job
from nautobot.users.models import User


class GitRepositoryPullAndRefreshData(Job):
    def run(self, repository_pk):
        job_result = self.get_job_result()
        user = job_result.user

        # Retrieve the Git repo or immediately fail.
        try:
            repository_record = GitRepository.ojects.get(pk=repository_pk)
        except GitRepository.DoesNotExist:
            job_result.log(
                f"No GitRepository {repository_pk} found!",
                level_choice=LogLevelChoices.LOG_FAILURE,
                logger=self.logger,
            )

        job_result.log(
            f'Creating/refreshing local copy of Git repository "{repository_record.name}"...',
            logger=self.logger,
        )

        try:
            if not os.path.exists(settings.GIT_ROOT):
                os.makedirs(settings.GIT_ROOT)

            ensure_git_repository(
                repository_record,
                job_result=job_result,
                logger=logger,
            )

            job_result.log(
                f'The current Git repository hash is "{repository_record.current_head}"',
            )

            refresh_datasource_content("extras.gitrepository", repository_record, user, job_result, delete=False)

        except Exception as exc:
            job_result.log(
                f"Error while refreshing {repository_record.name}: {exc}",
                level_choice=LogLevelChoices.LOG_FAILURE,
            )
            raise

        finally:
            log_job_result_final_status(job_result, "synchronization")


jobs = [GitRepositoryPullAndRefreshData]
register_jobs(*jobs)
