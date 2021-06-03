"""Jobs functionality - consolidates and replaces legacy "custom scripts" and "reports" features."""
import inspect
import json
import logging
import os
import pkgutil
import shutil
import traceback
import warnings
from collections import OrderedDict

import yaml

from django import forms
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import transaction
from django.utils import timezone
from django.utils.functional import classproperty

from cacheops import cached
from django_rq import job

from .choices import JobResultStatusChoices, LogLevelChoices
from .context_managers import change_logging
from .datasources.git import ensure_git_repository
from .forms import JobForm
from .models import GitRepository
from .registry import registry

from nautobot.ipam.formfields import IPAddressFormField, IPNetworkFormField
from nautobot.ipam.validators import (
    MaxPrefixLengthValidator,
    MinPrefixLengthValidator,
    prefix_validator,
)
from nautobot.utilities.exceptions import AbortTransaction
from nautobot.utilities.forms import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
)


__all__ = [
    "Job",
    "BooleanVar",
    "ChoiceVar",
    "FileVar",
    "IntegerVar",
    "IPAddressVar",
    "IPAddressWithMaskVar",
    "IPNetworkVar",
    "MultiChoiceVar",
    "MultiObjectVar",
    "ObjectVar",
    "StringVar",
    "TextVar",
]

logger = logging.getLogger("nautobot.jobs")


class BaseJob:
    """Base model for jobs (reports, scripts).

    Users can subclass this directly if they want to provide their own base class for implementing multiple jobs
    with shared functionality; if no such sharing is required, use Job class instead.

    For backward compatibility with NetBox, this class has several APIs that can be implemented by the user:

    1. run(self, data, commit) - First method called when invoking a Job, can handle setup and parameter storage.
    2. test_*(self) - Any method matching this pattern will be called next
    3. post_run(self) - Last method called, will be called even in case of an exception during the above methods
    """

    class Meta:
        """
        Metaclass attributes - subclasses can define any or all of the following attributes:

        - name (str)
        - description (str)
        - commit_default (bool)
        - field_order (list)
        """

        pass

    @staticmethod
    def _results_struct():
        return OrderedDict(
            [
                ("success", 0),
                ("info", 0),
                ("warning", 0),
                ("failure", 0),
                ("log", []),
            ]
        )

    def __init__(self):
        self.logger = logging.getLogger(f"nautobot.jobs.{self.__class__.__name__}")

        self.request = None
        self.active_test = None
        self.failed = False
        self._job_result = None

        # Grab some info about the job
        self.source = inspect.getsource(self.__class__)

        # Compile test methods and initialize results skeleton
        self.test_methods = []

        for method_name in dir(self):
            if method_name.startswith("test_") and callable(getattr(self, method_name)):
                self.test_methods.append(method_name)

    def __str__(self):
        return self.name

    @classproperty
    def file_path(cls):
        return inspect.getfile(cls)

    @classproperty
    def class_path(cls):
        """
        Unique identifier of a specific Job class, in the form <source_grouping>/<module_name>/<ClassName>.

        Examples:
        local/my_script/MyScript
        plugins/my_plugin.jobs/MyPluginJob
        git.my-repository/myjob/MyJob
        """
        # TODO: it'd be nice if this were derived more automatically instead of needing this logic
        if cls in registry["plugin_jobs"]:
            source_grouping = "plugins"
        elif cls.file_path.startswith(settings.JOBS_ROOT):
            source_grouping = "local"
        elif cls.file_path.startswith(settings.GIT_ROOT):
            # $GIT_ROOT/<repo_slug>/jobs/job.py -> <repo_slug>
            source_grouping = ".".join(
                [
                    "git",
                    os.path.basename(os.path.dirname(os.path.dirname(cls.file_path))),
                ]
            )
        else:
            raise RuntimeError(
                f"Unknown/unexpected job file_path {cls.file_path}, should be one of "
                + ", ".join([settings.JOBS_ROOT, settings.GIT_ROOT])
            )

        return "/".join([source_grouping, cls.__module__, cls.__name__])

    @classproperty
    def class_path_dotted(cls):
        """
        Dotted class_path, suitable for use in things like Python logger names.
        """
        return cls.class_path.replace("/", ".")

    @classproperty
    def class_path_js_escaped(cls):
        """
        Escape various characters so that the class_path can be used as a jQuery selector.
        """
        return cls.class_path.replace("/", r"\/").replace(".", r"\.")

    @classproperty
    def name(cls):
        return getattr(cls.Meta, "name", cls.__name__)

    @classproperty
    def description(cls):
        return getattr(cls.Meta, "description", "")

    @classmethod
    def _get_vars(cls):
        vars = OrderedDict()
        for name, attr in cls.__dict__.items():
            if name not in vars and issubclass(attr.__class__, ScriptVariable):
                vars[name] = attr

        return vars

    @property
    def job_result(self):
        return self._job_result

    @job_result.setter
    def job_result(self, value):
        # Initialize job_result data format for our usage
        value.data = OrderedDict()
        value.data["total"] = self._results_struct()
        del value.data["total"]["log"]
        for method_name in self.test_methods:
            value.data[method_name] = self._results_struct()
        # Only initialize results for run and post_run if they're actually implemented
        if self.run.__func__ != BaseJob.run:
            value.data["run"] = self._results_struct()
        if self.post_run.__func__ != BaseJob.post_run:
            value.data["post_run"] = self._results_struct()

        self._job_result = value

    @property
    def results(self):
        """
        The results (log messages and final output) generated by this job.

        {
            "total": {
                "success": 0,
                "info": 3,
                "warning": 6,
                "failure": 9,
            }
            "run": {
                "success": 0,
                "info": 1,
                "warning": 2,
                "failure": 3,
                "log": [
                    (timestamp, level, object_name, object_url, message),
                    (timestamp, level, object_name, object_url, message),
                    ...
                ],
            },
            "test_function": {
                "success": 0,
                "info": 1,
                "warning": 2,
                "failure": 3,
                "log": [
                    (timestamp, level, object_name, object_url, message),
                    (timestamp, level, object_name, object_url, message),
                    ...
                ],
            },
            "post_run": {
                "success": 0,
                "info": 1,
                "warning": 2,
                "failure": 3,
                "log": [
                    (timestamp, level, object_name, object_url, message),
                    (timestamp, level, object_name, object_url, message),
                    ...
                ],
            },
            "output": "...",
        }
        """
        return self.job_result.data if self.job_result else None

    def as_form(self, data=None, files=None, initial=None):
        """
        Return a Django form suitable for populating the context data required to run this Job.
        """
        fields = {name: var.as_field() for name, var in self._get_vars().items()}
        FormClass = type("JobForm", (JobForm,), fields)

        form = FormClass(data, files, initial=initial)

        # Set initial "commit" checkbox state based on the Meta parameter
        form.fields["_commit"].initial = getattr(self.Meta, "commit_default", True)

        field_order = getattr(self.Meta, "field_order", None)

        if field_order:
            form.order_fields(field_order)

        return form

    def run(self, data, commit):
        """
        Method invoked when this Job is run, before any "test_*" methods.
        """
        pass

    def post_run(self):
        """
        Method invoked after "run()" and all "test_*" methods.
        """
        pass

    # Logging

    def _log(self, obj, message, level_choice=LogLevelChoices.LOG_DEFAULT):
        """
        Log a message. Do not call this method directly; use one of the log_* wrappers below.
        """
        self.job_result.log(
            message,
            obj=obj,
            level_choice=level_choice,
            grouping=self.active_test,
            logger=self.logger,
        )

    def log(self, message):
        """
        Log a generic message which is not associated with a particular object.
        """
        self._log(None, message, level_choice=LogLevelChoices.LOG_DEFAULT)

    def log_debug(self, message):
        """
        Log a debug message which is not associated with a particular object.
        """
        self._log(None, message, level_choice=LogLevelChoices.LOG_DEFAULT)

    def log_success(self, obj=None, message=None):
        """
        Record a successful test against an object. Logging a message is optional.
        """
        self._log(obj, message, level_choice=LogLevelChoices.LOG_SUCCESS)

    def log_info(self, obj=None, message=None):
        """
        Log an informational message.
        """
        self._log(obj, message, level_choice=LogLevelChoices.LOG_INFO)

    def log_warning(self, obj=None, message=None):
        """
        Log a warning.
        """
        self._log(obj, message, level_choice=LogLevelChoices.LOG_WARNING)

    def log_failure(self, obj=None, message=None):
        """
        Log a failure. Calling this method will automatically mark the overall job as failed.
        """
        self._log(obj, message, level_choice=LogLevelChoices.LOG_FAILURE)
        self.failed = True

    # Convenience functions

    def load_yaml(self, filename):
        """
        Return data from a YAML file
        """
        file_path = os.path.join(os.path.dirname(self.file_path), filename)
        with open(file_path, "r") as datafile:
            data = yaml.safe_load(datafile)

        return data

    def load_json(self, filename):
        """
        Return data from a JSON file
        """
        file_path = os.path.join(os.path.dirname(self.file_path), filename)
        with open(file_path, "r") as datafile:
            data = json.load(datafile)

        return data


class Job(BaseJob):
    """
    Classes which inherit from this model will appear in the list of available jobs.
    """


#
# Script variables
#


class ScriptVariable:
    """
    Base model for script variables
    """

    form_field = forms.CharField

    def __init__(self, label="", description="", default=None, required=True, widget=None):

        # Initialize field attributes
        if not hasattr(self, "field_attrs"):
            self.field_attrs = {}
        if label:
            self.field_attrs["label"] = label
        if description:
            self.field_attrs["help_text"] = description
        if default:
            self.field_attrs["initial"] = default
        if widget:
            self.field_attrs["widget"] = widget
        self.field_attrs["required"] = required

    def as_field(self):
        """
        Render the variable as a Django form field.
        """
        form_field = self.form_field(**self.field_attrs)
        if not isinstance(form_field.widget, forms.CheckboxInput):
            if form_field.widget.attrs and "class" in form_field.widget.attrs.keys():
                form_field.widget.attrs["class"] += " form-control"
            else:
                form_field.widget.attrs["class"] = "form-control"

        return form_field


class StringVar(ScriptVariable):
    """
    Character string representation. Can enforce minimum/maximum length and/or regex validation.
    """

    def __init__(self, min_length=None, max_length=None, regex=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Optional minimum/maximum lengths
        if min_length:
            self.field_attrs["min_length"] = min_length
        if max_length:
            self.field_attrs["max_length"] = max_length

        # Optional regular expression validation
        if regex:
            self.field_attrs["validators"] = [
                RegexValidator(
                    regex=regex,
                    message="Invalid value. Must match regex: {}".format(regex),
                    code="invalid",
                )
            ]


class TextVar(ScriptVariable):
    """
    Free-form text data. Renders as a <textarea>.
    """

    form_field = forms.CharField

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.field_attrs["widget"] = forms.Textarea


class IntegerVar(ScriptVariable):
    """
    Integer representation. Can enforce minimum/maximum values.
    """

    form_field = forms.IntegerField

    def __init__(self, min_value=None, max_value=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Optional minimum/maximum values
        if min_value:
            self.field_attrs["min_value"] = min_value
        if max_value:
            self.field_attrs["max_value"] = max_value


class BooleanVar(ScriptVariable):
    """
    Boolean representation (true/false). Renders as a checkbox.
    """

    form_field = forms.BooleanField

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Boolean fields cannot be required
        self.field_attrs["required"] = False


class ChoiceVar(ScriptVariable):
    """
    Select one of several predefined static choices, passed as a list of two-tuples. Example:

        color = ChoiceVar(
            choices=(
                ('#ff0000', 'Red'),
                ('#00ff00', 'Green'),
                ('#0000ff', 'Blue')
            )
        )
    """

    form_field = forms.ChoiceField

    def __init__(self, choices, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set field choices
        self.field_attrs["choices"] = choices


class MultiChoiceVar(ChoiceVar):
    """
    Like ChoiceVar, but allows for the selection of multiple choices.
    """

    form_field = forms.MultipleChoiceField


class ObjectVar(ScriptVariable):
    """
    A single object within Nautobot.

    :param model: The Nautobot model being referenced
    :param display_field: The attribute of the returned object to display in the selection list (default: 'name')
    :param query_params: A dictionary of additional query parameters to attach when making REST API requests (optional)
    :param null_option: The label to use as a "null" selection option (optional)
    """

    form_field = DynamicModelChoiceField

    def __init__(
        self,
        model=None,
        queryset=None,
        display_field="display",
        query_params=None,
        null_option=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        # Set the form field's queryset. Support backward compatibility for the "queryset" argument for now.
        if model is not None:
            self.field_attrs["queryset"] = model.objects.all()
        elif queryset is not None:
            warnings.warn(
                f'{self}: Specifying a queryset for ObjectVar is no longer supported. Please use "model" instead.'
            )
            self.field_attrs["queryset"] = queryset
        else:
            raise TypeError("ObjectVar must specify a model")

        self.field_attrs.update(
            {
                "display_field": display_field,
                "query_params": query_params,
                "null_option": null_option,
            }
        )


class MultiObjectVar(ObjectVar):
    """
    Like ObjectVar, but can represent one or more objects.
    """

    form_field = DynamicModelMultipleChoiceField


class FileVar(ScriptVariable):
    """
    An uploaded file.
    """

    form_field = forms.FileField


class IPAddressVar(ScriptVariable):
    """
    An IPv4 or IPv6 address without a mask.
    """

    form_field = IPAddressFormField


class IPAddressWithMaskVar(ScriptVariable):
    """
    An IPv4 or IPv6 address with a mask.
    """

    form_field = IPNetworkFormField


class IPNetworkVar(ScriptVariable):
    """
    An IPv4 or IPv6 prefix.
    """

    form_field = IPNetworkFormField

    def __init__(self, min_prefix_length=None, max_prefix_length=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set prefix validator and optional minimum/maximum prefix lengths
        self.field_attrs["validators"] = [prefix_validator]
        if min_prefix_length is not None:
            self.field_attrs["validators"].append(MinPrefixLengthValidator(min_prefix_length))
        if max_prefix_length is not None:
            self.field_attrs["validators"].append(MaxPrefixLengthValidator(max_prefix_length))


def is_job(obj):
    """
    Returns True if the given object is a Job subclass.
    """
    from .scripts import Script, BaseScript
    from .reports import Report

    try:
        return issubclass(obj, Job) and obj not in [Job, Script, BaseScript, Report]
    except TypeError:
        return False


def is_variable(obj):
    """
    Returns True if the object is a ScriptVariable instance.
    """
    return isinstance(obj, ScriptVariable)


def get_jobs():
    """
    Compile a dictionary of all jobs available across all modules in the jobs path(s).

    Returns an OrderedDict:

    {
        "local": {
            <module_name>: {
                "name": <human-readable module name>,
                "jobs": {
                   <class_name>: <job_class>,
                   <class_name>: <job_class>,
                   ...
                },
            },
            <module_name>: { ... },
            ...
        },
        "git.<repository-slug>": {
            <module_name>: { ... },
        },
        ...
        "plugins": {
            <module_name>: { ... },
        }
    }
    """
    jobs = OrderedDict()

    paths = _get_job_source_paths()

    # Iterate over all groupings (local, git.<slug1>, git.<slug2>, etc.)
    for grouping, path_list in paths.items():
        # Iterate over all modules (Python files) found in any of the directory paths identified for the given grouping
        for importer, module_name, _ in pkgutil.iter_modules(path_list):
            try:
                # Dynamically import this module to make its contents (job(s)) available to Python
                module = importer.find_module(module_name).load_module(module_name)
            except Exception as exc:
                logger.error(f"Unable to load job {module_name}: {exc}")
                continue

            # For each module, we construct a dict {"name": module_name, "jobs": {"job_name": job_class, ...}}
            human_readable_name = module.name if hasattr(module, "name") else module_name
            module_jobs = {"name": human_readable_name, "jobs": OrderedDict()}
            # Get all Job subclasses (which includes Script and Report subclasses as well) in this module,
            # and add them to the dict
            for name, cls in inspect.getmembers(module, is_job):
                module_jobs["jobs"][name] = cls

            # If there were any Job subclasses found, add the module_jobs dict to the overall jobs dict
            # (otherwise skip it since there aren't any jobs in this module to report)
            if module_jobs["jobs"]:
                jobs.setdefault(grouping, {})[module_name] = module_jobs

    # Add jobs from plugins (which were already imported at startup)
    for cls in registry["plugin_jobs"]:
        module = inspect.getmodule(cls)
        human_readable_name = module.name if hasattr(module, "name") else module.__name__
        jobs.setdefault("plugins", {}).setdefault(module.__name__, {"name": human_readable_name, "jobs": OrderedDict()})
        jobs["plugins"][module.__name__]["jobs"][cls.__name__] = cls

    return jobs


def _get_job_source_paths():
    """
    Helper function to get_jobs().

    Constructs a dict of {"grouping": [filesystem_path, ...]}.
    Current groupings are "local", "git.<repository_slug>".
    Plugin jobs aren't loaded dynamically from a source_path and so are not included in this function
    """
    paths = {}
    # Locally installed jobs
    if settings.JOBS_ROOT and os.path.exists(settings.JOBS_ROOT):
        paths.setdefault("local", []).append(settings.JOBS_ROOT)

    # Jobs derived from Git repositories
    if settings.GIT_ROOT and os.path.isdir(settings.GIT_ROOT):
        for repository_record in GitRepository.objects.all():
            if "extras.job" not in repository_record.provided_contents:
                # This repository isn't marked as containing jobs that we should use.
                continue

            try:
                # In the case where we have multiple Nautobot instances, or multiple RQ worker instances,
                # they are not required to share a common filesystem; therefore, we may need to refresh our local clone
                # of the Git repository to ensure that it is in sync with the latest repository clone from any instance.
                ensure_git_repository(
                    repository_record,
                    head=repository_record.current_head,
                    logger=logger,
                )
            except Exception as exc:
                logger.error(f"Error during local clone of Git repository {repository_record}: {exc}")
                continue

            jobs_path = os.path.join(repository_record.filesystem_path, "jobs")
            if os.path.isdir(jobs_path):
                paths[f"git.{repository_record.slug}"] = [jobs_path]
            else:
                logger.warning(f"Git repository {repository_record} is configured to provide jobs, but none are found!")

        # TODO: when a Git repo is deleted or its slug is changed, we update the local filesystem
        # (see extras/signals.py, extras/models/datasources.py), but as noted above, there may be multiple filesystems
        # involved, so not all local clones of deleted Git repositories may have been deleted yet.
        # For now, if we encounter a "leftover" Git repo here, we delete it now.
        for git_slug in os.listdir(settings.GIT_ROOT):
            git_path = os.path.join(settings.GIT_ROOT, git_slug)
            if not os.path.isdir(git_path):
                logger.warning(
                    f"Found non-directory {git_slug} in {settings.GIT_ROOT}. Only Git repositories should exist here."
                )
            elif not os.path.isdir(os.path.join(git_path, ".git")):
                logger.warning(f"Directory {git_slug} in {settings.GIT_ROOT} does not appear to be a Git repository.")
            elif not GitRepository.objects.filter(slug=git_slug):
                logger.warning(f"Deleting unmanaged (leftover?) repository at {git_path}")
                shutil.rmtree(git_path)

    return paths


@cached(timeout=60)
def get_job_classpaths():
    """
    Get a list of all known Job class_path strings.

    This is used as a cacheable, light-weight alternative to calling get_jobs() or get_job()
    when all that's needed is to verify whether a given job exists.
    """
    jobs_dict = get_jobs()
    result = set()
    for grouping_name, modules_dict in jobs_dict.items():
        for module_name in modules_dict:
            for class_name in modules_dict[module_name]["jobs"]:
                result.add(f"{grouping_name}/{module_name}/{class_name}")
    return result


def get_job(class_path):
    """
    Retrieve a specific job class by its class_path.

    Note that this is built atop get_jobs() and so is not a particularly light-weight API;
    if all you need to do is to verify whether a given class_path exists, use get_job_classpaths() instead.

    Returns None if not found.
    """
    try:
        grouping_name, module_name, class_name = class_path.split("/", 2)
    except ValueError:
        logger.error(f'Invalid class_path value "{class_path}"')
        return None

    jobs = get_jobs()
    return jobs.get(grouping_name, {}).get(module_name, {}).get("jobs", {}).get(class_name, None)


@job("default")
def run_job(data, request, job_result, commit=True, *args, **kwargs):
    """
    Helper function to call the "run()", "test_*()", and "post_run" methods on a Job.

    This gets around the inability to pickle an instance method for queueing into the background processor.
    """
    job_class = get_job(job_result.name)
    if not job_class:
        job_result.log(
            f'Unable to locate job "{job_result.name}" to run it!',
            level_choice=LogLevelChoices.LOG_FAILURE,
            grouping="initialization",
            logger=logger,
        )
        job_result.status = JobResultStatusChoices.STATUS_ERRORED
        job_result.completed = timezone.now()
        job_result.save()
        return False
    job = job_class()
    job.job_result = job_result

    # TODO: validate that all args required by this job are set in the data or else log helpful errors?

    job.logger.info(f"Running job (commit={commit})")

    job_result.status = JobResultStatusChoices.STATUS_RUNNING
    job_result.save()

    # Add any files to the form data
    if request:
        files = request.FILES
        for field_name, fileobj in files.items():
            data[field_name] = fileobj

    # Add the current request as a property of the job
    job.request = request

    def _run_job():
        """
        Core job execution task.

        We capture this within a subfunction to allow for conditionally wrapping it with the change_logging
        context manager (which is only relevant if commit == True).
        """
        job.results["output"] = ""
        try:
            with transaction.atomic():
                # Script-like behavior
                job.active_test = "run"
                output = job.run(data=data, commit=commit)
                if output:
                    job.results["output"] += "\n" + str(output)

                # Report-like behavior
                for method_name in job.test_methods:
                    job.active_test = method_name
                    output = getattr(job, method_name)()
                    if output:
                        job.results["output"] += "\n" + str(output)

                if job.failed:
                    job.logger.warning("job failed")
                    job_result.set_status(JobResultStatusChoices.STATUS_FAILED)
                else:
                    job.logger.info("job completed successfully")
                    job_result.set_status(JobResultStatusChoices.STATUS_COMPLETED)

                if not commit:
                    raise AbortTransaction()

        except AbortTransaction:
            job.log_info(message="Database changes have been reverted automatically.")

        except Exception as exc:
            stacktrace = traceback.format_exc()
            job.log_failure(message=f"An exception occurred: `{type(exc).__name__}: {exc}`\n```\n{stacktrace}\n```")
            job.log_info(message="Database changes have been reverted due to error.")
            job_result.set_status(JobResultStatusChoices.STATUS_ERRORED)

        finally:
            job_result.save()

        # Perform any post-run tasks
        job.active_test = "post_run"
        output = job.post_run()
        if output:
            job.results["output"] += "\n" + str(output)

        job_result.completed = timezone.now()
        job_result.save()

        job.logger.info(f"Job completed in {job_result.duration}")

    # Execute the job. If commit == True, wrap it with the change_logging context manager to ensure we
    # process change logs, webhooks, etc.
    if commit:
        with change_logging(request):
            _run_job()
    else:
        _run_job()
