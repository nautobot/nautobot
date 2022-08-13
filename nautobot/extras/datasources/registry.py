"""Registry-related APIs for datasources."""

from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices
from nautobot.extras.context_managers import change_logging, JobChangeContext
from nautobot.extras.registry import registry


def get_datasource_contents(model_name):
    """Get the list of DatasourceContent entries registered for a given model name."""
    return sorted(
        registry["datasource_contents"].get(model_name, []), key=lambda datasource: (datasource.weight, datasource.name)
    )


def get_datasource_content_choices(model_name):
    """Get a list (suitable for use with forms.ChoiceField, etc.) of valid datasource content choices."""
    return sorted(
        [(entry.content_identifier, entry.name) for entry in registry["datasource_contents"].get(model_name, [])]
    )


def refresh_datasource_content(model_name, record, request, job_result, delete=False):
    """Invoke the refresh callbacks for every content type registered for this model.

    Note that these callback functions are invoked regardless of whether a given model instance actually is flagged
    as providing each content type; this is intentional, as there may be cleanup required if a model was previously
    providing content but has now been changed to no longer provide that content.

    Args:
        model_name (str): Identifier of the datasource owner, such as "extras.gitrepository"
        record (models.Model): Datasource model instance, such as a GitRepository record
        request (HttpRequest): Initiating request for this refresh, optional, used for change logging if provided
        job_result (JobResult): Passed through to the callback functions to use with logging their actions.
        delete (bool): True if the record is being deleted; False if it is being created/updated.
    """
    job_result.log(f"Refreshing data provided by {record}...", level_choice=LogLevelChoices.LOG_INFO)
    job_result.save()
    if request:
        change_context = JobChangeContext(user=request.user)
        with change_logging(change_context):
            for entry in get_datasource_contents(model_name):
                job_result.log(f"Refreshing {entry.name}...", level_choice=LogLevelChoices.LOG_INFO)
                try:
                    entry.callback(record, job_result, delete=delete)
                except Exception as exc:
                    job_result.log(
                        f"Error while refreshing {entry.name}: {exc}", level_choice=LogLevelChoices.LOG_FAILURE
                    )
                    job_result.set_status(JobResultStatusChoices.STATUS_ERRORED)
                job_result.save()
            job_result.log(f"Data refresh from {record} complete!", level_choice=LogLevelChoices.LOG_INFO)
            job_result.save()
    else:
        for entry in get_datasource_contents(model_name):
            job_result.log(f"Refreshing {entry.name}...", level_choice=LogLevelChoices.LOG_INFO)
            try:
                entry.callback(record, job_result, delete=delete)
            except Exception as exc:
                job_result.log(f"Error while refreshing {entry.name}: {exc}", level_choice=LogLevelChoices.LOG_FAILURE)
                job_result.set_status(JobResultStatusChoices.STATUS_ERRORED)
            job_result.save()
        job_result.log(f"Data refresh from {record} complete!", level_choice=LogLevelChoices.LOG_INFO)
        job_result.save()
