"""Registry-related APIs for datasources."""
from extras.choices import JobResultStatusChoices, LogLevelChoices
from extras.context_managers import change_logging
from extras.registry import registry


def get_datasource_contents(model_name):
    """Get the list of DatasourceContent entries registered for a given model name."""
    return sorted(registry['datasource_contents'].get(model_name, []))


def get_datasource_content_choices(model_name):
    """Get a list (suitable for use with forms.ChoiceField, etc.) of valid datasource content choices."""
    return sorted([(entry.token, entry.name) for entry in registry['datasource_contents'].get(model_name, [])])


def refresh_datasource_content(model_name, model, request, job_result):
    """Invoke the refresh callbacks for every content type registered for this model.

    Note that these callback functions are invoked regardless of whether a given model instance actually is flagged
    as providing each content type; this is intentional, as there may be cleanup required if a model was previously
    providing content but has now been changed to no longer provide that content.
    """
    job_result.log(f"Refreshing data provided by {model}...", level_choice=LogLevelChoices.LOG_INFO)
    job_result.save()
    with change_logging(request):
        for entry in get_datasource_contents(model_name):
            job_result.log(f"Refreshing {entry.name}...", level_choice=LogLevelChoices.LOG_INFO)
            try:
                entry.callback(model, job_result)
            except Exception as exc:
                job_result.log(f"Error while refreshing {entry.name}: {exc}", level_choice=LogLevelChoices.LOG_FAILURE)
                job_result.set_status(JobResultStatusChoices.STATUS_ERRORED)
            job_result.save()
        job_result.log(f"Data refresh from {model} complete!", level_choice=LogLevelChoices.LOG_INFO)
        job_result.save()
