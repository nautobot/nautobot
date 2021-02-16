import urllib.parse
import uuid

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse

from dcim.models import Device, Site
from extras.choices import ObjectChangeActionChoices
from extras.models import ConfigContext, CustomLink, GitRepository, ObjectChange, Status, Tag
from utilities.testing import ViewTestCases, TestCase


class TagTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = Tag

    @classmethod
    def setUpTestData(cls):

        Tag.objects.bulk_create((
            Tag(name='Tag 1', slug='tag-1'),
            Tag(name='Tag 2', slug='tag-2'),
            Tag(name='Tag 3', slug='tag-3'),
        ))

        cls.form_data = {
            'name': 'Tag X',
            'slug': 'tag-x',
            'color': 'c0c0c0',
            'comments': 'Some comments',
        }

        cls.csv_data = (
            "name,slug,color,description",
            "Tag 4,tag-4,ff0000,Fourth tag",
            "Tag 5,tag-5,00ff00,Fifth tag",
            "Tag 6,tag-6,0000ff,Sixth tag",
        )

        cls.bulk_edit_data = {
            'color': '00ff00',
        }


# TODO: Change base class to PrimaryObjectViewTestCase
# Blocked by absence of standard create/edit, bulk create views
class ConfigContextTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase
):
    model = ConfigContext

    @classmethod
    def setUpTestData(cls):

        site = Site.objects.create(name='Site 1', slug='site-1')

        # Create three ConfigContexts
        for i in range(1, 4):
            configcontext = ConfigContext(
                name='Config Context {}'.format(i),
                data={'foo': i}
            )
            configcontext.save()
            configcontext.sites.add(site)

        cls.form_data = {
            'name': 'Config Context X',
            'weight': 200,
            'description': 'A new config context',
            'is_active': True,
            'regions': [],
            'sites': [site.pk],
            'roles': [],
            'platforms': [],
            'tenant_groups': [],
            'tenants': [],
            'tags': [],
            'data': '{"foo": 123}',
        }

        cls.bulk_edit_data = {
            'weight': 300,
            'is_active': False,
            'description': 'New description',
        }


# TODO: Convert to StandardTestCases.Views
class ObjectChangeTestCase(TestCase):
    user_permissions = (
        'extras.view_objectchange',
    )

    @classmethod
    def setUpTestData(cls):

        site = Site(name='Site 1', slug='site-1')
        site.save()

        # Create three ObjectChanges
        user = User.objects.create_user(username='testuser2')
        for i in range(1, 4):
            oc = site.to_objectchange(action=ObjectChangeActionChoices.ACTION_UPDATE)
            oc.user = user
            oc.request_id = uuid.uuid4()
            oc.save()

    def test_objectchange_list(self):

        url = reverse('extras:objectchange_list')
        params = {
            "user": User.objects.first().pk,
        }

        response = self.client.get('{}?{}'.format(url, urllib.parse.urlencode(params)))
        self.assertHttpStatus(response, 200)

    def test_objectchange(self):

        objectchange = ObjectChange.objects.first()
        response = self.client.get(objectchange.get_absolute_url())
        self.assertHttpStatus(response, 200)


class CustomLinkTest(TestCase):
    user_permissions = ['dcim.view_site']

    def test_view_object_with_custom_link(self):
        customlink = CustomLink(
            content_type=ContentType.objects.get_for_model(Site),
            name='Test',
            text='FOO {{ obj.name }} BAR',
            url='http://example.com/?site={{ obj.slug }}',
            new_window=False
        )
        customlink.save()

        site = Site(name='Test Site', slug='test-site')
        site.save()

        response = self.client.get(site.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'FOO {site.name} BAR', str(response.content))


class GitRepositoryTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = GitRepository

    @classmethod
    def setUpTestData(cls):

        # Create three GitRepository records
        repos = (
            GitRepository(name='Repo 1', slug='repo-1', remote_url='https://example.com/repo1.git'),
            GitRepository(name='Repo 2', slug='repo-2', remote_url='https://example.com/repo2.git'),
            GitRepository(name='Repo 3', slug='repo-3', remote_url='https://example.com/repo3.git'),
        )
        for repo in repos:
            repo.save(trigger_resync=False)

        cls.form_data = {
            'name': 'A new Git repository',
            'slug': 'a-new-git-repository',
            'remote_url': 'http://example.com/a_new_git_repository.git',
            'branch': 'develop',
            '_token': '1234567890abcdef1234567890abcdef',
            'provided_contents': ['extras.ConfigContext', 'extras.Job', 'extras.ExportTemplate'],
        }


class StatusTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = Status

    @classmethod
    def setUpTestData(cls):

        # Status objects to test.
        statuses = (
            Status(name='status1'),
            Status(name='status2'),
            Status(name='status3'),
        )
        for status in statuses:
            status.save()

        content_type = ContentType.objects.get_for_model(Device)

        cls.form_data = {
            'name': 'new_status',
            'color': 'ffcc00',
            'content_types': [content_type.pk],
        }

        cls.csv_data = (
            'name,color,content_types'
            'test_status1,ffffff,"dcim.device"'
            'test_status2,ffffff,"dcim.device,dcim.rack"'
            'test_status3,ffffff,"dcim.device,dcim.site"'
        )

        cls.bulk_edit_data = {
            'color': '000000',
        }
