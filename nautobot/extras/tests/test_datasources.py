import os
import sys
import tempfile
from unittest import mock
import uuid

from celery.exceptions import NotRegistered
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import RequestFactory
import yaml

from nautobot.core.jobs import GitRepositoryDryRun, GitRepositorySync
from nautobot.core.testing import (
    create_job_result_and_run_job,
    run_job_for_testing,
    TransactionTestCase,
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
    GraphQLQuery,
    Job,
    JobButton,
    JobHook,
    JobLogEntry,
    JobResult,
    Role,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
)
from nautobot.extras.tests.git_helper import create_and_populate_git_repository
from nautobot.ipam.models import VLAN


class GitTest(TransactionTestCase):
    """
    Tests for Git repository handling.

    This is a TransactionTestCase because it involves JobResult logging.
    """

    databases = ("default", "job_logs")

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

        self.tempdir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        create_and_populate_git_repository(self.tempdir.name)

        self.repo_slug = "test_git_repo"
        self.repo = GitRepository(
            name="Test Git Repository",
            slug=self.repo_slug,
            remote_url="file://" + self.tempdir.name,  # file:// URLs aren't permitted normally, but very useful here!
            branch="empty-repo",
            # Provide everything we know we can provide
            provided_contents=[entry.content_identifier for entry in get_datasource_contents("extras.gitrepository")],
        )
        self.repo.save()

        self.job_result = JobResult.objects.create(name=self.repo.name)

    def tearDown(self):
        if f"{self.repo_slug}.jobs" in sys.modules:
            del sys.modules[f"{self.repo_slug}.jobs"]
        if f"{self.repo_slug}" in sys.modules:
            del sys.modules[f"{self.repo_slug}"]
        self.tempdir.cleanup()
        if self.repo is not None:
            self.repo.delete()
        super().tearDown()

    def assert_repo_slug_valid_python_package_name(self):
        git_repository = GitRepository.objects.create(
            name="1 Very-Bad Git_____Repo Name (2)", remote_url="http://localhost/git.git"
        )
        self.assertEqual(git_repository.slug, "a1_very_bad_git_____repo_name_2")

    def assert_config_context_schema_record_exists(self, name, filename="schema-1.yaml"):
        """Assert that a ConfigContextSchema record exists with the expected name and data_schema."""
        config_context_schema_record = ConfigContextSchema.objects.get(
            name=name,
            owner_object_id=self.repo.pk,
            owner_content_type=ContentType.objects.get_for_model(GitRepository),
        )
        self.assertIsNotNone(config_context_schema_record)
        with open(os.path.join(settings.GIT_ROOT, self.repo.slug, "config_context_schemas", filename)) as fd:
            config_context_schema_data = yaml.safe_load(fd)
        self.assertEqual(config_context_schema_data["_metadata"]["name"], config_context_schema_record.name)
        self.assertEqual(config_context_schema_data["data_schema"], config_context_schema_record.data_schema)

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
        self.assertIsNotNone(config_context.config_context_schema)

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

    def assert_graphql_query_exists(self, name="device_names.gql"):
        """Helper function to assert Graphql query exists."""
        graphql_query = GraphQLQuery.objects.get(
            name=name,
            owner_object_id=self.repo.pk,
            owner_content_type=ContentType.objects.get_for_model(GitRepository),
        )
        self.assertIsNotNone(graphql_query)

    def assert_job_exists(self, name="MyJob", installed=True):
        """Helper function to assert JobModel and registered Job exist."""
        # Is it registered correctly in the database?
        job_model = Job.objects.get(name=name, module_name=f"{self.repo_slug}.jobs.my_job", job_class_name=name)
        self.assertIsNotNone(job_model)
        if installed:
            self.assertTrue(job_model.installed)
            # Is the in-memory code accessible?
            self.assertIsNotNone(job_model.job_class)
            self.assertIsNotNone(job_model.job_task)
        else:
            self.assertFalse(job_model.installed)
            self.assertIsNone(job_model.job_class)
            with self.assertRaises(NotRegistered):
                job_model.job_task

    def test_pull_git_repository_and_refresh_data_with_no_data(self):
        """
        The pull_git_repository_and_refresh_data job should fail if the given repo is empty.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                # Run the Git operation and refresh the object from the DB
                # pull_git_repository_and_refresh_data(self.repo.pk, self.mock_request, self.job_result.pk)
                job_result = create_job_result_and_run_job(
                    module="nautobot.core.jobs",
                    name="GitRepositorySync",
                    source="system",
                    repository=self.repo.pk,
                )

                self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
                self.repo.refresh_from_db()

                log_entries = JobLogEntry.objects.filter(job_result=job_result)
                failure_logs = log_entries.filter(log_level=LogLevelChoices.LOG_ERROR)
                try:
                    failure_logs.get(grouping="jobs", message__contains="No `jobs` submodule found")
                except JobLogEntry.DoesNotExist:
                    for log in log_entries:
                        print(log.message)
                    print(job_result.traceback)
                    raise

    @mock.patch("nautobot.extras.datasources.git.GitRepo")
    def test_pull_git_repository_and_refresh_data_with_secrets(self, MockGitRepo):
        """
        The pull_git_repository_and_refresh_data job should correctly make use of secrets.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                MockGitRepo.return_value.checkout.return_value = ("0123456789abcdef", True)
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
                self.repo.remote_url = "http://localhost/git.git"
                # avoid failing due to lack of jobs module
                self.repo.provided_contents.remove("extras.job")  # pylint: disable=no-member
                self.repo.save()

                self.mock_request.id = uuid.uuid4()

                job_result = create_job_result_and_run_job(
                    module="nautobot.core.jobs",
                    name="GitRepositorySync",
                    source="system",
                    repository=self.repo.pk,
                )

                self.assertJobResultStatus(job_result)
                self.repo.refresh_from_db()
                MockGitRepo.assert_called_with(
                    os.path.join(tempdir, self.repo.slug),
                    "http://n%C3%BA%C3%B1ez:1%3A3%40%2F%3F%3Dab%40@localhost/git.git",
                )

    def test_pull_git_repository_and_refresh_data_with_valid_data(self):
        """
        The test_pull_git_repository_and_refresh_data job should succeed if valid data is present in the repo.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                # Run the Git operation and refresh the object from the DB
                self.repo.branch = "valid-files"  # actually a tag
                self.repo.save()
                job_model = GitRepositorySync().job_model
                job_result = run_job_for_testing(job=job_model, repository=self.repo.pk)
                job_result.refresh_from_db()
                self.assertJobResultStatus(job_result)

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

                # Make sure Graphgl queries were loaded
                self.assert_graphql_query_exists("device_names")
                self.assert_graphql_query_exists("device_interfaces")

                # Make sure Jobs were successfully loaded from file and registered as JobModels
                self.assert_job_exists(name="MyJob")
                self.assert_job_exists(name="MyJobButtonReceiver")
                self.assert_job_exists(name="MyJobHookReceiver")

                # Create JobButton and JobHook
                JobButton.objects.create(
                    name="MyJobButton", enabled=True, text="Click me", job=Job.objects.get(name="MyJobButtonReceiver")
                )
                JobHook.objects.create(name="MyJobHook", enabled=True, job=Job.objects.get(name="MyJobHookReceiver"))

                # TODO: test successful sync against a branch name or a commit hash as well

                # Now "resync" the repository, but now those files no longer exist in the repository
                self.repo.refresh_from_db()
                self.repo.branch = "empty-repo"  # actually a tag
                self.repo.save()

                # Run the Git operation and refresh the object from the DB
                job_result = run_job_for_testing(job=job_model, repository=self.repo.pk)
                job_result.refresh_from_db()
                self.assertJobResultStatus(job_result)

                # Verify that objects have been removed from the database
                self.assertEqual(
                    [],
                    list(
                        ConfigContext.objects.filter(
                            owner_content_type=ContentType.objects.get_for_model(GitRepository),
                            owner_object_id=self.repo.pk,
                        )
                    ),
                    list(job_result.job_log_entries.values_list("message", flat=True)),
                )
                self.assertEqual(
                    [],
                    list(
                        ExportTemplate.objects.filter(
                            owner_content_type=ContentType.objects.get_for_model(GitRepository),
                            owner_object_id=self.repo.pk,
                        )
                    ),
                    list(job_result.job_log_entries.values_list("message", flat=True)),
                )
                device = Device.objects.get(name=self.device.name)
                self.assertIsNone(device.local_config_context_data)
                self.assertIsNone(device.local_config_context_data_owner)

                # Verify that Job database record still exists but code is no longer installed/loaded
                self.assert_job_exists(installed=False)
                self.assert_job_exists(name="MyJobButtonReceiver", installed=False)
                self.assert_job_exists(name="MyJobHookReceiver", installed=False)

                # Verify that JobButton and JobHook are auto-disabled since the jobs are no longer available
                jb = JobButton.objects.get(name="MyJobButton")
                self.assertFalse(jb.enabled)
                jh = JobHook.objects.get(name="MyJobHook")
                self.assertFalse(jh.enabled)

    def test_pull_git_repository_and_refresh_data_with_bad_data(self):
        """
        The test_pull_git_repository_and_refresh_data job should gracefully handle bad data in the Git repository.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                self.repo.branch = "invalid-files"
                self.repo.save()
                # Run the Git operation and refresh the object from the DB
                job_model = GitRepositorySync().job_model
                self.assertIsNotNone(job_model)
                job_result = run_job_for_testing(
                    job=job_model,
                    repository=self.repo.pk,
                )
                job_result.refresh_from_db()

                self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)

                # Due to transaction rollback on failure, the database should still/again match the pre-sync state, of
                # no records owned by the repository.
                self.assertFalse(ConfigContextSchema.objects.filter(owner_object_id=self.repo.id).exists())
                self.assertFalse(ConfigContext.objects.filter(owner_object_id=self.repo.id).exists())
                self.assertFalse(ExportTemplate.objects.filter(owner_object_id=self.repo.id).exists())
                self.assertFalse(GraphQLQuery.objects.filter(owner_object_id=self.repo.id).exists())
                self.assertFalse(Job.objects.filter(module_name__startswith=f"{self.repo.slug}.").exists())
                device = Device.objects.get(name=self.device.name)
                self.assertIsNone(device.local_config_context_data)
                self.assertIsNone(device.local_config_context_data_owner)
                self.repo.refresh_from_db()
                self.assertEqual(self.repo.current_head, "")

                # Check for specific log messages
                log_entries = JobLogEntry.objects.filter(job_result=job_result)
                warning_logs = log_entries.filter(log_level=LogLevelChoices.LOG_WARNING)
                failure_logs = log_entries.filter(log_level=LogLevelChoices.LOG_ERROR)

                try:
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
                except JobLogEntry.DoesNotExist:
                    for log in log_entries:
                        print(log.message)
                    print(job_result.traceback)
                    raise

                try:
                    failure_logs.get(
                        grouping="config context schemas",
                        message__contains="Error in loading config context schema data from `badschema1.json`",
                    )
                    failure_logs.get(
                        grouping="config context schemas",
                        message__contains="Error in loading config context schema data from `badschema2.json`: "
                        "data is missing the required `_metadata` key",
                    )
                    failure_logs.get(
                        grouping="config contexts",
                        message__contains="Error in loading config context data from `badcontext1.json`",
                    )
                    failure_logs.get(
                        grouping="config contexts",
                        message__contains="Error in loading config context data from `badcontext2.json`: "
                        "data is missing the required `_metadata` key",
                    )
                    failure_logs.get(
                        grouping="config contexts",
                        message__contains="Error in loading config context data from `badcontext3.json`: "
                        "data `_metadata` is missing the required `name` key",
                    )
                    failure_logs.get(
                        grouping="local config contexts",
                        message__contains="Error in loading local config context from `devices/nosuchdevice.json`: "
                        "record not found",
                    )
                    failure_logs.get(
                        grouping="jobs",
                        message__contains="Error in loading Jobs from Git repository: ",
                    )
                    failure_logs.get(
                        grouping="graphql queries",
                        message__contains="Error processing GraphQL query file 'bad_device_names.gql': Syntax Error GraphQL (4:5) Expected Name, found }",
                    )

                except (AssertionError, JobLogEntry.DoesNotExist):
                    for log in log_entries:
                        print(log.message)
                    print(job_result.traceback)
                    raise

    def test_delete_git_repository_cleanup(self):
        """
        When deleting a GitRepository record, the data that it owned should also be deleted.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                self.repo.branch = "valid-files"
                self.repo.save()
                # Run the Git operation and refresh the object from the DB
                job_model = GitRepositorySync().job_model
                job_result = run_job_for_testing(
                    job=job_model,
                    repository=self.repo.pk,
                )
                job_result.refresh_from_db()

                self.assertJobResultStatus(job_result)

                # Make sure ConfigContext was successfully loaded from file
                config_context = ConfigContext.objects.get(
                    name="Frobozz 1000 NTP servers",
                    owner_object_id=self.repo.pk,
                    owner_content_type=ContentType.objects.get_for_model(GitRepository),
                )
                self.assertIsNotNone(config_context)
                self.assertEqual(1500, config_context.weight)
                self.assertEqual("NTP servers for Frobozz 1000 devices **only**", config_context.description)
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
                repo_pk = self.repo.pk
                repo_name = self.repo.name
                self.repo.delete()
                self.repo = None

                with self.subTest("Assert Deleted GitRepo do not create a never ending JobResult record"):
                    # Bug fix test for https://github.com/nautobot/nautobot/issues/5121
                    delete_job_result = JobResult.objects.filter(name=repo_name).first()
                    # Make sure we didn't get the wrong JobResult
                    self.assertNotEqual(job_result, delete_job_result)
                    self.assertJobResultStatus(delete_job_result)

                with self.assertRaises(ConfigContext.DoesNotExist):
                    ConfigContext.objects.get(
                        owner_object_id=repo_pk,
                        owner_content_type=ContentType.objects.get_for_model(GitRepository),
                    )

                with self.assertRaises(ConfigContextSchema.DoesNotExist):
                    ConfigContextSchema.objects.get(
                        owner_object_id=repo_pk,
                        owner_content_type=ContentType.objects.get_for_model(GitRepository),
                    )

                with self.assertRaises(ExportTemplate.DoesNotExist):
                    ExportTemplate.objects.get(
                        owner_object_id=repo_pk,
                        owner_content_type=ContentType.objects.get_for_model(GitRepository),
                    )

                device = Device.objects.get(name=self.device.name)
                self.assertIsNone(device.local_config_context_data)
                self.assertIsNone(device.local_config_context_data_owner)

                self.assert_job_exists(installed=False)

    def test_git_repository_sync_rollback(self):
        """
        Once a "known-good" sync state is achieved, resync to a new "bad" head commit should fail and be rolled back.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                # Initially have a successful sync to a good commit that provides data
                self.repo.branch = "valid-files"  # actually a tag
                self.repo.save()
                job_model = GitRepositorySync().job_model
                job_result = run_job_for_testing(job=job_model, repository=self.repo.pk)
                job_result.refresh_from_db()
                self.assertJobResultStatus(job_result)

                self.assert_explicit_config_context_exists("Frobozz 1000 NTP servers")
                self.assert_implicit_config_context_exists("Location context")
                self.assert_config_context_schema_record_exists("Config Context Schema 1")
                self.assert_device_exists(self.device.name)
                self.assert_export_template_device("template.j2")
                self.assert_export_template_html_exist("template2.html")
                self.assert_export_template_vlan_exists("template.j2")
                self.assert_graphql_query_exists(name="device_names")
                self.assert_graphql_query_exists(name="device_interfaces")
                self.assert_job_exists(name="MyJob")
                self.assert_job_exists(name="MyJobButtonReceiver")
                self.assert_job_exists(name="MyJobHookReceiver")

                # Create JobButton and JobHook
                JobButton.objects.create(
                    name="MyJobButton", enabled=True, text="Click me", job=Job.objects.get(name="MyJobButtonReceiver")
                )
                JobHook.objects.create(name="MyJobHook", enabled=True, job=Job.objects.get(name="MyJobHookReceiver"))

                self.repo.refresh_from_db()
                self.assertNotEqual(self.repo.current_head, "")
                good_current_head = self.repo.current_head

                # Now change to the `main` branch (which includes the current commit, followed by a "bad" commit)
                self.repo.branch = "main"
                self.repo.save()

                # Resync, attempting and failing to update to the new commit
                job_result = run_job_for_testing(job=job_model, repository=self.repo.pk)
                job_result.refresh_from_db()
                self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
                log_entries = JobLogEntry.objects.filter(job_result=job_result)

                # Assert database changes were rolled back
                self.repo.refresh_from_db()
                try:
                    self.assertEqual(self.repo.current_head, good_current_head)
                    self.assert_explicit_config_context_exists("Frobozz 1000 NTP servers")
                    self.assert_implicit_config_context_exists("Location context")
                    self.assert_config_context_schema_record_exists("Config Context Schema 1")
                    self.assert_device_exists(self.device.name)
                    self.assert_export_template_device("template.j2")
                    self.assert_export_template_html_exist("template2.html")
                    self.assert_export_template_vlan_exists("template.j2")
                    self.assert_graphql_query_exists("device_names")
                    self.assert_graphql_query_exists("device_interfaces")
                    self.assert_job_exists(name="MyJob")
                    self.assert_job_exists(name="MyJobButtonReceiver")
                    self.assert_job_exists(name="MyJobHookReceiver")
                    self.assertTrue(JobButton.objects.get(name="MyJobButton").enabled)
                    self.assertTrue(JobHook.objects.get(name="MyJobHook").enabled)
                except Exception:
                    for log in log_entries:
                        print(log.message)
                    print(job_result.traceback)
                    raise

    def test_git_dry_run(self):
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                self.mock_request.id = uuid.uuid4()

                self.repo.branch = "valid-files"
                self.repo.save()
                job_model = GitRepositoryDryRun().job_model
                job_result = run_job_for_testing(
                    job=job_model,
                    repository=self.repo.pk,
                )
                job_result.refresh_from_db()

                self.assertJobResultStatus(job_result)

                log_entries = JobLogEntry.objects.filter(job_result=job_result)

                try:
                    log_entries.get(message__contains="Addition - `__init__.py`")
                    log_entries.get(message__contains="Addition - `config_context_schemas/schema-1.yaml`")
                    log_entries.get(message__contains="Addition - `config_contexts/context.yaml`")
                    log_entries.get(message__contains="Addition - `config_contexts/devices/test-device.json`")
                    log_entries.get(message__contains="Addition - `config_contexts/locations/Test Location.json`")
                    log_entries.get(message__contains="Addition - `export_templates/dcim/device/template.j2`")
                    log_entries.get(message__contains="Addition - `export_templates/dcim/device/template2.html`")
                    log_entries.get(message__contains="Addition - `export_templates/ipam/vlan/template.j2`")
                    log_entries.get(message__contains="Addition - `graphql_queries/device_interfaces.gql`")
                    log_entries.get(message__contains="Addition - `graphql_queries/device_names.gql`")
                    log_entries.get(message__contains="Addition - `jobs/__init__.py`")
                    log_entries.get(message__contains="Addition - `jobs/my_job.py`")
                except JobLogEntry.DoesNotExist:
                    for log in log_entries:
                        print(log.message)
                    raise

                self.assertFalse(ConfigContextSchema.objects.filter(owner_object_id=self.repo.pk).exists())
                self.assertFalse(ConfigContext.objects.filter(owner_object_id=self.repo.pk).exists())
                self.assertFalse(ExportTemplate.objects.filter(owner_object_id=self.repo.pk).exists())
                self.assertFalse(GraphQLQuery.objects.filter(owner_object_id=self.repo.pk).exists())
                self.assertFalse(Job.objects.filter(module_name__startswith=self.repo.slug).exists())

    # TODO: test dry-run against a branch name
    # TODO: test dry-run against a specific commit hash

    def test_duplicate_repo_url_with_unique_provided_contents(self):
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

    def test_duplicate_repo_url_with_duplicate_provided_contents(self):
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

    @mock.patch("nautobot.extras.models.datasources.GitRepo")
    def test_clone_to_directory_with_secrets(self, MockGitRepo):
        """
        The clone_to_directory method should correctly make use of secrets.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            # Prepare secrets values
            with open(os.path.join(tempdir, "username.txt"), "wt") as handle:
                handle.write("núñez")

            with open(os.path.join(tempdir, "token.txt"), "wt") as handle:
                handle.write("1:3@/?=ab@")

            # Create secrets and assign
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

            # Configure GitRepository model
            self.repo.secrets_group = secrets_group
            self.repo.remote_url = "http://localhost/git.git"
            self.repo.save()

            # Try to clone it
            self.repo.clone_to_directory(tempdir, "main")

            # Assert that GitRepo was called with proper args
            args, kwargs = MockGitRepo.call_args
            path, from_url = args
            self.assertTrue(path.startswith(os.path.join(tempdir, self.repo.slug)))
            self.assertEqual(from_url, "http://n%C3%BA%C3%B1ez:1%3A3%40%2F%3F%3Dab%40@localhost/git.git")
            self.assertEqual(kwargs["depth"], 0)
            self.assertEqual(kwargs["branch"], "main")
