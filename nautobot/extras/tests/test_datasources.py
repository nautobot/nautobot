import json
import os
import sys
import tempfile
from unittest import mock
import uuid

from celery.exceptions import NotRegistered
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import RequestFactory
import yaml

from nautobot.core.jobs import GitRepositoryDryRun, GitRepositorySync
from nautobot.core.testing import (
    TransactionTestCase,
    create_job_result_and_run_job,
    run_job_for_testing,
)
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Manufacturer
from nautobot.extras.choices import (
    JobResultStatusChoices,
    LogLevelChoices,
    SecretsGroupAccessTypeChoices,
    SecretsGroupSecretTypeChoices,
)
from nautobot.extras.datasources.registry import get_datasource_contents
from nautobot.extras.models import (
    ConfigContext,
    ConfigContextSchema,
    ExportTemplate,
    GitRepository,
    Job,
    JobLogEntry,
    JobResult,
    Role,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
)
from nautobot.ipam.models import VLAN


@mock.patch("nautobot.extras.datasources.git.GitRepo")
class GitTest(TransactionTestCase):
    """
    Tests for Git repository handling.

    This is a TransactionTestCase because it involves JobResult logging.
    """

    databases = ("default", "job_logs")
    COMMIT_HEXSHA = "88dd9cd78df89e887ee90a1d209a3e9a04e8c841"

    def setUp(self):
        super().setUp()

        self.factory = RequestFactory()
        self.mock_request = self.factory.get("/no-op/")
        self.mock_request.user = self.user
        # Needed for use with the change_logging decorator
        self.mock_request.id = uuid.uuid4()

        self.location_type = LocationType.objects.create(name="Test Location Type")
        self.location_type.content_types.add(ContentType.objects.get_for_model(Device))
        status = Status.objects.create(name="Active Test")
        status.content_types.add(ContentType.objects.get_for_model(Location))
        self.location = Location.objects.create(location_type=self.location_type, name="Test Location", status=status)
        self.manufacturer = Manufacturer.objects.create(name="Manufacturer 1")
        self.device_type = DeviceType.objects.create(manufacturer=self.manufacturer, model="Frobozz 1000")
        role = Role.objects.create(name="Active Test")
        role.content_types.add(ContentType.objects.get_for_model(Device))
        status.content_types.add(ContentType.objects.get_for_model(Device))
        self.device = Device.objects.create(
            name="test-device",
            role=role,
            device_type=self.device_type,
            location=self.location,
            status=status,
        )

        self.repo = GitRepository(
            name="Test Git Repository",
            slug="test_git_repo",
            remote_url="http://localhost/git.git",
            # Provide everything we know we can provide
            provided_contents=[entry.content_identifier for entry in get_datasource_contents("extras.gitrepository")],
        )
        self.repo.save()

        self.job_result = JobResult.objects.create(name=self.repo.name)

        self.config_context_schema = {
            "_metadata": {
                "name": "Config Context Schema 1",
                "description": "Schema for defining first names, last names and ages.",
            },
            "data_schema": {
                "title": "Person",
                "type": "object",
                "properties": {
                    "firstName": {
                        "type": "string",
                        "description": "The person's first name.",
                    },
                    "lastName": {
                        "type": "string",
                        "description": "The person's last name.",
                    },
                    "age": {
                        "description": "Age in years which must be equal to or greater than zero.",
                        "type": "integer",
                        "minimum": 0,
                    },
                },
            },
        }

    def tearDown(self):
        if f"{self.repo.slug}.jobs" in sys.modules:
            del sys.modules[f"{self.repo.slug}.jobs"]
        if f"{self.repo.slug}" in sys.modules:
            del sys.modules[f"{self.repo.slug}"]

    def populate_repo(self, path, url, *args, **kwargs):
        os.makedirs(path)

        os.makedirs(os.path.join(path, "config_contexts"))
        os.makedirs(os.path.join(path, "config_contexts", "devices"))
        os.makedirs(os.path.join(path, "config_contexts", "locations"))
        os.makedirs(os.path.join(path, "config_context_schemas"))
        os.makedirs(os.path.join(path, "export_templates", "dcim", "device"))
        os.makedirs(os.path.join(path, "export_templates", "ipam", "vlan"))
        os.makedirs(os.path.join(path, "jobs"))

        with open(os.path.join(path, "__init__.py"), "w") as fd:
            # Required for job importing
            pass

        with open(os.path.join(path, "config_contexts", "context.yaml"), "w") as fd:
            yaml.dump(
                {
                    "_metadata": {
                        "name": "Frobozz 1000 NTP servers",
                        "weight": 1500,
                        "description": "NTP servers for Frobozz 1000 devices **only**",
                        "is_active": True,
                        "config_context_schema": "Config Context Schema 1",
                        "device_types": [{"model": self.device_type.model}],
                    },
                    "ntp-servers": ["172.16.10.22", "172.16.10.33"],
                },
                fd,
            )

        with open(os.path.join(path, "config_contexts", "locations", f"{self.location.name}.json"), "w") as fd:
            json.dump(
                {
                    "_metadata": {"name": "Location context", "is_active": False},
                    "domain_name": "example.com",
                },
                fd,
            )

        with open(os.path.join(path, "config_contexts", "devices", f"{self.device.name}.json"), "w") as fd:
            json.dump({"dns-servers": ["8.8.8.8"]}, fd)

        with open(os.path.join(path, "config_context_schemas", "schema-1.yaml"), "w") as fd:
            yaml.dump(self.config_context_schema, fd)

        with open(os.path.join(path, "export_templates", "dcim", "device", "template.j2"), "w") as fd:
            fd.write("{% for device in queryset %}\n{{ device.name }}\n{% endfor %}")

        with open(os.path.join(path, "export_templates", "dcim", "device", "template2.html"), "w") as fd:
            fd.write("<!DOCTYPE html>/n{% for device in queryset %}\n{{ device.name }}\n{% endfor %}")

        with open(os.path.join(path, "export_templates", "ipam", "vlan", "template.j2"), "w") as fd:
            fd.write("{% for vlan in queryset %}\n{{ vlan.name }}\n{% endfor %}")

        with open(os.path.join(path, "jobs", "__init__.py"), "w") as fd:
            fd.write("from nautobot.core.celery import register_jobs\nfrom .my_job import MyJob\nregister_jobs(MyJob)")

        with open(os.path.join(path, "jobs", "my_job.py"), "w") as fd:
            fd.write("from nautobot.extras.jobs import Job\nclass MyJob(Job):\n    def run(self):\n        pass")

        return mock.DEFAULT

    def empty_repo(self, path, url, *args, **kwargs):
        os.remove(os.path.join(path, "__init__.py"))
        os.remove(os.path.join(path, "config_contexts", "context.yaml"))
        os.remove(os.path.join(path, "config_contexts", "locations", f"{self.location.name}.json"))
        os.remove(os.path.join(path, "config_contexts", "devices", f"{self.device.name}.json"))
        os.remove(os.path.join(path, "config_context_schemas", "schema-1.yaml"))
        os.remove(os.path.join(path, "export_templates", "dcim", "device", "template.j2"))
        os.remove(os.path.join(path, "export_templates", "dcim", "device", "template2.html"))
        os.remove(os.path.join(path, "export_templates", "ipam", "vlan", "template.j2"))
        os.remove(os.path.join(path, "jobs", "__init__.py"))
        os.remove(os.path.join(path, "jobs", "my_job.py"))
        return mock.DEFAULT

    def assert_repo_slug_valid_python_package_name(self):
        git_repository = GitRepository.objects.create(
            name="1 Very-Bad Git_____Repo Name (2)", remote_url="http://localhost/git.git"
        )
        self.assertEqual(git_repository.slug, "a1_very_bad_git_____repo_name_2")

    def assert_config_context_schema_record_exists(self, name):
        """Helper Func to assert ConfigContextSchema with name=name exists"""
        config_context_schema_record = ConfigContextSchema.objects.get(
            name=name,
            owner_object_id=self.repo.pk,
            owner_content_type=ContentType.objects.get_for_model(GitRepository),
        )
        config_context_schema = self.config_context_schema
        config_context_schema_metadata = config_context_schema["_metadata"]
        self.assertIsNotNone(config_context_schema_record)
        self.assertEqual(config_context_schema_metadata["name"], config_context_schema_record.name)
        self.assertEqual(config_context_schema["data_schema"], config_context_schema_record.data_schema)

    def assert_device_exists(self, name):
        """Helper function to assert device exists"""
        device = Device.objects.get(name=name)
        self.assertIsNotNone(device.local_config_context_data)
        self.assertEqual({"dns-servers": ["8.8.8.8"]}, device.local_config_context_data)
        self.assertEqual(device.local_config_context_data_owner, self.repo)

    def assert_export_template_device(self, name):
        export_template_device = ExportTemplate.objects.get(
            owner_object_id=self.repo.pk,
            owner_content_type=ContentType.objects.get_for_model(GitRepository),
            content_type=ContentType.objects.get_for_model(Device),
            name=name,
        )
        self.assertIsNotNone(export_template_device)
        self.assertEqual(export_template_device.mime_type, "text/plain")

    def assert_explicit_config_context_exists(self, name):
        """Helper function to assert that an 'explicit' ConfigContext exists and is configured appropriately."""
        config_context = ConfigContext.objects.get(
            name=name,
            owner_object_id=self.repo.pk,
            owner_content_type=ContentType.objects.get_for_model(GitRepository),
        )
        self.assertIsNotNone(config_context)
        self.assertEqual(1500, config_context.weight)
        self.assertEqual("NTP servers for Frobozz 1000 devices **only**", config_context.description)
        self.assertTrue(config_context.is_active)
        self.assertEqual(list(config_context.device_types.all()), [self.device_type])
        self.assertEqual(
            {"ntp-servers": ["172.16.10.22", "172.16.10.33"]},
            config_context.data,
        )
        self.assertEqual(self.config_context_schema["_metadata"]["name"], config_context.config_context_schema.name)

    def assert_implicit_config_context_exists(self, name):
        """Helper function to assert that an 'implicit' ConfigContext exists and is configured appropriately."""
        config_context = ConfigContext.objects.get(
            name=name,
            owner_object_id=self.repo.pk,
            owner_content_type=ContentType.objects.get_for_model(GitRepository),
        )
        self.assertIsNotNone(config_context)
        self.assertEqual(1000, config_context.weight)  # default value
        self.assertEqual("", config_context.description)  # default value
        self.assertFalse(config_context.is_active)  # explicit metadata
        self.assertEqual(list(config_context.locations.all()), [self.location])  # implicit from the file path
        self.assertEqual({"domain_name": "example.com"}, config_context.data)
        self.assertIsNone(config_context.config_context_schema)

    def assert_export_template_html_exist(self, name):
        """Helper function to assert ExportTemplate exists"""
        export_template_html = ExportTemplate.objects.get(
            owner_object_id=self.repo.pk,
            owner_content_type=ContentType.objects.get_for_model(GitRepository),
            content_type=ContentType.objects.get_for_model(Device),
            name=name,
        )
        self.assertIsNotNone(export_template_html)
        self.assertEqual(export_template_html.mime_type, "text/html")

    def assert_export_template_vlan_exists(self, name):
        """Helper function to assert ExportTemplate exists"""
        export_template_vlan = ExportTemplate.objects.get(
            owner_object_id=self.repo.pk,
            owner_content_type=ContentType.objects.get_for_model(GitRepository),
            content_type=ContentType.objects.get_for_model(VLAN),
            name=name,
        )
        self.assertIsNotNone(export_template_vlan)

    def assert_job_exists(self, installed=True):
        """Helper function to assert JobModel and registerd Job exist."""
        # Is it registered correctly in the database?
        job_model = Job.objects.get(name="MyJob", module_name=f"{self.repo.slug}.jobs.my_job", job_class_name="MyJob")
        self.assertIsNotNone(job_model)
        if installed:
            self.assertTrue(job_model.installed)
            # Is the in-memory code accessible?
            self.assertIsNotNone(job_model.job_class)
            # Is it registered properly with Celery?
            self.assertIsNotNone(job_model.job_task)
        else:
            self.assertFalse(job_model.installed)
            self.assertIsNone(job_model.job_class)
            with self.assertRaises(NotRegistered):
                job_model.job_task

    def test_pull_git_repository_and_refresh_data_with_no_data(self, MockGitRepo):
        """
        The pull_git_repository_and_refresh_data job should fail if the given repo is empty.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):

                def create_empty_repo(path, url):
                    os.makedirs(path, exist_ok=True)
                    return mock.DEFAULT

                MockGitRepo.side_effect = create_empty_repo
                MockGitRepo.return_value.checkout.return_value = (self.COMMIT_HEXSHA, True)

                # Run the Git operation and refresh the object from the DB
                # pull_git_repository_and_refresh_data(self.repo.pk, self.mock_request, self.job_result.pk)
                job_result = create_job_result_and_run_job(
                    module="nautobot.core.jobs",
                    name="GitRepositorySync",
                    source="system",
                    repository=self.repo.pk,
                )

                self.assertEqual(
                    job_result.status,
                    JobResultStatusChoices.STATUS_FAILURE,
                    (
                        job_result.result,
                        list(job_result.job_log_entries.filter(log_level="error").values_list("message", flat=True)),
                    ),
                )
                self.repo.refresh_from_db()
                self.assertEqual(self.repo.current_head, self.COMMIT_HEXSHA, job_result.result)
                MockGitRepo.assert_called_with(os.path.join(tempdir, self.repo.slug), "http://localhost/git.git")

                log_entries = JobLogEntry.objects.filter(job_result=job_result)
                failure_logs = log_entries.filter(log_level=LogLevelChoices.LOG_ERROR)
                failure_logs.get(grouping="jobs", message__contains="Error in loading Jobs from Git repository: ")

    def test_pull_git_repository_and_refresh_data_with_secrets(self, MockGitRepo):
        """
        The pull_git_repository_and_refresh_data job should correctly make use of secrets.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):

                def create_empty_repo(path, url):
                    os.makedirs(path, exist_ok=True)
                    return mock.DEFAULT

                MockGitRepo.side_effect = create_empty_repo
                MockGitRepo.return_value.checkout.return_value = (self.COMMIT_HEXSHA, True)

                with open(os.path.join(tempdir, "username.txt"), "wt") as handle:
                    handle.write("núñez")

                with open(os.path.join(tempdir, "token.txt"), "wt") as handle:
                    handle.write("1:3@/?=ab@")

                username_secret = Secret.objects.create(
                    name="Git Username",
                    provider="text-file",
                    parameters={"path": os.path.join(tempdir, "username.txt")},
                )
                token_secret = Secret.objects.create(
                    name="Git Token",
                    provider="text-file",
                    parameters={"path": os.path.join(tempdir, "token.txt")},
                )
                secrets_group = SecretsGroup.objects.create(name="Git Credentials")
                SecretsGroupAssociation.objects.create(
                    secret=username_secret,
                    secrets_group=secrets_group,
                    access_type=SecretsGroupAccessTypeChoices.TYPE_HTTP,
                    secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
                )
                SecretsGroupAssociation.objects.create(
                    secret=token_secret,
                    secrets_group=secrets_group,
                    access_type=SecretsGroupAccessTypeChoices.TYPE_HTTP,
                    secret_type=SecretsGroupSecretTypeChoices.TYPE_TOKEN,
                )

                self.repo.secrets_group = secrets_group
                self.repo.provided_contents.remove("extras.job")  # avoid failing due to lack of jobs module
                self.repo.save()

                self.mock_request.id = uuid.uuid4()

                job_result = create_job_result_and_run_job(
                    module="nautobot.core.jobs",
                    name="GitRepositorySync",
                    source="system",
                    repository=self.repo.pk,
                )

                self.assertEqual(
                    job_result.status,
                    JobResultStatusChoices.STATUS_SUCCESS,
                    (
                        job_result.result,
                        list(job_result.job_log_entries.filter(log_level="error").values_list("message", flat=True)),
                    ),
                )
                self.repo.refresh_from_db()
                MockGitRepo.assert_called_with(
                    os.path.join(tempdir, self.repo.slug),
                    "http://n%C3%BA%C3%B1ez:1%3A3%40%2F%3F%3Dab%40@localhost/git.git",
                )

    def test_pull_git_repository_and_refresh_data_with_valid_data(self, MockGitRepo):
        """
        The test_pull_git_repository_and_refresh_data job should succeed if valid data is present in the repo.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                MockGitRepo.side_effect = self.populate_repo
                MockGitRepo.return_value.checkout.return_value = (self.COMMIT_HEXSHA, True)

                # Run the Git operation and refresh the object from the DB
                job_model = GitRepositorySync().job_model
                job_result = run_job_for_testing(job=job_model, repository=self.repo.pk)
                job_result.refresh_from_db()
                self.assertEqual(
                    job_result.status,
                    JobResultStatusChoices.STATUS_SUCCESS,
                    (
                        job_result.result,
                        list(job_result.job_log_entries.filter(log_level="error").values_list("message", flat=True)),
                    ),
                )

                # Make sure explicit ConfigContext was successfully loaded from file
                self.assert_explicit_config_context_exists("Frobozz 1000 NTP servers")

                # Make sure implicit ConfigContext was successfully loaded from file
                self.assert_implicit_config_context_exists("Location context")

                # Make sure ConfigContextSchema was successfully loaded from file
                self.assert_config_context_schema_record_exists("Config Context Schema 1")

                # Make sure Device local config context was successfully populated from file
                self.assert_device_exists(self.device.name)

                # Make sure ExportTemplate was successfully loaded from file
                self.assert_export_template_device("template.j2")

                self.assert_export_template_html_exist("template2.html")

                # Make sure ExportTemplate was successfully loaded from file
                # Case when ContentType.model != ContentType.name, template was added and deleted during sync (#570)
                self.assert_export_template_vlan_exists("template.j2")

                # Make sure Job was successfully loaded from file and registered as a JobModel
                self.assert_job_exists()

                # Now "resync" the repository, but now those files no longer exist in the repository
                MockGitRepo.side_effect = self.empty_repo

                # For verisimilitude, don't re-use the old request and job_result
                self.mock_request.id = uuid.uuid4()

                # Run the Git operation and refresh the object from the DB
                job_result = run_job_for_testing(job=job_model, repository=self.repo.pk)
                job_result.refresh_from_db()
                self.assertEqual(
                    job_result.status,
                    JobResultStatusChoices.STATUS_SUCCESS,
                    (
                        job_result.result,
                        list(job_result.job_log_entries.filter(log_level="error").values_list("message", flat=True)),
                    ),
                )

                # Verify that objects have been removed from the database
                self.assertEqual(
                    [],
                    list(
                        ConfigContext.objects.filter(
                            owner_content_type=ContentType.objects.get_for_model(GitRepository),
                            owner_object_id=self.repo.pk,
                        )
                    ),
                )
                self.assertEqual(
                    [],
                    list(
                        ExportTemplate.objects.filter(
                            owner_content_type=ContentType.objects.get_for_model(GitRepository),
                            owner_object_id=self.repo.pk,
                        )
                    ),
                )
                device = Device.objects.get(name=self.device.name)
                self.assertIsNone(device.local_config_context_data)
                self.assertIsNone(device.local_config_context_data_owner)

                # Verify that Job database record still exists but code is no longer installed/loaded
                self.assert_job_exists(installed=False)

    def test_pull_git_repository_and_refresh_data_with_bad_data(self, MockGitRepo):
        """
        The test_pull_git_repository_and_refresh_data job should gracefully handle bad data in the Git repository
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):

                def populate_repo(path, url):
                    os.makedirs(path)
                    os.makedirs(os.path.join(path, "config_contexts"))
                    os.makedirs(os.path.join(path, "config_contexts", "devices"))
                    os.makedirs(os.path.join(path, "config_context_schemas"))
                    os.makedirs(os.path.join(path, "export_templates", "nosuchapp", "device"))
                    os.makedirs(os.path.join(path, "export_templates", "dcim", "nosuchmodel"))
                    os.makedirs(os.path.join(path, "jobs"))
                    # Incorrect directories
                    os.makedirs(os.path.join(path, "devices"))
                    os.makedirs(os.path.join(path, "dcim"))
                    with open(os.path.join(path, "__init__.py"), "w") as fd:
                        pass
                    # Malformed JSON
                    with open(os.path.join(path, "config_contexts", "context.json"), "w") as fd:
                        fd.write('{"data": ')
                    # Valid JSON but missing required keys
                    with open(os.path.join(path, "config_contexts", "context2.json"), "w") as fd:
                        fd.write("{}")
                    with open(os.path.join(path, "config_contexts", "context3.json"), "w") as fd:
                        fd.write('{"_metadata": {}}')
                    # Malformed JSON
                    with open(os.path.join(path, "config_context_schemas", "schema-1.yaml"), "w") as fd:
                        fd.write('{"data": ')
                    # Valid JSON but missing required keys
                    with open(os.path.join(path, "config_context_schemas", "schema-2.yaml"), "w") as fd:
                        fd.write("{}")
                    # No such device
                    with open(os.path.join(path, "config_contexts", "devices", "nosuchdevice.json"), "w") as fd:
                        fd.write("{}")
                    # Invalid paths
                    with open(os.path.join(path, "export_templates", "nosuchapp", "device", "template.j2"), "w") as fd:
                        fd.write("{% for device in queryset %}\n{{ device.name }}\n{% endfor %}")
                    with open(os.path.join(path, "export_templates", "dcim", "nosuchmodel", "template.j2"), "w") as fd:
                        fd.write("{% for device in queryset %}\n{{ device.name }}\n{% endfor %}")
                    # Malformed Python
                    with open(os.path.join(path, "jobs", "syntaxerror.py"), "w") as fd:
                        fd.write("print(")
                    with open(os.path.join(path, "jobs", "importerror.py"), "w") as fd:
                        fd.write("import nosuchmodule")
                    with open(os.path.join(path, "jobs", "__init__.py"), "w") as fd:
                        fd.write("import .syntaxerror\nimport .importerror")
                    return mock.DEFAULT

                MockGitRepo.side_effect = populate_repo
                MockGitRepo.return_value.checkout.return_value = (self.COMMIT_HEXSHA, True)

                # Run the Git operation and refresh the object from the DB
                job_model = GitRepositorySync().job_model
                job_result = run_job_for_testing(
                    job=job_model,
                    repository=self.repo.pk,
                )
                job_result.refresh_from_db()

                self.assertEqual(
                    job_result.status,
                    JobResultStatusChoices.STATUS_FAILURE,
                    job_result.result,
                )

                # Check for specific log messages
                log_entries = JobLogEntry.objects.filter(job_result=job_result)
                warning_logs = log_entries.filter(log_level=LogLevelChoices.LOG_WARNING)
                failure_logs = log_entries.filter(log_level=LogLevelChoices.LOG_ERROR)

                warning_logs.get(
                    grouping="config contexts", message__contains='Found "devices" directory in the repository root'
                )
                warning_logs.get(
                    grouping="export templates", message__contains='Found "dcim" directory in the repository root'
                )
                warning_logs.get(
                    grouping="export templates",
                    message__contains="Skipping `dcim.nosuchmodel` as it isn't a known content type",
                )
                warning_logs.get(
                    grouping="export templates",
                    message__contains="Skipping `nosuchapp.device` as it isn't a known content type",
                )

                failure_logs.get(
                    grouping="config context schemas",
                    message__contains="Error in loading config context schema data from `schema-1.yaml`",
                )
                failure_logs.get(
                    grouping="config context schemas",
                    message__contains="Error in loading config context schema data from `schema-2.yaml`: "
                    "data is missing the required `_metadata` key",
                )
                failure_logs.get(
                    grouping="config contexts",
                    message__contains="Error in loading config context data from `context.json`",
                )
                failure_logs.get(
                    grouping="config contexts",
                    message__contains="Error in loading config context data from `context2.json`: "
                    "data is missing the required `_metadata` key",
                )
                failure_logs.get(
                    grouping="config contexts",
                    message__contains="Error in loading config context data from `context3.json`: "
                    "data `_metadata` is missing the required `name` key",
                )
                failure_logs.get(
                    grouping="local config contexts",
                    message__contains="Error in loading local config context from `devices/nosuchdevice.json`: "
                    "record not found",
                )
                failure_logs.get(
                    grouping="jobs",
                    # The specific exception message differs between Python versions
                    message__contains="Error in loading Jobs from Git repository: ",
                )

    def test_delete_git_repository_cleanup(self, MockGitRepo):
        """
        When deleting a GitRepository record, the data that it owned should also be deleted.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):

                def populate_repo(path, url):
                    os.makedirs(path)
                    os.makedirs(os.path.join(path, "config_contexts"))
                    os.makedirs(os.path.join(path, "config_contexts", "devices"))
                    os.makedirs(os.path.join(path, "config_context_schemas"))
                    os.makedirs(os.path.join(path, "export_templates", "dcim", "device"))
                    os.makedirs(os.path.join(path, "jobs"))
                    with open(os.path.join(path, "__init__.py"), "w") as fd:
                        pass
                    with open(os.path.join(path, "config_contexts", "context.yaml"), "w") as fd:
                        yaml.dump(
                            {
                                "_metadata": {
                                    "name": "Region NYC servers",
                                    "weight": 1500,
                                    "description": "NTP servers for region NYC",
                                    "is_active": True,
                                    # Changing this from `config_context_schema` to `schema` to assert that schema can
                                    # be used inplace of `config_context_schema`.
                                    # TODO(timizuo): Replace `schema` with `config_context_schema` when `schema`
                                    #  backwards-compatibility is removed.
                                    "schema": "Config Context Schema 1",
                                },
                                "ntp-servers": ["172.16.10.22", "172.16.10.33"],
                            },
                            fd,
                        )
                    with open(
                        os.path.join(path, "config_contexts", "devices", "test-device.json"),
                        "w",
                    ) as fd:
                        json.dump({"dns-servers": ["8.8.8.8"]}, fd)
                    with open(os.path.join(path, "config_context_schemas", "schema-1.yaml"), "w") as fd:
                        yaml.dump(self.config_context_schema, fd)
                    with open(
                        os.path.join(path, "export_templates", "dcim", "device", "template.j2"),
                        "w",
                    ) as fd:
                        fd.write("{% for device in queryset %}\n{{ device.name }}\n{% endfor %}")
                    with open(os.path.join(path, "jobs", "__init__.py"), "w") as fd:
                        fd.write(
                            "from nautobot.core.celery import register_jobs\nfrom .my_job import MyJob\nregister_jobs(MyJob)"
                        )

                    with open(os.path.join(path, "jobs", "my_job.py"), "w") as fd:
                        fd.write(
                            "from nautobot.extras.jobs import Job\nclass MyJob(Job):\n    def run(self):\n        pass"
                        )

                    return mock.DEFAULT

                MockGitRepo.side_effect = populate_repo
                MockGitRepo.return_value.checkout.return_value = (self.COMMIT_HEXSHA, True)

                # Run the Git operation and refresh the object from the DB
                job_model = GitRepositorySync().job_model
                job_result = run_job_for_testing(
                    job=job_model,
                    repository=self.repo.pk,
                )
                job_result.refresh_from_db()

                self.assertEqual(
                    job_result.status,
                    JobResultStatusChoices.STATUS_SUCCESS,
                    (
                        job_result.result,
                        list(job_result.job_log_entries.filter(log_level="error").values_list("message", flat=True)),
                    ),
                )

                # Make sure ConfigContext was successfully loaded from file
                config_context = ConfigContext.objects.get(
                    name="Region NYC servers",
                    owner_object_id=self.repo.pk,
                    owner_content_type=ContentType.objects.get_for_model(GitRepository),
                )
                self.assertIsNotNone(config_context)
                self.assertEqual(1500, config_context.weight)
                self.assertEqual("NTP servers for region NYC", config_context.description)
                self.assertTrue(config_context.is_active)
                self.assertEqual(
                    {"ntp-servers": ["172.16.10.22", "172.16.10.33"]},
                    config_context.data,
                )

                # Make sure ConfigContextSchema was successfully loaded from file
                self.assert_config_context_schema_record_exists("Config Context Schema 1")

                # Make sure Device local config context was successfully populated from file
                self.assert_device_exists(self.device.name)

                # Make sure ExportTemplate was successfully loaded from file
                self.assert_export_template_device("template.j2")

                # Make sure Job is loaded and registered into Celery as well as the database
                self.assert_job_exists()

                # Now delete the GitRepository
                self.repo.delete()

                with self.assertRaises(ConfigContext.DoesNotExist):
                    ConfigContext.objects.get(
                        owner_object_id=self.repo.pk,
                        owner_content_type=ContentType.objects.get_for_model(GitRepository),
                    )

                with self.assertRaises(ConfigContextSchema.DoesNotExist):
                    ConfigContextSchema.objects.get(
                        owner_object_id=self.repo.pk,
                        owner_content_type=ContentType.objects.get_for_model(GitRepository),
                    )

                with self.assertRaises(ExportTemplate.DoesNotExist):
                    ExportTemplate.objects.get(
                        owner_object_id=self.repo.pk,
                        owner_content_type=ContentType.objects.get_for_model(GitRepository),
                    )

                device = Device.objects.get(name=self.device.name)
                self.assertIsNone(device.local_config_context_data)
                self.assertIsNone(device.local_config_context_data_owner)

                self.assert_job_exists(installed=False)

    def test_git_dry_run(self, MockGitRepo):
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):

                def create_empty_repo(path, url, clone_initially=False):
                    os.makedirs(path, exist_ok=True)
                    return mock.DEFAULT

                MockGitRepo.side_effect = create_empty_repo

                self.mock_request.id = uuid.uuid4()

                job_model = GitRepositoryDryRun().job_model
                job_result = run_job_for_testing(
                    job=job_model,
                    repository=self.repo.pk,
                )
                job_result.refresh_from_db()

                self.assertEqual(
                    job_result.status,
                    JobResultStatusChoices.STATUS_SUCCESS,
                    (
                        job_result.result,
                        list(job_result.job_log_entries.filter(log_level="error").values_list("message", flat=True)),
                    ),
                )

                MockGitRepo.return_value.checkout.assert_not_called()
                MockGitRepo.assert_called_with(
                    os.path.join(tempdir, self.repo.slug),
                    self.repo.remote_url,
                    clone_initially=False,
                )
                MockGitRepo.return_value.diff_remote.assert_called()

    def test_duplicate_repo_url_with_unique_provided_contents(self, MockGitRepo):
        """Create a duplicate repo but with unique provided_contents."""
        remote_url = "http://localhost/duplicates.git"
        repo1 = GitRepository(
            name="Repo 1",
            slug="repo_1",
            remote_url=remote_url,
            provided_contents=["extras.job"],
        )
        repo1.validated_save()
        repo2 = GitRepository(
            name="Repo 2",
            slug="repo_2",
            remote_url=remote_url,
            provided_contents=["extras.configcontext"],
        )
        repo2.validated_save()
        repos = GitRepository.objects.filter(remote_url=remote_url)
        self.assertEqual(repos.count(), 2)

    def test_duplicate_repo_url_with_duplicate_provided_contents(self, MockGitRepo):
        """Create a duplicate repo but with duplicate provided_contents."""
        remote_url = "http://localhost/duplicates.git"
        repo1 = GitRepository(
            name="Repo 1",
            slug="repo_1",
            remote_url=remote_url,
            provided_contents=["extras.job"],
        )
        repo1.validated_save()
        repo2 = GitRepository(
            name="Repo 2",
            slug="repo_2",
            remote_url=remote_url,
            provided_contents=["extras.job"],
        )

        with self.assertRaises(ValidationError) as cm:
            repo2.validated_save()

        self.assertIn(
            f"Another Git repository already configured for remote URL {repo1.remote_url} "
            "provides contents overlapping with this repository.",
            str(cm.exception),
        )
