import json
import os
import tempfile
from unittest import mock
import uuid

import yaml

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase

from nautobot.dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site

from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.datasources.git import pull_git_repository_and_refresh_data
from nautobot.extras.datasources.registry import get_datasource_contents
from nautobot.extras.models import (
    ConfigContext,
    ConfigContextSchema,
    ExportTemplate,
    GitRepository,
    JobResult,
    Status,
)


# Use the proper swappable User model
User = get_user_model()


@mock.patch("nautobot.extras.datasources.git.GitRepo")
class GitTest(TestCase):

    COMMIT_HEXSHA = "88dd9cd78df89e887ee90a1d209a3e9a04e8c841"

    def setUp(self):
        self.user = User.objects.create_user(username="testuser")
        self.factory = RequestFactory()
        self.dummy_request = self.factory.get("/no-op/")
        self.dummy_request.user = self.user
        # Needed for use with the change_logging decorator
        self.dummy_request.id = uuid.uuid4()

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

        self.job_result = JobResult(
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

                pull_git_repository_and_refresh_data(self.repo.pk, self.dummy_request, self.job_result)

                self.assertEqual(
                    self.job_result.status,
                    JobResultStatusChoices.STATUS_COMPLETED,
                    self.job_result.data,
                )
                self.repo.refresh_from_db()
                self.assertEqual(self.repo.current_head, self.COMMIT_HEXSHA, self.job_result.data)
                MockGitRepo.assert_called_with(os.path.join(tempdir, self.repo.slug), "http://localhost/git.git")
                # TODO: inspect the logs in job_result.data?

                # Check that token-based authentication is handled as expected
                self.repo._token = "1:3@/?=ab@"
                self.repo.save()
                # For verisimilitude, don't re-use the old request and job_result
                self.dummy_request.id = uuid.uuid4()
                self.job_result = JobResult(
                    name=self.repo.name,
                    obj_type=ContentType.objects.get_for_model(GitRepository),
                    job_id=uuid.uuid4(),
                )
                pull_git_repository_and_refresh_data(self.repo.pk, self.dummy_request, self.job_result)

                self.assertEqual(
                    self.job_result.status,
                    JobResultStatusChoices.STATUS_COMPLETED,
                    self.job_result.data,
                )
                MockGitRepo.assert_called_with(
                    os.path.join(tempdir, self.repo.slug), "http://1%3A3%40%2F%3F%3Dab%40@localhost/git.git"
                )

                # Check that username/password authentication is handled as expected
                self.repo.username = "núñez"
                self.repo.save()
                # For verisimilitude, don't re-use the old request and job_result
                self.dummy_request.id = uuid.uuid4()
                self.job_result = JobResult(
                    name=self.repo.name,
                    obj_type=ContentType.objects.get_for_model(GitRepository),
                    job_id=uuid.uuid4(),
                )
                pull_git_repository_and_refresh_data(self.repo.pk, self.dummy_request, self.job_result)

                self.assertEqual(
                    self.job_result.status,
                    JobResultStatusChoices.STATUS_COMPLETED,
                    self.job_result.data,
                )
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

                pull_git_repository_and_refresh_data(self.repo.pk, self.dummy_request, self.job_result)

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
                self.assertEqual(self.config_context_schema["_metadata"]["name"], config_context.schema.name)

                # Make sure ConfigContextSchema was successfully loaded from file
                config_context_schema_record = ConfigContextSchema.objects.get(
                    name="Config Context Schema 1",
                    owner_object_id=self.repo.pk,
                    owner_content_type=ContentType.objects.get_for_model(GitRepository),
                )
                config_context_schema = self.config_context_schema
                config_context_schema_metadata = config_context_schema.setdefault("_metadata", {})
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

                # Now "resync" the repository, but now those files no longer exist in the repository
                def empty_repo(path, url):
                    os.remove(os.path.join(path, "config_contexts", "context.yaml"))
                    os.remove(os.path.join(path, "config_contexts", "devices", "test-device.json"))
                    os.remove(os.path.join(path, "config_context_schemas", "schema-1.yaml"))
                    os.remove(os.path.join(path, "export_templates", "dcim", "device", "template.j2"))
                    return mock.DEFAULT

                MockGitRepo.side_effect = empty_repo
                # For verisimilitude, don't re-use the old request and job_result
                self.dummy_request.id = uuid.uuid4()
                self.job_result = JobResult(
                    name=self.repo.name,
                    obj_type=ContentType.objects.get_for_model(GitRepository),
                    job_id=uuid.uuid4(),
                )

                pull_git_repository_and_refresh_data(self.repo.pk, self.dummy_request, self.job_result)

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
                    # Just make config_contexts and export_templates directories as we don't load jobs
                    os.makedirs(os.path.join(path, "config_contexts"))
                    os.makedirs(os.path.join(path, "config_contexts", "devices"))
                    os.makedirs(os.path.join(path, "config_context_schemas"))
                    os.makedirs(os.path.join(path, "export_templates", "nosuchapp", "device"))
                    os.makedirs(os.path.join(path, "export_templates", "dcim", "nosuchmodel"))
                    # Malformed JSON
                    with open(os.path.join(path, "config_contexts", "context.json"), "w") as fd:
                        fd.write('{"data": ')
                    # Valid JSON but missing required keys
                    with open(os.path.join(path, "config_contexts", "context2.json"), "w") as fd:
                        fd.write("{}")
                    with open(os.path.join(path, "config_context_schemas", "schema-1.yaml"), "w") as fd:
                        fd.write('{"data": ')
                    # Valid JSON but missing required keys
                    with open(os.path.join(path, "config_context_schemas", "schema-2.yaml"), "w") as fd:
                        fd.write("{}")
                    # No such device
                    with open(
                        os.path.join(path, "config_contexts", "devices", "nosuchdevice.json"),
                        "w",
                    ) as fd:
                        fd.write("{}")
                    # Invalid paths
                    with open(
                        os.path.join(
                            path,
                            "export_templates",
                            "nosuchapp",
                            "device",
                            "template.j2",
                        ),
                        "w",
                    ) as fd:
                        fd.write("{% for device in queryset %}\n{{ device.name }}\n{% endfor %}")
                    with open(
                        os.path.join(
                            path,
                            "export_templates",
                            "dcim",
                            "nosuchmodel",
                            "template.j2",
                        ),
                        "w",
                    ) as fd:
                        fd.write("{% for device in queryset %}\n{{ device.name }}\n{% endfor %}")
                    return mock.DEFAULT

                MockGitRepo.side_effect = populate_repo
                MockGitRepo.return_value.checkout.return_value = self.COMMIT_HEXSHA

                pull_git_repository_and_refresh_data(self.repo.pk, self.dummy_request, self.job_result)

                self.assertEqual(
                    self.job_result.status,
                    JobResultStatusChoices.STATUS_FAILED,
                    self.job_result.data,
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

                pull_git_repository_and_refresh_data(self.repo.pk, self.dummy_request, self.job_result)

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
                self.assertEqual(self.config_context_schema["_metadata"]["name"], config_context.schema.name)

                # Make sure ConfigContextSchema was successfully loaded from file
                config_context_schema_record = ConfigContextSchema.objects.get(
                    name="Config Context Schema 1",
                    owner_object_id=self.repo.pk,
                    owner_content_type=ContentType.objects.get_for_model(GitRepository),
                )
                config_context_schema = self.config_context_schema
                config_context_schema_metadata = config_context_schema.setdefault("_metadata", {})
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
