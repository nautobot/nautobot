"""Jobs functionality - consolidates and replaces legacy "custom scripts" and "reports" features."""

from collections import OrderedDict
import functools
import inspect
import json
import logging
import os
import sys
import tempfile
from textwrap import dedent
from typing import final
import warnings

from billiard.einfo import ExceptionInfo
from celery.exceptions import Ignore, Reject
from celery.utils.log import get_task_logger
from db_file_storage.form_widgets import DBClearableFileInput
from django import forms
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import RegexValidator
from django.db.models import Model
from django.db.models.query import QuerySet
from django.forms import ValidationError
from django.utils.functional import classproperty
import netaddr
import yaml

from nautobot.core.celery import import_jobs, nautobot_task
from nautobot.core.events import publish_event
from nautobot.core.forms import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    JSONField,
)
from nautobot.core.forms.widgets import ClearableFileInput
from nautobot.core.utils.config import get_settings_or_config
from nautobot.core.utils.logging import sanitize
from nautobot.core.utils.lookup import get_model_from_name
from nautobot.extras.choices import (
    JobResultStatusChoices,
    ObjectChangeActionChoices,
    ObjectChangeEventContextChoices,
)
from nautobot.extras.context_managers import web_request_context
from nautobot.extras.forms import JobForm
from nautobot.extras.models import (
    FileProxy,
    Job as JobModel,
    JobHook,
    JobQueue,
    JobResult,
    ObjectChange,
)
from nautobot.extras.registry import registry
from nautobot.extras.utils import change_logged_models_queryset
from nautobot.ipam.formfields import IPAddressFormField, IPNetworkFormField
from nautobot.ipam.validators import (
    MaxPrefixLengthValidator,
    MinPrefixLengthValidator,
    prefix_validator,
)

User = get_user_model()


__all__ = [
    "BooleanVar",
    "ChoiceVar",
    "FileVar",
    "IPAddressVar",
    "IPAddressWithMaskVar",
    "IPNetworkVar",
    "IntegerVar",
    "JSONVar",
    "Job",
    "MultiChoiceVar",
    "MultiObjectVar",
    "ObjectVar",
    "StringVar",
    "TextVar",
]

logger = logging.getLogger(__name__)


class RunJobTaskFailed(Exception):
    """Celery task failed for some reason."""


class BaseJob:
    """Base model for jobs.

    Users can subclass this directly if they want to provide their own base class for implementing multiple jobs
    with shared functionality; if no such sharing is required, use Job class instead.

    Jobs must define at minimum a run method.
    """

    class Meta:
        """
        Metaclass attributes - subclasses can define any or all of the following attributes:

        - name (str)
        - description (str)
        - approval_required (bool)
        - dryrun_default (bool)
        - field_order (list)
        - has_sensitive_variables (bool)
        - hidden (bool)
        - soft_time_limit (int)
        - task_queues (list)
        - template_name (str)
        - time_limit (int)
        - is_singleton (bool)
        """

    def __init__(self):
        self.logger = get_task_logger(self.__module__)
        self._failed = False

    def __call__(self, *args, **kwargs):
        # Attempt to resolve serialized data back into original form by creating querysets or model instances
        # If we fail to find any objects, we consider this a job execution error, and fail.
        # This might happen when a job sits on the queue for a while (i.e. scheduled) and data has changed
        # or it might be bad input from an API request, or manual execution.
        try:
            deserialized_kwargs = self.deserialize_data(kwargs)
        except Exception as err:
            self.logger.exception("Error deserializing kwargs")
            raise RunJobTaskFailed("Error initializing job") from err

        if isinstance(self, JobHookReceiver):
            change_context = ObjectChangeEventContextChoices.CONTEXT_JOB_HOOK
        else:
            change_context = ObjectChangeEventContextChoices.CONTEXT_JOB

        with web_request_context(user=self.user, context_detail=self.class_path, context=change_context):
            if self.celery_kwargs.get("nautobot_job_profile", False) is True:
                import cProfile

                # TODO: This should probably be available as a file download rather than dumped to the hard drive.
                # Pending this: https://github.com/nautobot/nautobot/issues/3352
                profiling_path = f"{tempfile.gettempdir()}/nautobot-jobresult-{self.job_result.id}.pstats"
                self.logger.info(
                    "Writing profiling information to %s.", profiling_path, extra={"grouping": "initialization"}
                )

                with cProfile.Profile() as pr:
                    try:
                        output = self.run(*args, **deserialized_kwargs)
                    except Exception as err:
                        pr.dump_stats(profiling_path)
                        raise err
                    else:
                        pr.dump_stats(profiling_path)
                        return output
            else:
                return self.run(*args, **deserialized_kwargs)

    def __str__(self):
        return str(self.name)

    def fail(self, msg, *args, **kwargs):
        """Mark this job as failed without immediately raising an exception and aborting."""
        # Instead of failing in "fail" grouping, fail in the parent function's grouping by default
        self.logger.failure(msg, *args, stacklevel=2, **kwargs)
        self._failed = True

    def before_start(self, task_id, args, kwargs):
        """Handler called before the task starts.

        Arguments:
            task_id (str): Unique id of the task to execute.
            args (Tuple): Original arguments for the task to execute.
            kwargs (Dict): Original keyword arguments for the task to execute.

        Returns:
            (Any): The return value of this handler is ignored normally, **except** if `self.fail()` is called herein,
                in which case the return value will be used as the overall JobResult return value
                since `self.run()` will **not** be called in such a case.
        """

    def run(self, *args, **kwargs):
        """
        Method invoked when this Job is run.
        """
        raise NotImplementedError("Jobs must define the run method.")

    def on_success(self, retval, task_id, args, kwargs):
        """Success handler.

        Run by the worker if the task executes successfully.

        Arguments:
            retval (Any): The return value of the task.
            task_id (str): Unique id of the executed task.
            args (Tuple): Original arguments for the executed task.
            kwargs (Dict): Original keyword arguments for the executed task.

        Returns:
            (None): The return value of this handler is ignored.
        """

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Retry handler.

        This is run by the worker when the task is to be retried.

        Arguments:
            exc (Exception): The exception sent to :meth:`retry`.
            task_id (str): Unique id of the retried task.
            args (Tuple): Original arguments for the retried task.
            kwargs (Dict): Original keyword arguments for the retried task.
            einfo (~billiard.einfo.ExceptionInfo): Exception information.

        Returns:
            (None): The return value of this handler is ignored.
        """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Error handler.

        This is run by the worker when the task fails.

        Arguments:
            exc (Any): Exception raised by the task (if any) **or** return value from the task, if it failed cleanly,
                such as if the Job called `self.fail()` rather than raising an exception.
            task_id (str): Unique id of the failed task.
            args (Tuple): Original arguments for the task that failed.
            kwargs (Dict): Original keyword arguments for the task that failed.
            einfo (~billiard.einfo.ExceptionInfo): Exception information, or None.

        Returns:
            (None): The return value of this handler is ignored.
        """

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """
        Handler called after the task returns.

        Arguments:
            status (str): Current task state.
            retval (Any): Task return value/exception.
            task_id (str): Unique id of the task.
            args (tuple):  Original arguments for the task that returned.
            kwargs (dict): Original keyword arguments for the task that returned.
            einfo (ExceptionInfo): ExceptionInfo instance, containing the traceback (if any).

        Returns:
            (None): The return value of this handler is ignored.
        """

    # See https://github.com/PyCQA/pylint-django/issues/240 for why we have a pylint disable on each classproperty below

    @final
    @classproperty
    def singleton_cache_key(cls) -> str:  # pylint: disable=no-self-argument
        """Cache key for singleton jobs."""
        return f"nautobot.extras.jobs.running.{cls.class_path}"

    @final
    @classproperty
    def file_path(cls) -> str:  # pylint: disable=no-self-argument
        """Deprecated as of Nautobot 2.2.3."""
        return inspect.getfile(cls)

    @final
    @classproperty
    def class_path(cls) -> str:  # pylint: disable=no-self-argument
        """
        Unique identifier of a specific Job class, in the form <module_name>.<ClassName>.

        Examples:
        - my_script.MyScript - Local Job
        - nautobot.core.jobs.MySystemJob - System Job
        - my_plugin.jobs.MyPluginJob - App-provided Job
        - git_repository.jobs.myjob.MyJob - GitRepository Job
        """
        return f"{cls.__module__}.{cls.__name__}"  # pylint: disable=no-member

    @final
    @classproperty
    def class_path_dotted(cls) -> str:  # pylint: disable=no-self-argument
        """
        Dotted class_path, suitable for use in things like Python logger names.

        Deprecated as of Nautobot 2.0: just use .class_path instead.
        """
        return cls.class_path

    @final
    @classproperty
    def class_path_js_escaped(cls) -> str:  # pylint: disable=no-self-argument
        """
        Escape various characters so that the class_path can be used as a jQuery selector.
        """
        return cls.class_path.replace(".", r"\.")

    @final
    @classproperty
    def grouping(cls) -> str:  # pylint: disable=no-self-argument
        module = inspect.getmodule(cls)
        return getattr(module, "name", cls.__module__)

    @final
    @classmethod
    def _get_meta_attr_and_assert_type(cls, attr_name, default, expected_type):
        result = getattr(cls.Meta, attr_name, default)
        if not isinstance(result, expected_type):
            raise TypeError(f"Meta.{attr_name} should be {expected_type}, not {type(result)}")
        return result

    @final
    @classproperty
    def name(cls) -> str:  # pylint: disable=no-self-argument
        return cls._get_meta_attr_and_assert_type("name", cls.__name__, expected_type=str)  # pylint: disable=no-member

    @final
    @classproperty
    def description(cls) -> str:  # pylint: disable=no-self-argument
        return dedent(cls._get_meta_attr_and_assert_type("description", "", expected_type=str)).strip()

    @final
    @classproperty
    def description_first_line(cls) -> str:  # pylint: disable=no-self-argument
        if cls.description:  # pylint: disable=using-constant-test
            return cls.description.splitlines()[0]
        return ""

    @final
    @classproperty
    def dryrun_default(cls) -> bool:  # pylint: disable=no-self-argument
        return cls._get_meta_attr_and_assert_type("dryrun_default", False, expected_type=bool)

    @final
    @classproperty
    def hidden(cls) -> bool:  # pylint: disable=no-self-argument
        return cls._get_meta_attr_and_assert_type("hidden", False, expected_type=bool)

    @final
    @classproperty
    def field_order(cls):  # pylint: disable=no-self-argument
        return cls._get_meta_attr_and_assert_type("field_order", [], expected_type=(list, tuple))

    @final
    @classproperty
    def read_only(cls) -> bool:  # pylint: disable=no-self-argument
        return cls._get_meta_attr_and_assert_type("read_only", False, expected_type=bool)

    @final
    @classproperty
    def approval_required(cls) -> bool:  # pylint: disable=no-self-argument
        return cls._get_meta_attr_and_assert_type("approval_required", False, expected_type=bool)

    @final
    @classproperty
    def soft_time_limit(cls) -> int:  # pylint: disable=no-self-argument
        return cls._get_meta_attr_and_assert_type("soft_time_limit", 0, expected_type=int)

    @final
    @classproperty
    def time_limit(cls) -> int:  # pylint: disable=no-self-argument
        return cls._get_meta_attr_and_assert_type("time_limit", 0, expected_type=int)

    @final
    @classproperty
    def has_sensitive_variables(cls) -> bool:  # pylint: disable=no-self-argument
        return cls._get_meta_attr_and_assert_type("has_sensitive_variables", True, expected_type=bool)

    @final
    @classproperty
    def supports_dryrun(cls) -> bool:  # pylint: disable=no-self-argument
        return isinstance(getattr(cls, "dryrun", None), DryRunVar)

    @final
    @classproperty
    def task_queues(cls) -> list:  # pylint: disable=no-self-argument
        return cls._get_meta_attr_and_assert_type("task_queues", [], expected_type=(list, tuple))

    @final
    @classproperty
    def is_singleton(cls) -> bool:  # pylint: disable=no-self-argument
        return cls._get_meta_attr_and_assert_type("is_singleton", False, expected_type=bool)

    @final
    @classproperty
    def properties_dict(cls) -> dict:  # pylint: disable=no-self-argument
        """
        Return all relevant classproperties as a dict.

        Used for convenient rendering into job_edit.html via the `json_script` template tag.
        """
        return {
            "name": cls.name,
            "grouping": cls.grouping,
            "description": cls.description,
            "approval_required": cls.approval_required,
            "hidden": cls.hidden,
            "soft_time_limit": cls.soft_time_limit,
            "time_limit": cls.time_limit,
            "has_sensitive_variables": cls.has_sensitive_variables,
            "task_queues": cls.task_queues,
            "is_singleton": cls.is_singleton,
        }

    @final
    @classproperty
    def registered_name(cls) -> str:  # pylint: disable=no-self-argument
        """Deprecated - use class_path classproperty instead."""
        return f"{cls.__module__}.{cls.__name__}"  # pylint: disable=no-member

    @classmethod
    def _get_vars(cls):
        """
        Return dictionary of ScriptVariable attributes defined on this class or any of its base parent classes.

        The variables are sorted in the order that they were defined,
        with variables defined on base classes appearing before subclass variables.
        """
        cls_vars = {}
        # get list of base classes, including cls, in reverse method resolution order: [BaseJob, Job, cls]
        base_classes = reversed(inspect.getmro(cls))
        attr_names = [name for base in base_classes for name in base.__dict__.keys()]
        for name in attr_names:
            try:
                attr_class = getattr(cls, name, None).__class__
            except TypeError:
                pass
            if name not in cls_vars and issubclass(attr_class, ScriptVariable):
                cls_vars[name] = getattr(cls, name)

        return cls_vars

    @classmethod
    def _get_file_vars(cls):
        """Return an ordered dict of FileVar fields."""
        cls_vars = cls._get_vars()
        file_vars = OrderedDict()
        for name, attr in cls_vars.items():
            if isinstance(attr, FileVar):
                file_vars[name] = attr

        return file_vars

    @classmethod
    def as_form_class(cls):
        """
        Dynamically generate a Django form class corresponding to the variables in this Job.

        In most cases you should use `.as_form()` instead of calling this method directly.
        """
        fields = {name: var.as_field() for name, var in cls._get_vars().items()}
        return type("JobForm", (JobForm,), fields)

    @classmethod
    def as_form(cls, data=None, files=None, initial=None, approval_view=False):
        """
        Return a Django form suitable for populating the context data required to run this Job.

        `approval_view` will disable all fields from modification and is used to display the form
        during a approval review workflow.
        """

        form = cls.as_form_class()(data, files, initial=initial)
        form.fields["_profile"] = forms.BooleanField(
            required=False,
            initial=False,
            label="Profile job execution",
            help_text="Profiles the job execution using cProfile and outputs a report to /tmp/",
        )
        # If the class already exists there may be overrides, so we have to check this.
        try:
            job_model = JobModel.objects.get(module_name=cls.__module__, job_class_name=cls.__name__)
            is_singleton = job_model.is_singleton
        except JobModel.DoesNotExist:
            logger.warning("No Job instance found in the database corresponding to %s", cls.class_path)
            job_model = None
            is_singleton = cls.is_singleton

        if is_singleton:
            form.fields["_ignore_singleton_lock"] = forms.BooleanField(
                required=False,
                initial=False,
                label="Ignore singleton lock",
                help_text="Allow this singleton job to run even when another instance is already running",
            )

        if job_model is not None:
            job_queue_queryset = JobQueue.objects.filter(jobs=job_model)
            job_queue_params = {"jobs": [job_model.pk]}
        else:
            job_queue_queryset = JobQueue.objects.all()
            job_queue_params = {}

        # Initialize job_queue choices
        form.fields["_job_queue"] = DynamicModelChoiceField(
            queryset=job_queue_queryset,
            query_params=job_queue_params,
            required=False,
            help_text="The job queue to route this job to",
            label="Job queue",
        )

        dryrun_default = cls.dryrun_default
        if job_model is not None:
            form.fields["_job_queue"].initial = job_model.default_job_queue.pk
            if job_model.dryrun_default_override:
                dryrun_default = job_model.dryrun_default

        if cls.supports_dryrun and (not initial or "dryrun" not in initial):
            # Set initial "dryrun" checkbox state based on the Meta parameter
            form.fields["dryrun"].initial = dryrun_default
        if not settings.DEBUG:
            form.fields["_profile"].widget = forms.HiddenInput()

        # https://github.com/PyCQA/pylint/issues/3484
        if cls.field_order:  # pylint: disable=using-constant-test
            form.order_fields(cls.field_order)

        if approval_view:
            # Set `disabled=True` on all fields
            for _, field in form.fields.items():
                field.disabled = True

        # Ensure non-Job-specific fields are still last after applying field_order
        for field in ["_job_queue", "_profile", "_ignore_singleton_lock"]:
            if field not in form.fields:
                continue
            value = form.fields.pop(field)
            form.fields[field] = value

        return form

    @functools.cached_property
    def job_model(self):
        return JobModel.objects.get(module_name=self.__module__, job_class_name=self.__class__.__name__)

    @functools.cached_property
    def job_result(self):
        return JobResult.objects.get(id=self.request.id)

    @functools.cached_property
    def celery_kwargs(self):
        return self.job_result.celery_kwargs or {}

    @property
    def user(self):
        return getattr(self.job_result, "user", None)

    @staticmethod
    def serialize_data(data):
        """
        This method parses input data (from JobForm usually) and returns a dict which is safe to serialize

        Here we convert the QuerySet of a MultiObjectVar to a list of the pk's and the model instance
        of an ObjectVar into the pk value.

        These are converted back during job execution.
        """

        return_data = {}
        for field_name, value in data.items():
            # MultiObjectVar
            if isinstance(value, QuerySet):
                return_data[field_name] = list(value.values_list("pk", flat=True))
            # ObjectVar
            elif isinstance(value, Model):
                return_data[field_name] = value.pk
            # FileVar (Save each FileVar as a FileProxy)
            elif isinstance(value, UploadedFile):
                return_data[field_name] = BaseJob._save_file_to_proxy(value)
            # IPAddressVar, IPAddressWithMaskVar, IPNetworkVar
            elif isinstance(value, netaddr.ip.BaseIP):
                return_data[field_name] = str(value)
            # Everything else...
            else:
                return_data[field_name] = value

        return return_data

    # TODO: can the deserialize_data logic be moved to NautobotKombuJSONEncoder?
    @classmethod
    def deserialize_data(cls, data):
        """
        Given data input for a job execution, deserialize it by resolving object references using defined variables.

        This converts a list of pk's back into a QuerySet for MultiObjectVar instances and single pk values into
        model instances for ObjectVar.

        Note that when resolving querysets or model instances by their PK, we do not catch DoesNotExist
        exceptions here, we leave it up the caller to handle those cases. The normal job execution code
        path would consider this a failure of the job execution, as described in `nautobot.extras.jobs.run_job`.
        """
        cls_vars = cls._get_vars()
        return_data = {}

        if not isinstance(data, dict):
            raise TypeError("Data should be a dictionary.")

        for field_name, value in data.items():
            # If a field isn't a var, skip it (e.g. `_task_queue`).
            try:
                var = cls_vars[field_name]
            except KeyError:
                continue

            if value is None:
                if var.field_attrs.get("required"):
                    raise ValidationError(f"{field_name} is a required field")
                else:
                    return_data[field_name] = value
                    continue

            if isinstance(var, MultiObjectVar):
                queryset = var.field_attrs["queryset"].filter(pk__in=value)
                if queryset.count() < len(value):
                    # Not all objects found
                    found_pks = set(queryset.values_list("pk", flat=True))
                    not_found_pks = set(value).difference(found_pks)
                    raise queryset.model.DoesNotExist(
                        f"Failed to find requested objects for var {field_name}: [{', '.join(not_found_pks)}]"
                    )
                return_data[field_name] = var.field_attrs["queryset"].filter(pk__in=value)

            elif isinstance(var, ObjectVar):
                if isinstance(value, dict):
                    return_data[field_name] = var.field_attrs["queryset"].get(**value)
                else:
                    return_data[field_name] = var.field_attrs["queryset"].get(pk=value)
            elif isinstance(var, FileVar):
                return_data[field_name] = cls._load_file_from_proxy(value)
            # IPAddressVar is a netaddr.IPAddress object
            elif isinstance(var, IPAddressVar):
                return_data[field_name] = netaddr.IPAddress(value)
            # IPAddressWithMaskVar, IPNetworkVar are netaddr.IPNetwork objects
            elif isinstance(var, (IPAddressWithMaskVar, IPNetworkVar)):
                return_data[field_name] = netaddr.IPNetwork(value)
            else:
                return_data[field_name] = value

        return return_data

    @classmethod
    def validate_data(cls, data, files=None):
        cls_vars = cls._get_vars()

        if not isinstance(data, dict):
            raise ValidationError("Job data needs to be a dict")

        for k in data:
            if k not in cls_vars:
                raise ValidationError({k: "Job data contained an unknown property"})

        # defer validation to the form object
        f = cls.as_form(data=cls.deserialize_data(data), files=files)
        if not f.is_valid():
            raise ValidationError(f.errors)

        return f.cleaned_data

    @classmethod
    def prepare_job_kwargs(cls, job_kwargs):
        """Process dict and return kwargs that exist as ScriptVariables on this job."""
        job_vars = cls._get_vars()
        return {k: v for k, v in job_kwargs.items() if k in job_vars}

    @staticmethod
    def _load_file_from_proxy(pk):
        """Load a file proxy stored in the database by primary key.

        Args:
            pk (uuid): Primary key of the `FileProxy` to retrieve

        Returns:
            (File): A File-like object
        """
        fp = FileProxy.objects.get(pk=pk)
        return fp.file

    @staticmethod
    def _save_file_to_proxy(uploaded_file):
        """
        Save an uploaded file to the database as a file proxy and return the
        primary key.

        Args:
            uploaded_file (file): File handle of file to save to database

        Returns:
            (uuid): The pk of the `FileProxy` object
        """
        fp = FileProxy.objects.create(name=uploaded_file.name, file=uploaded_file)
        return fp.pk

    def _delete_file_proxies(self, *files_to_delete):
        """Given an unpacked list of primary keys for `FileProxy` objects, delete them.

        Args:
            files_to_delete (*args): List of primary keys to delete

        Returns:
            (int): number of objects deleted
        """
        files = FileProxy.objects.filter(pk__in=files_to_delete)
        num = 0
        for fp in files:
            fp.delete()  # Call delete() on each, so `FileAttachment` is reaped
            num += 1
        self.logger.debug("Deleted %d file proxies", num, extra={"grouping": "post_run"})
        return num

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

    def create_file(self, filename, content):
        """
        Create a file that can later be downloaded by users.

        Args:
            filename (str): Name of the file to create, including extension
            content (str, bytes): Content to populate the created file with.

        Raises:
            (ValueError): if the provided content exceeds JOB_CREATE_FILE_MAX_SIZE in length

        Returns:
            (FileProxy): record that was created
        """
        if isinstance(content, str):
            content = content.encode("utf-8")
        max_size = get_settings_or_config("JOB_CREATE_FILE_MAX_SIZE", fallback=10 << 20)
        actual_size = len(content)
        if actual_size > max_size:
            raise ValueError(f"Provided {actual_size} bytes of content, but JOB_CREATE_FILE_MAX_SIZE is {max_size}")
        fp = FileProxy.objects.create(
            name=filename, job_result=self.job_result, file=ContentFile(content, name=filename)
        )
        self.logger.info("Created file [%s](%s)", filename, fp.file.url)
        return fp


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
        if default is not None:
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
                    message=f"Invalid value. Must match regex: {regex}",
                    code="invalid",
                )
            ]


class TextVar(ScriptVariable):
    """
    Free-form text data. Renders as a `<textarea>`.
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


class DryRunVar(BooleanVar):
    """
    Special boolean variable that bypasses approval requirements if this is set to True on job execution.
    """

    description = "Check to run job in dryrun mode."

    def __init__(self, *args, **kwargs):
        # Default must be false unless overridden through `dryrun_default` meta attribute
        kwargs["default"] = False

        # Default description if one was not provided
        kwargs.setdefault("description", self.description)

        super().__init__(*args, **kwargs)


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

    Args:
        model (Model): The Nautobot model being referenced
        display_field (str): The attribute of the returned object to display in the selection list
        query_params (dict): Additional query parameters to attach when making REST API requests
        null_option (str): The label to use as a "null" selection option
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


class DatabaseFileField(forms.FileField):
    """Specialized `FileField` for use with `DatabaseFileStorage` storage backend."""

    widget = DBClearableFileInput


class BootstrapStyleFileField(forms.FileField):
    """File picker with UX bootstrap style and clearable checkbox."""

    widget = ClearableFileInput


class FileVar(ScriptVariable):
    """
    An uploaded file.
    """

    form_field = BootstrapStyleFileField


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


class JSONVar(ScriptVariable):
    """
    Like TextVar but with native serializing of JSON data.
    """

    form_field = JSONField


class JobHookReceiver(Job):
    """
    Base class for job hook receivers. Job hook receivers are jobs that are initiated
    from object changes and are not intended to be run from the UI or API like standard jobs.
    """

    object_change = ObjectVar(model=ObjectChange)

    def run(self, object_change):  # pylint: disable=arguments-differ
        """JobHookReceiver subclasses generally shouldn't need to override this method."""
        self.receive_job_hook(
            change=object_change,
            action=object_change.action,
            changed_object=object_change.changed_object,
        )

    def receive_job_hook(self, change, action, changed_object):
        """
        Method to be implemented by concrete JobHookReceiver subclasses.

        Args:
            change (ObjectChange): an instance of `nautobot.extras.models.ObjectChange`
            action (str): a string with the action performed on the changed object ("create", "update" or "delete")
            changed_object (Model): an instance of the object that was changed, or `None` if the object has been deleted
        """
        raise NotImplementedError


class JobButtonReceiver(Job):
    """
    Base class for job button receivers. Job button receivers are jobs that are initiated
    from UI buttons and are not intended to be run from the job form UI or API like standard jobs.
    """

    object_pk = StringVar()
    object_model_name = StringVar()

    def run(self, object_pk, object_model_name):  # pylint: disable=arguments-differ
        """JobButtonReceiver subclasses generally shouldn't need to override this method."""
        model = get_model_from_name(object_model_name)
        obj = model.objects.get(pk=object_pk)

        self.receive_job_button(obj=obj)

    def receive_job_button(self, obj):
        """
        Method to be implemented by concrete JobButtonReceiver subclasses.

        Args:
            obj (Model): an instance of the object that triggered this job
        """
        raise NotImplementedError


def is_job(obj):
    """
    Returns True if the given object is a Job subclass.
    """
    try:
        return issubclass(obj, Job) and obj not in [Job, JobHookReceiver, JobButtonReceiver]
    except TypeError:
        return False


def is_variable(obj):
    """
    Returns True if the object is a ScriptVariable instance.
    """
    return isinstance(obj, ScriptVariable)


def get_jobs(*, reload=False):
    """
    Compile a dictionary of all Job classes available at this time.

    Args:
        reload (bool): If True, reimport Jobs from `JOBS_ROOT` and all applicable GitRepositories.

    Returns:
        (dict): `{"class_path.Job1": <job_class>, "class_path.Job2": <job_class>, ...}`
    """
    if reload:
        import_jobs()

    return registry["jobs"]


def get_job(class_path, reload=False):
    """
    Retrieve a specific job class by its class_path (`<module_name>.<JobClassName>`).

    May return None if the job can't be imported.

    Args:
        reload (bool): If True, **and** the given class_path describes a JOBS_ROOT or GitRepository Job,
            then refresh **all** such Jobs before retrieving the job class.
    """
    if reload:
        if class_path.startswith("nautobot."):
            # System job - not reloadable
            reload = False
        if any(class_path.startswith(f"{app_name}.") for app_name in settings.PLUGINS):
            # App provided job - only reload if the app provides dynamic jobs
            app_config = apps.get_app_config(class_path.split(".")[0])
            reload = getattr(app_config, "provides_dynamic_jobs", False)
    jobs = get_jobs(reload=reload)
    return jobs.get(class_path, None)


def _prepare_job(job_class_path, request, kwargs) -> tuple[Job, dict]:
    """Helper method to run_job task, handling initial data setup and initialization before running a Job."""
    logger.debug("Preparing to run job %s for task %s", job_class_path, request.id)

    # Get the job code
    job_class = get_job(job_class_path, reload=True)
    if job_class is None:
        raise KeyError(f"Job class not found for class path {job_class_path}")
    job = job_class()
    job.request = request

    # Get the JobResult record to record results to
    try:
        job_result = JobResult.objects.get(id=request.id)
    except JobResult.DoesNotExist:
        job.logger.exception("Unable to find JobResult %s", request.id, extra={"grouping": "initialization"})
        raise

    # Get the JobModel record associated with this job
    try:
        job.job_model
    except JobModel.DoesNotExist:
        job.logger.exception(
            "Unable to find Job database record %s", job_class_path, extra={"grouping": "initialization"}
        )
        raise

    # Make sure it's valid to run this job - 1) is it enabled?
    if not job.job_model.enabled:
        job.logger.error(
            "Job %s is not enabled to be run!",
            job.job_model,
            extra={"object": job.job_model, "grouping": "initialization"},
        )
        raise RunJobTaskFailed(f"Job {job.job_model} is not enabled to be run!")
    # 2) if it's a singleton, is there any existing lock to be aware of?
    if job.job_model.is_singleton:
        is_running = cache.get(job.singleton_cache_key)
        if is_running:
            ignore_singleton_lock = job.celery_kwargs.get("nautobot_job_ignore_singleton_lock", False)
            if ignore_singleton_lock:
                job.logger.warning(
                    "Job %s is a singleton and already running, but singleton will be ignored because"
                    " `ignore_singleton_lock` is set.",
                    job.job_model,
                    extra={"object": job.job_model, "grouping": "initialization"},
                )
            else:
                # TODO 3.0: maybe change to logger.failure() and return cleanly, as this is an "acceptable" failure?
                job.logger.error(
                    "Job %s is a singleton and already running.",
                    job.job_model,
                    extra={"object": job.job_model, "grouping": "initialization"},
                )
                raise RunJobTaskFailed(f"Job '{job.job_model}' is a singleton and already running.")
        cache_parameters = {
            "key": job.singleton_cache_key,
            "value": 1,
            "timeout": job.job_model.time_limit or settings.CELERY_TASK_TIME_LIMIT,
        }
        cache.set(**cache_parameters)

    # Check for validity of the soft/hard time limits for the job.
    # TODO: this is a bit out of place?
    soft_time_limit = job.job_model.soft_time_limit or settings.CELERY_TASK_SOFT_TIME_LIMIT
    time_limit = job.job_model.time_limit or settings.CELERY_TASK_TIME_LIMIT
    if time_limit <= soft_time_limit:
        job.logger.warning(
            "The hard time limit of %s seconds is less than "
            "or equal to the soft time limit of %s seconds. "
            "This job will fail silently after %s seconds.",
            time_limit,
            soft_time_limit,
            time_limit,
            extra={"grouping": "initialization", "object": job.job_model},
        )

    # Send notice that the job is running
    event_payload = {
        "job_result_id": request.id,
        "job_name": job.name,  # TODO: should this be job.job_model.name instead? Possible breaking change
        "user_name": job_result.user.username,
    }
    if not job.job_model.has_sensitive_variables:
        event_payload["job_kwargs"] = kwargs
    publish_event(topic="nautobot.jobs.job.started", payload=event_payload)
    job.logger.info("Running job", extra={"grouping": "initialization", "object": job.job_model})

    # Return the job, ready to run
    return job, event_payload


def _cleanup_job(job, event_payload, status, kwargs):
    """Helper method to run_job task, handling cleanup after running a Job."""
    # Cleanup FileProxy objects
    file_fields = list(job._get_file_vars())
    file_ids = [kwargs[f] for f in file_fields if f in kwargs]
    if file_ids:
        job._delete_file_proxies(*file_ids)

    if status == JobResultStatusChoices.STATUS_SUCCESS:
        job.logger.success("Job completed", extra={"grouping": "post_run"})

    publish_event(topic="nautobot.jobs.job.completed", payload=event_payload)

    cache.delete(job.singleton_cache_key)


@nautobot_task(bind=True)
def run_job(self, job_class_path, *args, **kwargs):
    """
    "Runner" function for execution of any Job class by a worker.

    This calls the following Job APIs in the following order:

    - `Job.__init__()`
    - `Job.before_start(self.request.id, args, kwargs)`
    - `Job.__call__(*args, **kwargs)` (which calls `run(*args, **kwargs)`)
    - If no exceptions have been raised (and `Job.fail()` was not called):
        - `Job.on_success(result, self.request.id, args, kwargs)`
    - Else:
        - `Job.on_failure(result_or_exception, self.request.id, args, kwargs, einfo)`
    - `Job.after_return(status, result_or_exception, self.request.id, args, kwargs, einfo)`

    Finally, it either returns any data returned from `Job.run()` or re-raises any exception encountered.
    """

    job, event_payload = _prepare_job(job_class_path, self.request, kwargs)

    result = None
    status = None
    try:
        before_start_result = job.before_start(self.request.id, args, kwargs)
        if not job._failed:
            # Call job(), which automatically calls job.run():
            result = job(*args, **kwargs)
        else:
            # don't run the job if before_start() reported a failure, and report the before_start() return value
            result = before_start_result

        event_payload["job_output"] = result
        status = JobResultStatusChoices.STATUS_SUCCESS if not job._failed else JobResultStatusChoices.STATUS_FAILURE

        if status == JobResultStatusChoices.STATUS_SUCCESS:
            job.on_success(result, self.request.id, args, kwargs)
        else:
            job.on_failure(result, self.request.id, args, kwargs, None)

        job.after_return(status, result, self.request.id, args, kwargs, None)

        if status == JobResultStatusChoices.STATUS_SUCCESS:
            return result

        # Report a failure, but with a result rather than an exception and einfo:
        self.update_state(
            state=status,
            meta=result,
        )
        # If we return a result, Celery automatically applies STATUS_SUCCESS.
        # If we raise an exception *other than* `Ignore` or `Reject`, Celery automatically applies STATUS_FAILURE.
        # We don't want to overwrite the manual state update that we did above, so:
        raise Ignore()

    except Reject:
        status = status or JobResultStatusChoices.STATUS_REJECTED
        raise

    except Ignore:
        status = status or JobResultStatusChoices.STATUS_IGNORED
        raise

    except Exception as exc:
        status = JobResultStatusChoices.STATUS_FAILURE
        einfo = ExceptionInfo(sys.exc_info())
        job.on_failure(exc, self.request.id, args, kwargs, einfo)
        job.after_return(JobResultStatusChoices.STATUS_FAILURE, exc, self.request.id, args, kwargs, einfo)
        event_payload["einfo"] = {
            "exc_type": type(exc).__name__,
            "exc_message": sanitize(str(exc)),
        }
        raise

    finally:
        _cleanup_job(job, event_payload, status, kwargs)


def enqueue_job_hooks(object_change, may_reload_jobs=True, jobhook_queryset=None):
    """
    Find job hook(s) assigned to this changed object type + action and enqueue them to be processed.

    Args:
        object_change (ObjectChange): The change that may trigger JobHooks to execute.
        may_reload_jobs (bool): Whether to reload JobHook source code from disk to guarantee up-to-date code.
        jobhook_queryset (QuerySet): Previously retrieved set of JobHooks to potentially enqueue

    Returns:
        result (tuple[bool, QuerySet]): whether Jobs were reloaded here, and the jobhooks that were considered
    """
    jobs_reloaded = False

    # Job hooks cannot trigger other job hooks
    if object_change.change_context == ObjectChangeEventContextChoices.CONTEXT_JOB_HOOK:
        return jobs_reloaded, jobhook_queryset

    # Determine whether this type of object supports job hooks
    content_type = object_change.changed_object_type
    if content_type not in change_logged_models_queryset():
        return jobs_reloaded, jobhook_queryset

    # Retrieve any applicable job hooks
    if jobhook_queryset is None:
        action_flag = {
            ObjectChangeActionChoices.ACTION_CREATE: "type_create",
            ObjectChangeActionChoices.ACTION_UPDATE: "type_update",
            ObjectChangeActionChoices.ACTION_DELETE: "type_delete",
        }[object_change.action]
        jobhook_queryset = JobHook.objects.filter(content_types=content_type, enabled=True, **{action_flag: True})

    if not jobhook_queryset:  # not .exists() as we *want* to populate the queryset cache
        return jobs_reloaded, jobhook_queryset

    # Enqueue the jobs related to the job_hooks
    if may_reload_jobs:
        get_jobs(reload=True)
        jobs_reloaded = True

    for job_hook in jobhook_queryset:
        job_model = job_hook.job
        if not job_model.installed or not job_model.enabled:
            logger.warning(
                "JobHook %s is enabled, but the underlying Job %s is not installed and enabled", job_hook, job_model
            )
        elif get_job(job_model.class_path) is None:
            logger.error("JobHook %s is enabled, but the underlying Job implementation is missing", job_hook)
        else:
            JobResult.enqueue_job(job_model, object_change.user, object_change=object_change.pk)

    return jobs_reloaded, jobhook_queryset
