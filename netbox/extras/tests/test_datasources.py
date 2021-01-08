import os
import tempfile
from unittest import mock
import uuid

import yaml

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase

from dcim.models import Device

from extras.choices import JobResultStatusChoices
from extras.datasources.git import pull_git_repository_and_refresh_data
from extras.datasources.registry import get_datasource_contents
from extras.models import GitRepository, JobResult, ConfigContext, ExportTemplate


@mock.patch('extras.datasources.git.GitRepo')
class GitTest(TestCase):

    COMMIT_HEXSHA = "88dd9cd78df89e887ee90a1d209a3e9a04e8c841"

    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.factory = RequestFactory()
        self.dummy_request = self.factory.get('/no-op/')
        self.dummy_request.user = self.user
        # Needed for use with the change_logging decorator
        self.dummy_request.id = uuid.uuid4()

        self.repo = GitRepository(
            name="Test Git Repository",
            slug="test_git_repo",
            remote_url="http://localhost/git.git",
            # Provide everything we know we can provide
            provided_contents=[entry.token for entry in get_datasource_contents("extras.GitRepository")],
        )
        self.repo.save(trigger_resync=False)

        self.job_result = JobResult(
            name=self.repo.name,
            obj_type=ContentType.objects.get_for_model(GitRepository),
            job_id=uuid.uuid4(),
        )

    def test_pull_git_repository_and_refresh_data_with_no_data(self, MockGitRepo):
        """
        The test_pull_git_repository_and_refresh_data job should succeeed if the given repo is empty.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                def create_empty_repo(path, url):
                    os.makedirs(path)
                    return mock.DEFAULT
                MockGitRepo.side_effect = create_empty_repo
                MockGitRepo.return_value.checkout.return_value = self.COMMIT_HEXSHA

                pull_git_repository_and_refresh_data(self.repo.pk, self.dummy_request, self.job_result)

                self.assertEqual(self.job_result.status, JobResultStatusChoices.STATUS_COMPLETED, self.job_result.data)
                self.repo.refresh_from_db()
                self.assertEqual(self.repo.current_head, self.COMMIT_HEXSHA, self.job_result.data)
                # TODO: inspect the logs in job_result.data?

    def test_pull_git_repository_and_refresh_data_with_valid_data(self, MockGitRepo):
        """
        The test_pull_git_repository_and_refresh_data job should succeed if valid data is present in the repo.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                def populate_repo(path, url):
                    os.makedirs(path)
                    # Just make config_contexts and export_templates directories as we don't load custom_jobs
                    os.makedirs(os.path.join(path, "config_contexts"))
                    os.makedirs(os.path.join(path, "export_templates", "dcim", "device"))
                    with open(os.path.join(path, "config_contexts", "context.yaml"), 'w') as fd:
                        yaml.dump(
                            {
                                "name": "Region NYC servers",
                                "weight": 1500,
                                "description": "NTP servers for region NYC",
                                "is_active": True,
                                "data": {"ntp-servers": ["172.16.10.22", "172.16.10.33"]}
                            },
                            fd)
                    with open(os.path.join(path, "export_templates", "dcim", "device", "template.j2"), 'w') as fd:
                        fd.write("{% for device in queryset %}\n{{ device.name }}\n{% endfor %}")
                    return mock.DEFAULT

                MockGitRepo.side_effect = populate_repo
                MockGitRepo.return_value.checkout.return_value = self.COMMIT_HEXSHA

                pull_git_repository_and_refresh_data(self.repo.pk, self.dummy_request, self.job_result)

                self.assertEqual(self.job_result.status, JobResultStatusChoices.STATUS_COMPLETED, self.job_result.data)

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
                self.assertEqual({"ntp-servers": ["172.16.10.22", "172.16.10.33"]}, config_context.data)

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

                self.assertEqual(self.job_result.status, JobResultStatusChoices.STATUS_COMPLETED, self.job_result.data)

                # Verify that objects have been removed from the database
                self.assertEqual([], list(ConfigContext.objects.filter(
                    owner_content_type=ContentType.objects.get_for_model(GitRepository),
                    owner_object_id=self.repo.pk,
                )))
                self.assertEqual([], list(ExportTemplate.objects.filter(
                    owner_content_type=ContentType.objects.get_for_model(GitRepository),
                    owner_object_id=self.repo.pk,
                )))

    def test_pull_git_repository_and_refresh_data_with_bad_data(self, MockGitRepo):
        """
        The test_pull_git_repository_and_refresh_data job should gracefully handle bad data in the Git repository
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                def populate_repo(path, url):
                    os.makedirs(path)
                    # Just make config_contexts and export_templates directories as we don't load custom_jobs
                    os.makedirs(os.path.join(path, "config_contexts"))
                    os.makedirs(os.path.join(path, "export_templates", "nosuchapp", "device"))
                    os.makedirs(os.path.join(path, "export_templates", "dcim", "nosuchmodel"))
                    # Malformed JSON
                    with open(os.path.join(path, "config_contexts", "context.json"), 'w') as fd:
                        fd.write('{"data": ')
                    # Valid JSON but missing required keys
                    with open(os.path.join(path, "config_contexts", "context2.json"), 'w') as fd:
                        fd.write('{}')
                    # Invalid paths
                    with open(os.path.join(path, "export_templates", "nosuchapp", "device", "template.j2"), 'w') as fd:
                        fd.write("{% for device in queryset %}\n{{ device.name }}\n{% endfor %}")
                    with open(os.path.join(path, "export_templates", "dcim", "nosuchmodel", "template.j2"), 'w') as fd:
                        fd.write("{% for device in queryset %}\n{{ device.name }}\n{% endfor %}")
                    return mock.DEFAULT

                MockGitRepo.side_effect = populate_repo
                MockGitRepo.return_value.checkout.return_value = self.COMMIT_HEXSHA

                pull_git_repository_and_refresh_data(self.repo.pk, self.dummy_request, self.job_result)

                self.assertEqual(self.job_result.status, JobResultStatusChoices.STATUS_FAILED, self.job_result.data)
