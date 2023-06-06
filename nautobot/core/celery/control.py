import logging
import os
import shutil

from celery.worker.control import control_command

from django.conf import settings


logger = logging.getLogger(__name__)


@control_command(args=[("repository_pk", str), ("head", str)])
def refresh_git_repository(state, repository_pk, head):
    """
    Celery worker control event to ensure that all active workers have the correct head for a given Git repository.
    """
    from nautobot.extras.datasources.git import ensure_git_repository, refresh_code_from_repository
    from nautobot.extras.models import GitRepository

    try:
        repository = GitRepository.objects.get(pk=repository_pk)
        # Refresh the repository on disk
        ensure_git_repository(repository, head=head, logger=logger)
        refresh_code_from_repository(repository.slug, consumer=state.consumer if state is not None else None)

        return {"ok": {"head": repository.current_head}}
    except Exception as exc:
        logger.error("%s", exc)
        return {"error": str(exc)}


@control_command(args=["repository_slug", str])
def discard_git_repository(state, repository_slug):
    """
    Celery worker control even to ensure that all active workers unload a given Git repository and delete it from disk.
    """
    from nautobot.extras.datasources.git import refresh_code_from_repository

    filesystem_path = os.path.join(settings.GIT_ROOT, repository_slug)
    if os.path.isdir(filesystem_path):
        shutil.rmtree(filesystem_path)
    # Unload any code from this repository
    refresh_code_from_repository(
        repository_slug, consumer=state.consumer if state is not None else None, skip_reimport=True
    )
