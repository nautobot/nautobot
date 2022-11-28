import json
import logging
import os
import tempfile
from unittest import mock
import uuid

import yaml

from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory

from nautobot.dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from nautobot.ipam.models import VLAN

from nautobot.extras.choices import (
    JobResultStatusChoices,
    SecretsGroupAccessTypeChoices,
    SecretsGroupSecretTypeChoices,
)
from nautobot.extras.choices import LogLevelChoices
from nautobot.extras.datasources.git import pull_git_repository_and_refresh_data, git_repository_diff_origin_and_local
from nautobot.extras.datasources.registry import get_datasource_contents
from nautobot.extras.models import (
    ConfigContext,
    ConfigContextSchema,
    ExportTemplate,
    GitRepository,
    JobLogEntry,
    JobResult,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
)
from nautobot.utilities.testing import TransactionTestCase


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

        self.site = Site.objects.create(name="Test Site", slug="test-site")
        self.manufacturer = Manufacturer.objects.create(name="Acme", slug="acme")
        self.device_type = DeviceType.objects.create(
            manufacturer=self.manufacturer, model="Frobozz 1000", slug="frobozz1000"
        )
        self.role = DeviceRole.objects.create(name="router", slug="router")
        self.device_status = Status.objects.get_for_model(Device).get(slug="active")
        self.device = Device.objects.create(
            name="test-device",
            device_role=self.role,
            device_type=self.device_type,
            site=self.site,
            status=self.device_status,
        )

        self.repo = GitRepository(
            name="Test Git Repository",
            slug="test_git_repo",
            remote_url="http://localhost/git.git",
            # Provide everything we know we can provide
            provided_contents=[entry.content_identifier for entry in get_datasource_contents("extras.gitrepository")],
        )
        self.repo.save(trigger_resync=False)

        self.job_result = JobResult.objects.create(
            name=self.repo.name,
            obj_type=ContentType.objects.get_for_model(GitRepository),
            job_id=uuid.uuid4(),
        )

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

    def populate_repo(self, path, url, *args, **kwargs):
        os.makedirs(path)
        # TODO: populate Jobs as well?
        os.makedirs(os.path.join(path, "config_contexts"))
        os.makedirs(os.path.join(path, "config_contexts", "devices"))
        os.makedirs(os.path.join(path, "config_context_schemas"))
        os.makedirs(os.path.join(path, "export_templates", "dcim", "device"))
        os.makedirs(os.path.join(path, "export_templates", "ipam", "vlan"))
        with open(os.path.join(path, "config_contexts", "context.yaml"), "w") as fd:
            yaml.dump(
                {
                    "_metadata": {
                        "name": "Frobozz 1000 NTP servers",
                        "weight": 1500,
                        "description": "NTP servers for Frobozz 1000 devices **only**",
                        "is_active": True,
                        "schema": "Config Context Schema 1",
                        "device_types": [{"slug": self.device_type.slug}],
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
        with open(
            os.path.join(path, "export_templates", "dcim", "device", "template2.html"),
            "w",
        ) as fd:
            fd.write("<!DOCTYPE html>/n{% for device in queryset %}\n{{ device.name }}\n{% endfor %}")
        with open(
            os.path.join(path, "export_templates", "ipam", "vlan", "template.j2"),
            "w",
        ) as fd:
            fd.write("{% for vlan in queryset %}\n{{ vlan.name }}\n{% endfor %}")
        return mock.DEFAULT

    def empty_repo(self, path, url, *args, **kwargs):
        os.remove(os.path.join(path, "config_contexts", "context.yaml"))
        os.remove(os.path.join(path, "config_contexts", "devices", "test-device.json"))
        os.remove(os.path.join(path, "config_context_schemas", "schema-1.yaml"))
        os.remove(os.path.join(path, "export_templates", "dcim", "device", "template.j2"))
        os.remove(os.path.join(path, "export_templates", "dcim", "device", "template2.html"))
        os.remove(os.path.join(path, "export_templates", "ipam", "vlan", "template.j2"))
        return mock.DEFAULT

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
        self.assertIsNotNone(device.local_context_data)
        self.assertEqual({"dns-servers": ["8.8.8.8"]}, device.local_context_data)
        self.assertEqual(device.local_context_data_owner, self.repo)

    def assert_export_template_device(self, name):
        export_template_device = ExportTemplate.objects.get(
            owner_object_id=self.repo.pk,
            owner_content_type=ContentType.objects.get_for_model(GitRepository),
            content_type=ContentType.objects.get_for_model(Device),
            name=name,
        )
        self.assertIsNotNone(export_template_device)
        self.assertEqual(export_template_device.mime_type, "text/plain")

    def assert_config_context_exists(self, name):
        """Helper function to assert ConfigContext exists"""
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
        self.assertEqual(self.config_context_schema["_metadata"]["name"], config_context.schema.name)

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

    def test_pull_git_repository_and_refresh_data_with_no_data(self, MockGitRepo):
        """
        The pull_git_repository_and_refresh_data job should succeed if the given repo is empty.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):

                def create_empty_repo(path, url):
                    os.makedirs(path, exist_ok=True)
                    return mock.DEFAULT

                MockGitRepo.side_effect = create_empty_repo
                MockGitRepo.return_value.checkout.return_value = self.COMMIT_HEXSHA

                # Run the Git operation and refresh the object from the DB
                pull_git_repository_and_refresh_data(self.repo.pk, self.mock_request, self.job_result.pk)
                self.job_result.refresh_from_db()

                self.assertEqual(
                    self.job_result.status,
                    JobResultStatusChoices.STATUS_COMPLETED,
                    self.job_result.data,
                )
                self.repo.refresh_from_db()
                self.assertEqual(self.repo.current_head, self.COMMIT_HEXSHA, self.job_result.data)
                MockGitRepo.assert_called_with(os.path.join(tempdir, self.repo.slug), "http://localhost/git.git")

                log_entries = JobLogEntry.objects.filter(job_result=self.job_result)
                warning_logs = log_entries.filter(log_level=LogLevelChoices.LOG_WARNING)
                warning_logs.get(grouping="jobs", message__contains="No `jobs` subdirectory found")

    def test_pull_git_repository_and_refresh_data_with_token(self, MockGitRepo):
        """
        The pull_git_repository_and_refresh_data job should correctly make use of a token.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):

                def create_empty_repo(path, url):
                    os.makedirs(path, exist_ok=True)
                    return mock.DEFAULT

                MockGitRepo.side_effect = create_empty_repo
                MockGitRepo.return_value.checkout.return_value = self.COMMIT_HEXSHA

                # Check that token-based authentication is handled as expected
                self.repo._token = "1:3@/?=ab@"
                self.repo.save(trigger_resync=False)
                # For verisimilitude, don't re-use the old request and job_result
                self.mock_request.id = uuid.uuid4()
                self.job_result = JobResult.objects.create(
                    name=self.repo.name,
                    obj_type=ContentType.objects.get_for_model(GitRepository),
                    job_id=uuid.uuid4(),
                )

                # Run the Git operation and refresh the object from the DB
                pull_git_repository_and_refresh_data(self.repo.pk, self.mock_request, self.job_result.pk)
                self.job_result.refresh_from_db()

                self.assertEqual(
                    self.job_result.status,
                    JobResultStatusChoices.STATUS_COMPLETED,
                    self.job_result.data,
                )
                MockGitRepo.assert_called_with(
                    os.path.join(tempdir, self.repo.slug), "http://1%3A3%40%2F%3F%3Dab%40@localhost/git.git"
                )

    def test_pull_git_repository_and_refresh_data_with_username_and_token(self, MockGitRepo):
        """
        The pull_git_repository_and_refresh_data job should correctly make use of a username + token.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):

                def create_empty_repo(path, url):
                    os.makedirs(path, exist_ok=True)
                    return mock.DEFAULT

                MockGitRepo.side_effect = create_empty_repo
                MockGitRepo.return_value.checkout.return_value = self.COMMIT_HEXSHA

                # Check that username/password authentication is handled as expected
                self.repo.username = "núñez"
                self.repo._token = "1:3@/?=ab@"
                self.repo.save(trigger_resync=False)
                # For verisimilitude, don't re-use the old request and job_result
                self.mock_request.id = uuid.uuid4()
                self.job_result = JobResult.objects.create(
                    name=self.repo.name,
                    obj_type=ContentType.objects.get_for_model(GitRepository),
                    job_id=uuid.uuid4(),
                )

                # Run the Git operation and refresh the object from the DB
                pull_git_repository_and_refresh_data(self.repo.pk, self.mock_request, self.job_result.pk)
                self.job_result.refresh_from_db()

                self.assertEqual(
                    self.job_result.status,
                    JobResultStatusChoices.STATUS_COMPLETED,
                    self.job_result.data,
                )
                MockGitRepo.assert_called_with(
                    os.path.join(tempdir, self.repo.slug),
                    "http://n%C3%BA%C3%B1ez:1%3A3%40%2F%3F%3Dab%40@localhost/git.git",
                )

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
                MockGitRepo.return_value.checkout.return_value = self.COMMIT_HEXSHA

                with open(os.path.join(tempdir, "username.txt"), "wt") as handle:
                    handle.write("user1234")

                with open(os.path.join(tempdir, "token.txt"), "wt") as handle:
                    handle.write("1234abcd5678ef90")

                username_secret = Secret.objects.create(
                    name="Git Username",
                    slug="git-username",
                    provider="text-file",
                    parameters={"path": os.path.join(tempdir, "username.txt")},
                )
                token_secret = Secret.objects.create(
                    name="Git Token",
                    slug="git-token",
                    provider="text-file",
                    parameters={"path": os.path.join(tempdir, "token.txt")},
                )
                secrets_group = SecretsGroup.objects.create(name="Git Credentials", slug="git-credentials")
                SecretsGroupAssociation.objects.create(
                    secret=username_secret,
                    group=secrets_group,
                    access_type=SecretsGroupAccessTypeChoices.TYPE_HTTP,
                    secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
                )
                SecretsGroupAssociation.objects.create(
                    secret=token_secret,
                    group=secrets_group,
                    access_type=SecretsGroupAccessTypeChoices.TYPE_HTTP,
                    secret_type=SecretsGroupSecretTypeChoices.TYPE_TOKEN,
                )

                self.repo.secrets_group = secrets_group
                self.repo.save(trigger_resync=False)

                self.mock_request.id = uuid.uuid4()
                self.job_result = JobResult.objects.create(
                    name=self.repo.name,
                    obj_type=ContentType.objects.get_for_model(GitRepository),
                    job_id=uuid.uuid4(),
                )

                # Run the Git operation and refresh the object from the DB
                pull_git_repository_and_refresh_data(self.repo.pk, self.mock_request, self.job_result.pk)
                self.job_result.refresh_from_db()

                self.assertEqual(
                    self.job_result.status,
                    JobResultStatusChoices.STATUS_COMPLETED,
                    self.job_result.data,
                )
                MockGitRepo.assert_called_with(
                    os.path.join(tempdir, self.repo.slug),
                    "http://user1234:1234abcd5678ef90@localhost/git.git",
                )

    def test_pull_git_repository_and_refresh_data_with_valid_data(self, MockGitRepo):
        """
        The test_pull_git_repository_and_refresh_data job should succeed if valid data is present in the repo.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):

                MockGitRepo.side_effect = self.populate_repo
                MockGitRepo.return_value.checkout.return_value = self.COMMIT_HEXSHA

                # Run the Git operation and refresh the object from the DB
                pull_git_repository_and_refresh_data(self.repo.pk, self.mock_request, self.job_result.pk)
                self.job_result.refresh_from_db()

                self.assertEqual(
                    self.job_result.status,
                    JobResultStatusChoices.STATUS_COMPLETED,
                    self.job_result.data,
                )

                # Make sure ConfigContext was successfully loaded from file
                self.assert_config_context_exists("Frobozz 1000 NTP servers")

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

                # Now "resync" the repository, but now those files no longer exist in the repository
                MockGitRepo.side_effect = self.empty_repo
                # For verisimilitude, don't re-use the old request and job_result
                self.mock_request.id = uuid.uuid4()
                self.job_result = JobResult.objects.create(
                    name=self.repo.name,
                    obj_type=ContentType.objects.get_for_model(GitRepository),
                    job_id=uuid.uuid4(),
                )

                # Run the Git operation and refresh the object from the DB
                pull_git_repository_and_refresh_data(self.repo.pk, self.mock_request, self.job_result.pk)
                self.job_result.refresh_from_db()

                self.assertEqual(
                    self.job_result.status,
                    JobResultStatusChoices.STATUS_COMPLETED,
                    self.job_result.data,
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
                self.assertIsNone(device.local_context_data)
                self.assertIsNone(device.local_context_data_owner)

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
                    return mock.DEFAULT

                MockGitRepo.side_effect = populate_repo
                MockGitRepo.return_value.checkout.return_value = self.COMMIT_HEXSHA

                # Run the Git operation and refresh the object from the DB
                logging.disable(logging.ERROR)
                pull_git_repository_and_refresh_data(self.repo.pk, self.mock_request, self.job_result.pk)
                logging.disable(logging.NOTSET)
                self.job_result.refresh_from_db()

                self.assertEqual(
                    self.job_result.status,
                    JobResultStatusChoices.STATUS_FAILED,
                    self.job_result.data,
                )

                # Check for specific log messages
                log_entries = JobLogEntry.objects.filter(job_result=self.job_result)
                warning_logs = log_entries.filter(log_level=LogLevelChoices.LOG_WARNING)
                failure_logs = log_entries.filter(log_level=LogLevelChoices.LOG_FAILURE)

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
                    message__contains="Error in loading Jobs from `syntaxerror`: ",
                )
                failure_logs.get(
                    grouping="jobs",
                    message__contains="Error in loading Jobs from `importerror`: `No module named 'nosuchmodule'`",
                )

    def test_delete_git_repository_cleanup(self, MockGitRepo):
        """
        When deleting a GitRepository record, the data that it owned should also be deleted.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):

                def populate_repo(path, url):
                    os.makedirs(path)
                    # Just make config_contexts and export_templates directories as we don't load jobs
                    os.makedirs(os.path.join(path, "config_contexts"))
                    os.makedirs(os.path.join(path, "config_contexts", "devices"))
                    os.makedirs(os.path.join(path, "config_context_schemas"))
                    os.makedirs(os.path.join(path, "export_templates", "dcim", "device"))
                    with open(os.path.join(path, "config_contexts", "context.yaml"), "w") as fd:
                        yaml.dump(
                            {
                                "_metadata": {
                                    "name": "Region NYC servers",
                                    "weight": 1500,
                                    "description": "NTP servers for region NYC",
                                    "is_active": True,
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
                    return mock.DEFAULT

                MockGitRepo.side_effect = populate_repo
                MockGitRepo.return_value.checkout.return_value = self.COMMIT_HEXSHA

                # Run the Git operation and refresh the object from the DB
                pull_git_repository_and_refresh_data(self.repo.pk, self.mock_request, self.job_result.pk)
                self.job_result.refresh_from_db()

                self.assertEqual(
                    self.job_result.status,
                    JobResultStatusChoices.STATUS_COMPLETED,
                    self.job_result.data,
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
                config_context_schema_record = ConfigContextSchema.objects.get(
                    name="Config Context Schema 1",
                    owner_object_id=self.repo.pk,
                    owner_content_type=ContentType.objects.get_for_model(GitRepository),
                )
                self.assertEqual(config_context_schema_record, config_context.schema)

                config_context_schema = self.config_context_schema
                config_context_schema_metadata = config_context_schema["_metadata"]
                self.assertIsNotNone(config_context_schema_record)
                self.assertEqual(config_context_schema_metadata["name"], config_context_schema_record.name)
                self.assertEqual(config_context_schema["data_schema"], config_context_schema_record.data_schema)

                # Make sure Device local config context was successfully populated from file
                device = Device.objects.get(name=self.device.name)
                self.assertIsNotNone(device.local_context_data)
                self.assertEqual({"dns-servers": ["8.8.8.8"]}, device.local_context_data)
                self.assertEqual(device.local_context_data_owner, self.repo)

                # Make sure ExportTemplate was successfully loaded from file
                export_template = ExportTemplate.objects.get(
                    owner_object_id=self.repo.pk,
                    owner_content_type=ContentType.objects.get_for_model(GitRepository),
                    content_type=ContentType.objects.get_for_model(Device),
                    name="template.j2",
                )
                self.assertIsNotNone(export_template)

                # Now delete the GitRepository
                self.repo.delete()

                with self.assertRaises(ConfigContext.DoesNotExist):
                    config_context = ConfigContext.objects.get(
                        owner_object_id=self.repo.pk,
                        owner_content_type=ContentType.objects.get_for_model(GitRepository),
                    )

                with self.assertRaises(ConfigContextSchema.DoesNotExist):
                    config_context_schema = ConfigContextSchema.objects.get(
                        owner_object_id=self.repo.pk,
                        owner_content_type=ContentType.objects.get_for_model(GitRepository),
                    )

                with self.assertRaises(ExportTemplate.DoesNotExist):
                    export_template = ExportTemplate.objects.get(
                        owner_object_id=self.repo.pk,
                        owner_content_type=ContentType.objects.get_for_model(GitRepository),
                    )

                device = Device.objects.get(name=self.device.name)
                self.assertIsNone(device.local_context_data)
                self.assertIsNone(device.local_context_data_owner)

    def test_git_dry_run(self, MockGitRepo):
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):

                def create_empty_repo(path, url, clone_initially=False):
                    os.makedirs(path, exist_ok=True)
                    return mock.DEFAULT

                MockGitRepo.side_effect = create_empty_repo

                self.mock_request.id = uuid.uuid4()
                self.job_result = JobResult.objects.create(
                    name=self.repo.name,
                    obj_type=ContentType.objects.get_for_model(GitRepository),
                    job_id=uuid.uuid4(),
                )

                git_repository_diff_origin_and_local(self.repo.pk, self.mock_request, self.job_result.pk)
                self.job_result.refresh_from_db()

                self.assertEqual(self.job_result.status, JobResultStatusChoices.STATUS_COMPLETED, self.job_result.data)

                MockGitRepo.return_value.checkout.assert_not_called()
                MockGitRepo.assert_called_with(
                    os.path.join(tempdir, self.repo.slug),
                    self.repo.remote_url,
                    clone_initially=False,
                )
                MockGitRepo.return_value.diff_remote.assert_called()
