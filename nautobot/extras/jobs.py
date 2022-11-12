"""Jobs functionality - consolidates and replaces legacy "custom scripts" and "reports" features."""
from collections import OrderedDict
import inspect
import json
import logging
import os
import shutil
from textwrap import dedent
import traceback
import warnings


from db_file_storage.form_widgets import DBClearableFileInput
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import RegexValidator
from django.db import IntegrityError, transaction
from django.db.models import Model
from django.db.models.query import QuerySet
from django.forms import ValidationError
from django.test.client import RequestFactory
from django.utils import timezone
from django.utils.functional import classproperty
import netaddr
import yaml


from .choices import JobResultStatusChoices, LogLevelChoices, ObjectChangeActionChoices, ObjectChangeEventContextChoices
from .context_managers import change_logging, JobChangeContext, JobHookChangeContext
from .datasources.git import ensure_git_repository
from .forms import JobForm
from .models import FileProxy, GitRepository, Job as JobModel, JobHook, ObjectChange, ScheduledJob
from .registry import registry
from .utils import ChangeLoggedModelsQuery, get_job_content_type, jobs_in_directory, task_queues_as_choices

from nautobot.core.celery import nautobot_task
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
from nautobot.utilities.utils import copy_safe_request


User = get_user_model()


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
        - hidden (bool)
        - field_order (list)
        - read_only (bool)
        - approval_required (bool)
        - soft_time_limit (int)
        - time_limit (int)
        - has_sensitive_variables (bool)
        - task_queues (list)
        """

    def __init__(self):
        self.logger = logging.getLogger(f"nautobot.jobs.{self.__class__.__name__}")

        self.request = None
        self.active_test = "main"
        self.failed = False
        self._job_result = None

        # Compile test methods and initialize results skeleton
        self.test_methods = []

        for method_name in dir(self):
            if method_name.startswith("test_") and callable(getattr(self, method_name)):
                self.test_methods.append(method_name)

    def __str__(self):
        return str(self.name)

    # See https://github.com/PyCQA/pylint-django/issues/240 for why we have a pylint disable on each classproperty below

    @classproperty
    def file_path(cls):  # pylint: disable=no-self-argument
        return inspect.getfile(cls)

    @classproperty
    def class_path(cls):  # pylint: disable=no-self-argument
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
    def class_path_dotted(cls):  # pylint: disable=no-self-argument
        """
        Dotted class_path, suitable for use in things like Python logger names.
        """
        return cls.class_path.replace("/", ".")

    @classproperty
    def class_path_js_escaped(cls):  # pylint: disable=no-self-argument
        """
        Escape various characters so that the class_path can be used as a jQuery selector.
        """
        return cls.class_path.replace("/", r"\/").replace(".", r"\.")

    @classproperty
    def grouping(cls):  # pylint: disable=no-self-argument
        module = inspect.getmodule(cls)
        return getattr(module, "name", module.__name__)

    @classproperty
    def name(cls):  # pylint: disable=no-self-argument
        return getattr(cls.Meta, "name", cls.__name__)

    @classproperty
    def description(cls):  # pylint: disable=no-self-argument
        return dedent(getattr(cls.Meta, "description", "")).strip()

    @classproperty
    def description_first_line(cls):  # pylint: disable=no-self-argument
        if cls.description:  # pylint: disable=using-constant-test
            return cls.description.splitlines()[0]
        return ""

    @classproperty
    def commit_default(cls):  # pylint: disable=no-self-argument
        return getattr(cls.Meta, "commit_default", True)

    @classproperty
    def hidden(cls):  # pylint: disable=no-self-argument
        return getattr(cls.Meta, "hidden", False)

    @classproperty
    def field_order(cls):  # pylint: disable=no-self-argument
        return getattr(cls.Meta, "field_order", None)

    @classproperty
    def read_only(cls):  # pylint: disable=no-self-argument
        return getattr(cls.Meta, "read_only", False)

    @classproperty
    def approval_required(cls):  # pylint: disable=no-self-argument
        return getattr(cls.Meta, "approval_required", False)

    @classproperty
    def soft_time_limit(cls):  # pylint: disable=no-self-argument
        return getattr(cls.Meta, "soft_time_limit", 0)

    @classproperty
    def time_limit(cls):  # pylint: disable=no-self-argument
        return getattr(cls.Meta, "time_limit", 0)

    @classproperty
    def has_sensitive_variables(cls):  # pylint: disable=no-self-argument
        return getattr(cls.Meta, "has_sensitive_variables", True)

    @classproperty
    def task_queues(cls):  # pylint: disable=no-self-argument
        return getattr(cls.Meta, "task_queues", [])

    @classproperty
    def properties_dict(cls):  # pylint: disable=no-self-argument
        """
        Return all relevant classproperties as a dict.

        Used for convenient rendering into job_edit.html via the `json_script` template tag.
        """
        return {
            "name": cls.name,
            "grouping": cls.grouping,
            "description": cls.description,
            "approval_required": cls.approval_required,
            "commit_default": cls.commit_default,
            "hidden": cls.hidden,
            "read_only": cls.read_only,
            "soft_time_limit": cls.soft_time_limit,
            "time_limit": cls.time_limit,
            "has_sensitive_variables": cls.has_sensitive_variables,
            "task_queues": cls.task_queues,
        }

    @classmethod
    def _get_vars(cls):
        """
        Return dictionary of ScriptVariable attributes defined on this class and any base classes to the top of the inheritance chain.
        The variables are sorted in the order that they were defined, with variables defined on base classes appearing before subclass variables.
        """
        cls_vars = {}
        # get list of base classes, including cls, in reverse method resolution order: [BaseJob, Job, cls]
        base_classes = reversed(inspect.getmro(cls))
        attr_names = [name for base in base_classes for name in base.__dict__.keys()]
        for name in attr_names:
            attr_class = getattr(cls, name, None).__class__
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

    @property
    def job_result(self):
        return self._job_result

    @job_result.setter
    def job_result(self, value):
        # Initialize job_result data format for our usage
        value.data = OrderedDict()

        self._job_result = value

    @property
    def results(self):
        """
        The results generated by this job.
        ** If you need the logs, you will need to filter on JobLogEntry **
            Ex.
            from nautobot.extras.models import JogLogEntry

            JobLogEntry.objects.filter(job_result=self.job_result, <other criteria>)

        {
            "output": "...",
        }
        """
        return self.job_result.data if self.job_result else None

    def as_form(self, data=None, files=None, initial=None, approval_view=False):
        """
        Return a Django form suitable for populating the context data required to run this Job.

        `approval_view` will disable all fields from modification and is used to display the form
        during a approval review workflow.
        """
        fields = {name: var.as_field() for name, var in self._get_vars().items()}
        FormClass = type("JobForm", (JobForm,), fields)

        form = FormClass(data, files, initial=initial)

        try:
            job_model = JobModel.objects.get_for_class_path(self.class_path)
            read_only = job_model.read_only if job_model.read_only_override else self.read_only
            commit_default = job_model.commit_default if job_model.commit_default_override else self.commit_default
            task_queues = job_model.task_queues if job_model.task_queues_override else self.task_queues
        except JobModel.DoesNotExist:
            # 2.0 TODO: remove this fallback, Job records should always exist.
            logger.error("No Job instance found in the database corresponding to %s", self.class_path)
            read_only = self.read_only
            commit_default = self.commit_default
            task_queues = self.task_queues

        if read_only:
            # Hide the commit field for read only jobs
            form.fields["_commit"].widget = forms.HiddenInput()
            form.fields["_commit"].initial = False
        elif not initial or "_commit" not in initial:
            # Set initial "commit" checkbox state based on the Meta parameter
            form.fields["_commit"].initial = commit_default

        # Update task queue choices
        form.fields["_task_queue"].choices = task_queues_as_choices(task_queues)

        # https://github.com/PyCQA/pylint/issues/3484
        if self.field_order:  # pylint: disable=using-constant-test
            form.order_fields(self.field_order)

        if approval_view:
            # Set `disabled=True` on all fields
            for _, field in form.fields.items():
                field.disabled = True

            # Alter the commit help text to avoid confusion concerning approval dry-runs
            form.fields["_commit"].help_text = "Commit changes to the database"

        return form

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
            elif isinstance(value, InMemoryUploadedFile):
                return_data[field_name] = BaseJob.save_file(value)
            # IPAddressVar, IPAddressWithMaskVar, IPNetworkVar
            elif isinstance(value, netaddr.ip.BaseIP):
                return_data[field_name] = str(value)
            # Everything else...
            else:
                return_data[field_name] = value

        return return_data

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
            # If a field isn't a var, skip it (e.g. `_commit`).
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
                    not_found_pk_list = value - list(queryset.values_list("pk", flat=True))
                    raise queryset.model.DoesNotExist(
                        f"Failed to find requested objects for var {field_name}: [{', '.join(not_found_pk_list)}]"
                    )
                return_data[field_name] = var.field_attrs["queryset"].filter(pk__in=value)

            elif isinstance(var, ObjectVar):
                if isinstance(value, dict):
                    return_data[field_name] = var.field_attrs["queryset"].get(**value)
                else:
                    return_data[field_name] = var.field_attrs["queryset"].get(pk=value)
            elif isinstance(var, FileVar):
                return_data[field_name] = cls.load_file(value)
            # IPAddressVar is a netaddr.IPAddress object
            elif isinstance(var, IPAddressVar):
                return_data[field_name] = netaddr.IPAddress(value)
            # IPAddressWithMaskVar, IPNetworkVar are netaddr.IPNetwork objects
            elif isinstance(var, (IPAddressWithMaskVar, IPNetworkVar)):
                return_data[field_name] = netaddr.IPNetwork(value)
            else:
                return_data[field_name] = value

        return return_data

    def validate_data(self, data):
        cls_vars = self._get_vars()

        if not isinstance(data, dict):
            raise ValidationError("Job data needs to be a dict")

        for k in data:
            if k not in cls_vars:
                raise ValidationError({k: "Job data contained an unknown property"})

        # defer validation to the form object
        f = self.as_form(data=self.deserialize_data(data))
        if not f.is_valid():
            raise ValidationError(f.errors)

    @staticmethod
    def load_file(pk):
        """Load a file proxy stored in the database by primary key.

        Args:
            pk (uuid): Primary key of the `FileProxy` to retrieve

        Returns:
            File-like object
        """
        fp = FileProxy.objects.get(pk=pk)
        return fp.file

    @staticmethod
    def save_file(uploaded_file):
        """
        Save an uploaded file to the database as a file proxy and return the
        primary key.

        Args:
            uploaded_file (file): File handle of file to save to database

        Returns:
            uuid
        """
        fp = FileProxy.objects.create(name=uploaded_file.name, file=uploaded_file)
        return fp.pk

    @staticmethod
    def delete_files(*files_to_delete):
        """Given an unpacked list of primary keys for `FileProxy` objects, delete them.

        Args:
            files_to_delete (*args): List of primary keys to delete

        Returns:
            int (number of objects deleted)
        """
        files = FileProxy.objects.filter(pk__in=files_to_delete)
        num = 0
        for fp in files:
            fp.delete()  # Call delete() on each, so `FileAttachment` is reaped
            num += 1
        logger.debug(f"Deleted {num} file proxies")
        return num

    def run(self, data, commit):
        """
        Method invoked when this Job is run, before any "test_*" methods.
        """

    def post_run(self):
        """
        Method invoked after "run()" and all "test_*" methods.
        """

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
        If the object provided is a string, treat it as a message. This is a carryover of Netbox Report API
        """
        if isinstance(obj, str) and message is None:
            self._log(obj=None, message=obj, level_choice=LogLevelChoices.LOG_SUCCESS)
        else:
            self._log(obj, message, level_choice=LogLevelChoices.LOG_SUCCESS)

    def log_info(self, obj=None, message=None):
        """
        Log an informational message.
        If the object provided is a string, treat it as a message. This is a carryover of Netbox Report API
        """
        if isinstance(obj, str) and message is None:
            self._log(obj=None, message=obj, level_choice=LogLevelChoices.LOG_INFO)
        else:
            self._log(obj, message, level_choice=LogLevelChoices.LOG_INFO)

    def log_warning(self, obj=None, message=None):
        """
        Log a warning.
        If the object provided is a string, treat it as a message. This is a carryover of Netbox Report API
        """
        if isinstance(obj, str) and message is None:
            self._log(obj=None, message=obj, level_choice=LogLevelChoices.LOG_WARNING)
        else:
            self._log(obj, message, level_choice=LogLevelChoices.LOG_WARNING)

    def log_failure(self, obj=None, message=None):
        """
        Log a failure. Calling this method will automatically mark the overall job as failed.
        If the object provided is a string, treat it as a message. This is a carryover of Netbox Report API
        """
        if isinstance(obj, str) and message is None:
            self._log(obj=None, message=obj, level_choice=LogLevelChoices.LOG_FAILURE)
        else:
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


class DatabaseFileField(forms.FileField):
    """Specialized `FileField` for use with `DatabaseFileStorage` storage backend."""

    widget = DBClearableFileInput


class FileVar(ScriptVariable):
    """
    An uploaded file.
    """

    form_field = DatabaseFileField


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


class JobHookReceiver(Job):
    """
    Base class for job hook receivers. Job hook receivers are jobs that are initiated
    from object changes and are not intended to be run from the UI or API like standard jobs.
    """

    object_change = ObjectVar(model=ObjectChange)

    def run(self, data, commit):
        """JobHookReceiver subclasses generally shouldn't need to override this method."""
        object_change = data["object_change"]
        self.receive_job_hook(
            change=object_change,
            action=object_change.action,
            changed_object=object_change.changed_object,
        )

    def receive_job_hook(self, change, action, changed_object):
        """
        Method to be implemented by concrete JobHookReceiver subclasses.

        :param change: an instance of `nautobot.extras.models.ObjectChange`
        :param action: a string with the action performed on the changed object ("create", "update" or "delete")
        :param changed_object: an instance of the object that was changed, or `None` if the object has been deleted
        """
        raise NotImplementedError


def is_job(obj):
    """
    Returns True if the given object is a Job subclass.
    """
    from .scripts import Script, BaseScript
    from .reports import Report

    try:
        return issubclass(obj, Job) and obj not in [Job, Script, BaseScript, Report, JobHookReceiver]
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

    # Iterate over all filesystem sources (local, git.<slug1>, git.<slug2>, etc.)
    for source, path in paths.items():
        for job_info in jobs_in_directory(path):
            jobs.setdefault(source, {})
            if job_info.module_name not in jobs[source]:
                jobs[source][job_info.module_name] = {"name": job_info.job_class.grouping, "jobs": OrderedDict()}
            jobs[source][job_info.module_name]["jobs"][job_info.job_class_name] = job_info.job_class

    # Add jobs from plugins (which were already imported at startup)
    for cls in registry["plugin_jobs"]:
        module = inspect.getmodule(cls)
        jobs.setdefault("plugins", {}).setdefault(module.__name__, {"name": cls.grouping, "jobs": OrderedDict()})
        jobs["plugins"][module.__name__]["jobs"][cls.__name__] = cls

    return jobs


def _get_job_source_paths():
    """
    Helper function to get_jobs().

    Constructs a dict of {"grouping": filesystem_path, ...}.
    Current groupings are "local", "git.<repository_slug>".
    Plugin jobs aren't loaded dynamically from a source_path and so are not included in this function
    """
    paths = {}
    # Locally installed jobs
    if settings.JOBS_ROOT and os.path.exists(settings.JOBS_ROOT):
        paths["local"] = settings.JOBS_ROOT

    # Jobs derived from Git repositories
    if settings.GIT_ROOT and os.path.isdir(settings.GIT_ROOT):
        for repository_record in GitRepository.objects.all():
            if "extras.job" not in repository_record.provided_contents:
                # This repository isn't marked as containing jobs that we should use.
                continue

            try:
                # In the case where we have multiple Nautobot instances, or multiple worker instances,
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
                paths[f"git.{repository_record.slug}"] = jobs_path
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


@nautobot_task
def run_job(data, request, job_result_pk, commit=True, *args, **kwargs):
    """
    Helper function to call the "run()", "test_*()", and "post_run" methods on a Job.

    This function is responsible for setting up the job execution, handing the DB tranaction
    and rollback conditions, plus post execution cleanup and saving the JobResult record.
    """
    from nautobot.extras.models import JobResult  # avoid circular import

    # Getting the correct job result can fail if the stored data cannot be serialized.
    # Catching `TypeError: the JSON object must be str, bytes or bytearray, not int`
    try:
        job_result = JobResult.objects.get(pk=job_result_pk)
    except TypeError as e:
        logger.error(f"Unable to serialize data for job {job_result_pk}")
        logger.error(e)
        return False

    job_model = job_result.job_model
    initialization_failure = None
    if not job_model:
        # 2.0 TODO: remove this fallback logic
        try:
            job_model = JobModel.objects.get_for_class_path(job_result.name)
        except JobModel.DoesNotExist:
            initialization_failure = f'Unable to locate Job database record for "{job_result.name}" to run it!'

    if not initialization_failure:
        if not job_model.enabled:
            initialization_failure = f"Job {job_model} is not enabled to be run!"
        else:
            job_class = job_model.job_class

            if not job_model.installed or not job_class:
                initialization_failure = f'Unable to locate job "{job_result.name}" to run it!'

    if initialization_failure:
        job_result.log(
            message=initialization_failure,
            obj=job_model,
            level_choice=LogLevelChoices.LOG_FAILURE,
            grouping="initialization",
            logger=logger,
        )
        job_result.status = JobResultStatusChoices.STATUS_ERRORED
        job_result.completed = timezone.now()
        job_result.save()
        return False

    try:
        job = job_class()
        job.active_test = "initialization"
        job.job_result = job_result
    except Exception as error:
        logger.error("Error initializing job object.")
        logger.error(error)
        stacktrace = traceback.format_exc()
        job_result.log_failure(f"Error initializing job:\n```\n{stacktrace}\n```")
        job_result.set_status(JobResultStatusChoices.STATUS_ERRORED)
        job_result.completed = timezone.now()
        job_result.save()
        return False

    soft_time_limit = job_model.soft_time_limit or settings.CELERY_TASK_SOFT_TIME_LIMIT
    time_limit = job_model.time_limit or settings.CELERY_TASK_TIME_LIMIT
    if time_limit <= soft_time_limit:
        job_result.log(
            f"The hard time limit of {time_limit} seconds is less than "
            f"or equal to the soft time limit of {soft_time_limit} seconds. "
            f"This job will fail silently after {time_limit} seconds.",
            level_choice=LogLevelChoices.LOG_WARNING,
            grouping="initialization",
            logger=logger,
        )

    file_ids = None
    try:
        # Capture the file IDs for any FileProxy objects created so we can cleanup later.
        file_fields = list(job._get_file_vars())
        file_ids = [data[f] for f in file_fields]

        # Attempt to resolve serialized data back into original form by creating querysets or model instances
        # If we fail to find any objects, we consider this a job execution error, and fail.
        # This might happen when a job sits on the queue for a while (i.e. scheduled) and data has changed
        # or it might be bad input from an API request, or manual execution.

        data = job_class.deserialize_data(data)
    except Exception:
        job_result.set_status(JobResultStatusChoices.STATUS_ERRORED)
        stacktrace = traceback.format_exc()
        job_result.log(
            f"Error initializing job:\n```\n{stacktrace}\n```",
            level_choice=LogLevelChoices.LOG_FAILURE,
            grouping="initialization",
            logger=logger,
        )
        job_result.completed = timezone.now()
        job_result.save()
        if file_ids:
            # Cleanup FileProxy objects
            job.delete_files(*file_ids)  # pylint: disable=not-an-iterable
        return False

    if job_model.read_only:
        # Force commit to false for read only jobs.
        commit = False

    # TODO: validate that all args required by this job are set in the data or else log helpful errors?

    job.logger.info(f"Running job (commit={commit})")

    job_result.set_status(JobResultStatusChoices.STATUS_RUNNING)
    job_result.save()

    # Add the current request as a property of the job
    job.request = request

    def _run_job():
        """
        Core job execution task.

        We capture this within a subfunction to allow for conditionally wrapping it with the change_logging
        context manager (which is only relevant if commit == True).

        If the job is marked as read_only == True, then commit is forced to False and no log messages will be
        emitted related to reverting database changes.
        """
        started = timezone.now()
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
            if not job_model.read_only:
                job.log_info(message="Database changes have been reverted automatically.")

        except Exception as exc:
            stacktrace = traceback.format_exc()
            job.log_failure(message=f"An exception occurred: `{type(exc).__name__}: {exc}`\n```\n{stacktrace}\n```")
            if not job_model.read_only:
                job.log_info(message="Database changes have been reverted due to error.")
            job_result.set_status(JobResultStatusChoices.STATUS_ERRORED)

        finally:
            try:
                job_result.save()
            except IntegrityError:
                # handle job_model deleted while job was running
                job_result.job_model = None
                job_result.save()
            if file_ids:
                job.delete_files(*file_ids)  # Cleanup FileProxy objects

        # record data about this jobrun in the schedule
        if job_result.schedule:
            job_result.schedule.total_run_count += 1
            job_result.schedule.last_run_at = started
            job_result.schedule.save()

        # Perform any post-run tasks
        # 2.0 TODO Remove post_run() method entirely
        job.active_test = "post_run"
        try:
            output = job.post_run()
        except Exception as exc:
            stacktrace = traceback.format_exc()
            message = (
                f"An exception occurred during job post_run(): `{type(exc).__name__}: {exc}`\n```\n{stacktrace}\n```"
            )
            output = message
            job.log_failure(message=message)
            job_result.set_status(JobResultStatusChoices.STATUS_ERRORED)
        finally:
            if output:
                job.results["output"] += "\n" + str(output)

            job_result.completed = timezone.now()
            job_result.save()

            job.logger.info(f"Job completed in {job_result.duration}")

    # Execute the job. If commit == True, wrap it with the change_logging context manager to ensure we
    # process change logs, webhooks, etc.
    if commit:
        context_class = JobHookChangeContext if job_model.is_job_hook_receiver else JobChangeContext
        change_context = context_class(user=request.user, context_detail=job_model.slug)
        with change_logging(change_context):
            _run_job()
    else:
        _run_job()

    return True


@nautobot_task
def scheduled_job_handler(*args, **kwargs):
    """
    A thin wrapper around JobResult.enqueue_job() that allows for it to be called as an async task
    for the purposes of enqueuing scheduled jobs at their recurring intervals. Thus, JobResult.enqueue_job()
    is responsible for enqueuing the actual job for execution and this method is the task executed
    by the scheduler to kick off the job execution on a recurring interval.
    """
    from nautobot.extras.models import JobResult  # avoid circular import

    user_pk = kwargs.pop("user")
    user = User.objects.get(pk=user_pk)
    name = kwargs.pop("name")
    scheduled_job_pk = kwargs.pop("scheduled_job_pk")
    celery_kwargs = kwargs.pop("celery_kwargs", {})
    schedule = ScheduledJob.objects.get(pk=scheduled_job_pk)

    job_content_type = get_job_content_type()
    JobResult.enqueue_job(
        run_job, name, job_content_type, user, celery_kwargs=celery_kwargs, schedule=schedule, **kwargs
    )


def enqueue_job_hooks(object_change):
    """
    Find job hook(s) assigned to this changed object type + action and enqueue them
    to be processed
    """
    from nautobot.extras.models import JobResult  # avoid circular import

    # Job hooks cannot trigger other job hooks
    if object_change.change_context == ObjectChangeEventContextChoices.CONTEXT_JOB_HOOK:
        return

    # Determine whether this type of object supports job hooks
    model_type = object_change.changed_object._meta.model
    if model_type not in ChangeLoggedModelsQuery().list_subclasses():
        return

    # Retrieve any applicable job hooks
    content_type = ContentType.objects.get_for_model(object_change.changed_object)
    action_flag = {
        ObjectChangeActionChoices.ACTION_CREATE: "type_create",
        ObjectChangeActionChoices.ACTION_UPDATE: "type_update",
        ObjectChangeActionChoices.ACTION_DELETE: "type_delete",
    }[object_change.action]
    job_hooks = JobHook.objects.filter(content_types=content_type, enabled=True, **{action_flag: True})

    # Enqueue the jobs related to the job_hooks
    for job_hook in job_hooks:
        job_content_type = get_job_content_type()
        job_model = job_hook.job
        request = RequestFactory().request(SERVER_NAME="job_hook")
        request.user = object_change.user
        JobResult.enqueue_job(
            run_job,
            job_model.class_path,
            job_content_type,
            object_change.user,
            data=job_model.job_class.serialize_data({"object_change": object_change}),
            request=copy_safe_request(request),
            commit=True,
        )
