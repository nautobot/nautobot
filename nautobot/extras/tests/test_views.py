import urllib.parse
import uuid

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nautobot.dcim.models import ConsolePort, Device, Site
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.constants import *
from nautobot.extras.models import (
    ConfigContext,
    CustomLink,
    ExportTemplate,
    GitRepository,
    ObjectChange,
    Status,
    Tag,
    Webhook,
)
from nautobot.utilities.testing import ViewTestCases, TestCase


class TagTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = Tag

    @classmethod
    def setUpTestData(cls):

        Tag.objects.create(name="Tag 1", slug="tag-1")
        Tag.objects.create(name="Tag 2", slug="tag-2")
        Tag.objects.create(name="Tag 3", slug="tag-3")

        cls.form_data = {
            "name": "Tag X",
            "slug": "tag-x",
            "color": "c0c0c0",
            "comments": "Some comments",
        }

        cls.csv_data = (
            "name,slug,color,description",
            "Tag 4,tag-4,ff0000,Fourth tag",
            "Tag 5,tag-5,00ff00,Fifth tag",
            "Tag 6,tag-6,0000ff,Sixth tag",
        )

        cls.bulk_edit_data = {
            "color": "00ff00",
        }


# TODO: Change base class to PrimaryObjectViewTestCase
# Blocked by absence of standard create/edit, bulk create views
class ConfigContextTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ConfigContext

    @classmethod
    def setUpTestData(cls):

        site = Site.objects.create(name="Site 1", slug="site-1")

        # Create three ConfigContexts
        for i in range(1, 4):
            configcontext = ConfigContext(name="Config Context {}".format(i), data={"foo": i})
            configcontext.save()
            configcontext.sites.add(site)

        cls.form_data = {
            "name": "Config Context X",
            "weight": 200,
            "description": "A new config context",
            "is_active": True,
            "regions": [],
            "sites": [site.pk],
            "roles": [],
            "platforms": [],
            "tenant_groups": [],
            "tenants": [],
            "tags": [],
            "data": '{"foo": 123}',
        }

        cls.bulk_edit_data = {
            "weight": 300,
            "is_active": False,
            "description": "New description",
        }


# TODO: Convert to StandardTestCases.Views
class ObjectChangeTestCase(TestCase):
    user_permissions = ("extras.view_objectchange",)

    @classmethod
    def setUpTestData(cls):

        site = Site(name="Site 1", slug="site-1")
        site.save()

        # Create three ObjectChanges
        user = User.objects.create_user(username="testuser2")
        for i in range(1, 4):
            oc = site.to_objectchange(action=ObjectChangeActionChoices.ACTION_UPDATE)
            oc.user = user
            oc.request_id = uuid.uuid4()
            oc.save()

    def test_objectchange_list(self):

        url = reverse("extras:objectchange_list")
        params = {
            "user": User.objects.first().pk,
        }

        response = self.client.get("{}?{}".format(url, urllib.parse.urlencode(params)))
        self.assertHttpStatus(response, 200)

    def test_objectchange(self):

        objectchange = ObjectChange.objects.first()
        response = self.client.get(objectchange.get_absolute_url())
        self.assertHttpStatus(response, 200)


class CustomLinkTest(TestCase):
    user_permissions = ["dcim.view_site"]

    def test_view_object_with_custom_link(self):
        customlink = CustomLink(
            content_type=ContentType.objects.get_for_model(Site),
            name="Test",
            text="FOO {{ obj.name }} BAR",
            target_url="http://example.com/?site={{ obj.slug }}",
            new_window=False,
        )
        customlink.save()

        site = Site(name="Test Site", slug="test-site")
        site.save()

        response = self.client.get(site.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(f"FOO {site.name} BAR", str(response.content))


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
            GitRepository(name="Repo 1", slug="repo-1", remote_url="https://example.com/repo1.git"),
            GitRepository(name="Repo 2", slug="repo-2", remote_url="https://example.com/repo2.git"),
            GitRepository(name="Repo 3", slug="repo-3", remote_url="https://example.com/repo3.git"),
        )
        for repo in repos:
            repo.save(trigger_resync=False)

        cls.form_data = {
            "name": "A new Git repository",
            "slug": "a-new-git-repository",
            "remote_url": "http://example.com/a_new_git_repository.git",
            "branch": "develop",
            "_token": "1234567890abcdef1234567890abcdef",
            "provided_contents": [
                "extras.configcontext",
                "extras.job",
                "extras.exporttemplate",
            ],
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
        Status.objects.create(name="Status 1", slug="status-1")
        Status.objects.create(name="Status 2", slug="status-2")
        Status.objects.create(name="Status 3", slug="status-3")

        content_type = ContentType.objects.get_for_model(Device)

        cls.form_data = {
            "name": "new_status",
            "slug": "new-status",
            "description": "I am a new status object.",
            "color": "ffcc00",
            "content_types": [content_type.pk],
        }

        cls.csv_data = (
            "name,slug,color,content_types"
            'test_status1,test-status1,ffffff,"dcim.device"'
            'test_status2,test-status2,ffffff,"dcim.device,dcim.rack"'
            'test_status3,test-status3,ffffff,"dcim.device,dcim.site"'
        )

        cls.bulk_edit_data = {
            "color": "000000",
        }


class ExportTemplateTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = ExportTemplate

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Site)

        templates = (
            ExportTemplate(
                name="template-1",
                template_code="template-1 test1",
                content_type=obj_type,
            ),
            ExportTemplate(
                name="template-2",
                template_code="template-2 test2",
                content_type=obj_type,
            ),
            ExportTemplate(
                name="template-3",
                template_code="template-3 test3",
                content_type=obj_type,
            ),
        )

        for template in templates:
            template.save()

        cls.form_data = {
            "name": "template-4",
            "content_type": obj_type.pk,
            "template_code": "template-4 test4",
        }


class CustomLinkTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = CustomLink

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Site)

        customlinks = (
            CustomLink(
                content_type=obj_type,
                name="customlink-1",
                text="customlink text 1",
                target_url="http://customlink1.com",
                weight=100,
                button_class="default",
                new_window=False,
            ),
            CustomLink(
                content_type=obj_type,
                name="customlink-2",
                text="customlink text 2",
                target_url="http://customlink2.com",
                weight=100,
                button_class="default",
                new_window=False,
            ),
            CustomLink(
                content_type=obj_type,
                name="customlink-3",
                text="customlink text 3",
                target_url="http://customlink3.com",
                weight=100,
                button_class="default",
                new_window=False,
            ),
        )

        for link in customlinks:
            link.save()

        cls.form_data = {
            "content_type": obj_type.pk,
            "name": "customlink-4",
            "text": "customlink text 4",
            "target_url": "http://customlink4.com",
            "weight": 100,
            "button_class": "default",
            "new_window": False,
        }


class WebhookTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = Webhook

    @classmethod
    def setUpTestData(cls):
        webhooks = (
            Webhook(
                name="webhook-1",
                enabled=True,
                type_create=True,
                payload_url="http://test-url.com/test-1",
                http_content_type=HTTP_CONTENT_TYPE_JSON,
            ),
            Webhook(
                name="webhook-2",
                enabled=True,
                type_update=True,
                payload_url="http://test-url.com/test-2",
                http_content_type=HTTP_CONTENT_TYPE_JSON,
            ),
            Webhook(
                name="webhook-3",
                enabled=True,
                type_delete=True,
                payload_url="http://test-url.com/test-3",
                http_content_type=HTTP_CONTENT_TYPE_JSON,
            ),
        )

        obj_type = ContentType.objects.get_for_model(ConsolePort)

        for webhook in webhooks:
            webhook.save()
            webhook.content_types.set([obj_type])

        cls.form_data = {
            "name": "webhook-4",
            "content_types": [obj_type.pk],
            "enabled": True,
            "type_create": True,
            "payload_url": "http://test-url.com/test-4",
            "http_method": "POST",
            "http_content_type": "application/json",
        }
