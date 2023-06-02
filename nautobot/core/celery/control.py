import logging
import sys

from celery.worker.control import control_command

from django.conf import settings


logger = logging.getLogger(__name__)


@control_command(
    args=[("repository_pk", str), ("head", str)]
)
def refresh_git_repository(state, repository_pk, head):
    """
    Celery worker control event to ensure that all active workers have the correct head for a given Git repository.
    """
    from nautobot.core.celery import app
    from nautobot.extras.datasources.git import ensure_git_repository
    from nautobot.extras.models import GitRepository

    try:
        repository = GitRepository.objects.get(pk=repository_pk)
        # Refresh the repository on disk
        changed = ensure_git_repository(repository, head=head, logger=logger)
        if changed:
            # Unload modules and tasks/jobs previously provided by the repository
            for module_name in sys.modules.keys():
                if module_name == repository.slug or module_name.startswith(f"{repository.slug}."):
                    logger.debug("Unloading module %s", module_name)
                    del sys.modules[module_name]

            for task_name in app.tasks.keys():
                if task_name.startswith(f"{repository.slug}."):
                    logger.debug("Unregistering task %s", task_name)
                    app.tasks.unregister(task_name)

        if "extras.job" in repository.provided_contents:
            if settings.GIT_ROOT not in sys.path:
                sys.path.append(settings.GIT_ROOT)
            logger.debug("Importing Jobs from %s.jobs in GIT_ROOT", repository.slug)
            app.loader.import_task_module(f"{repository.slug}.jobs")

        return {"ok": {"head": repository.current_head}}
    except Exception as exc:
        logger.error("%s", exc)
        return {"error": str(exc)}
