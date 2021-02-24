import datetime
import os.path
import uuid
from unittest import skipIf

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.test import override_settings
from django.urls import reverse
from django.utils.timezone import make_aware
from django_rq.queues import get_connection
from rest_framework import status
from rq import Worker

from nautobot.dcim.models import (
    Device,
    DeviceRole,
    DeviceType,
    Manufacturer,
    Rack,
    RackGroup,
    RackRole,
    Site,
)
from nautobot.extras.api.views import JobViewSet
from nautobot.extras.models import (
    ConfigContext,
    CustomField,
    CustomLink,
    ExportTemplate,
    GitRepository,
    ImageAttachment,
    JobResult,
    Status,
    Tag,
    Webhook,
)
from nautobot.extras.jobs import Job, BooleanVar, IntegerVar, StringVar
from nautobot.utilities.testing import APITestCase, APIViewTestCases
from nautobot.utilities.testing.utils import disable_warnings


rq_worker_running = Worker.count(get_connection("default"))


THIS_DIRECTORY = os.path.dirname(__file__)


class AppTest(APITestCase):
    def test_root(self):

        url = reverse("extras-api:api-root")
        response = self.client.get("{}?format=api".format(url), **self.header)

        self.assertEqual(response.status_code, 200)


class CustomFieldTest(APIViewTestCases.APIViewTestCase):
    model = CustomField
    brief_fields = ["id", "name", "url"]
    create_data = [
        {
            "content_types": ["dcim.site"],
            "name": "cf4",
            "type": "date",
        },
        {
            "content_types": ["dcim.site"],
            "name": "cf5",
            "type": "url",
        },
        {
            "content_types": ["dcim.site"],
            "name": "cf6",
            "type": "select",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        site_ct = ContentType.objects.get_for_model(Site)

        custom_fields = (
            CustomField.objects.create(name="cf1", type="text"),
            CustomField.objects.create(name="cf2", type="integer"),
            CustomField.objects.create(name="cf3", type="boolean"),
        )
        for cf in custom_fields:
            cf.content_types.add(site_ct)


class ExportTemplateTest(APIViewTestCases.APIViewTestCase):
    model = ExportTemplate
    brief_fields = ["id", "name", "url"]
    create_data = [
        {
            "content_type": "dcim.device",
            "name": "Test Export Template 4",
            "template_code": "{% for obj in queryset %}{{ obj.name }}\n{% endfor %}",
        },
        {
            "content_type": "dcim.device",
            "name": "Test Export Template 5",
            "template_code": "{% for obj in queryset %}{{ obj.name }}\n{% endfor %}",
        },
        {
            "content_type": "dcim.device",
            "name": "Test Export Template 6",
            "template_code": "{% for obj in queryset %}{{ obj.name }}\n{% endfor %}",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        ct = ContentType.objects.get_for_model(Device)

        ExportTemplate.objects.create(
            content_type=ct,
            name="Export Template 1",
            template_code="{% for obj in queryset %}{{ obj.name }}\n{% endfor %}",
        )
        ExportTemplate.objects.create(
            content_type=ct,
            name="Export Template 2",
            template_code="{% for obj in queryset %}{{ obj.name }}\n{% endfor %}",
        )
        ExportTemplate.objects.create(
            content_type=ct,
            name="Export Template 3",
            template_code="{% for obj in queryset %}{{ obj.name }}\n{% endfor %}",
        )


class TagTest(APIViewTestCases.APIViewTestCase):
    model = Tag
    brief_fields = ["color", "id", "name", "slug", "url"]
    create_data = [
        {
            "name": "Tag 4",
            "slug": "tag-4",
        },
        {
            "name": "Tag 5",
            "slug": "tag-5",
        },
        {
            "name": "Tag 6",
            "slug": "tag-6",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        Tag.objects.create(name="Tag 1", slug="tag-1")
        Tag.objects.create(name="Tag 2", slug="tag-2")
        Tag.objects.create(name="Tag 3", slug="tag-3")


class GitRepositoryTest(APIViewTestCases.APIViewTestCase):
    model = GitRepository
    brief_fields = ["id", "name", "url"]
    create_data = [
        {
            "name": "New Git Repository 1",
            "slug": "new-git-repository-1",
            "remote_url": "https://example.com/newrepo1.git",
        },
        {
            "name": "New Git Repository 2",
            "slug": "new-git-repository-2",
            "remote_url": "https://example.com/newrepo2.git",
        },
        {
            "name": "New Git Repository 3",
            "slug": "new-git-repository-3",
            "remote_url": "https://example.com/newrepo3.git",
        },
    ]
    bulk_update_data = {
        "branch": "develop",
    }

    @classmethod
    def setUpTestData(cls):
        repos = (
            GitRepository(name="Repo 1", slug="repo-1", remote_url="https://example.com/repo1.git"),
            GitRepository(name="Repo 2", slug="repo-2", remote_url="https://example.com/repo2.git"),
            GitRepository(name="Repo 3", slug="repo-3", remote_url="https://example.com/repo3.git"),
        )
        for repo in repos:
            repo.save(trigger_resync=False)


# TODO: Standardize to APIViewTestCase (needs create & update tests)
class ImageAttachmentTest(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.DeleteObjectViewTestCase,
):
    model = ImageAttachment
    brief_fields = ["id", "image", "name", "url"]

    @classmethod
    def setUpTestData(cls):
        ct = ContentType.objects.get_for_model(Site)

        site = Site.objects.create(name="Site 1", slug="site-1")

        ImageAttachment.objects.create(
            content_type=ct,
            object_id=site.pk,
            name="Image Attachment 1",
            image="http://example.com/image1.png",
            image_height=100,
            image_width=100,
        )
        ImageAttachment.objects.create(
            content_type=ct,
            object_id=site.pk,
            name="Image Attachment 2",
            image="http://example.com/image2.png",
            image_height=100,
            image_width=100,
        )
        ImageAttachment.objects.create(
            content_type=ct,
            object_id=site.pk,
            name="Image Attachment 3",
            image="http://example.com/image3.png",
            image_height=100,
            image_width=100,
        )


class ConfigContextTest(APIViewTestCases.APIViewTestCase):
    model = ConfigContext
    brief_fields = ["id", "name", "url"]
    create_data = [
        {
            "name": "Config Context 4",
            "data": {"more_foo": True},
        },
        {
            "name": "Config Context 5",
            "data": {"more_bar": False},
        },
        {
            "name": "Config Context 6",
            "data": {"more_baz": None},
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        ConfigContext.objects.create(name="Config Context 1", weight=100, data={"foo": 123})
        ConfigContext.objects.create(name="Config Context 2", weight=200, data={"bar": 456})
        ConfigContext.objects.create(name="Config Context 3", weight=300, data={"baz": 789})

    def test_render_configcontext_for_object(self):
        """
        Test rendering config context data for a device.
        """
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        devicerole = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")
        site = Site.objects.create(name="Site-1", slug="site-1")
        device = Device.objects.create(name="Device 1", device_type=devicetype, device_role=devicerole, site=site)

        # Test default config contexts (created at test setup)
        rendered_context = device.get_config_context()
        self.assertEqual(rendered_context["foo"], 123)
        self.assertEqual(rendered_context["bar"], 456)
        self.assertEqual(rendered_context["baz"], 789)

        # Add another context specific to the site
        configcontext4 = ConfigContext(name="Config Context 4", data={"site_data": "ABC"})
        configcontext4.save()
        configcontext4.sites.add(site)
        rendered_context = device.get_config_context()
        self.assertEqual(rendered_context["site_data"], "ABC")

        # Override one of the default contexts
        configcontext5 = ConfigContext(name="Config Context 5", weight=2000, data={"foo": 999})
        configcontext5.save()
        configcontext5.sites.add(site)
        rendered_context = device.get_config_context()
        self.assertEqual(rendered_context["foo"], 999)

        # Add a context which does NOT match our device and ensure it does not apply
        site2 = Site.objects.create(name="Site 2", slug="site-2")
        configcontext6 = ConfigContext(name="Config Context 6", weight=2000, data={"bar": 999})
        configcontext6.save()
        configcontext6.sites.add(site2)
        rendered_context = device.get_config_context()
        self.assertEqual(rendered_context["bar"], 456)


class JobTest(APITestCase):
    class TestJob(Job):
        class Meta:
            name = "Test job"

        var1 = StringVar()
        var2 = IntegerVar()
        var3 = BooleanVar()

        def run(self, data, commit=True):
            self.log_info(message=data["var1"])
            self.log_success(message=data["var2"])
            self.log_failure(message=data["var3"])

            return "Job complete"

        def test_foo(self):
            self.log_success(obj=None, message="Test completed")

    def get_test_job_class(self, class_path):
        if class_path == "local/test_api/TestJob":
            return self.TestJob
        raise Http404

    def setUp(self):
        super().setUp()

        # Monkey-patch the API viewset's _get_job_class method to return our test class above
        JobViewSet._get_job_class = self.get_test_job_class

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], JOBS_ROOT=THIS_DIRECTORY)
    def test_list_jobs_anonymous(self):
        url = reverse("extras-api:job-list")
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[], JOBS_ROOT=THIS_DIRECTORY)
    def test_list_jobs_without_permission(self):
        url = reverse("extras-api:job-list")
        with disable_warnings("django.request"):
            response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[], JOBS_ROOT=THIS_DIRECTORY)
    @skipIf(
        "nautobot.extras.tests.dummy_plugin" not in settings.PLUGINS,
        "dummy_plugin not in settings.PLUGINS",
    )
    def test_list_jobs_with_permission(self):
        self.add_permissions("extras.view_job")
        url = reverse("extras-api:job-list")
        response = self.client.get(url, **self.header)

        self.assertHttpStatus(response, status.HTTP_200_OK)
        # At a minimum, the job provided by the dummy plugin should be present
        self.assertNotEqual(response.data, [])
        self.assertIn(
            "plugins/nautobot.extras.tests.dummy_plugin.jobs/DummyJob",
            [job["id"] for job in response.data],
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], JOBS_ROOT=THIS_DIRECTORY)
    def test_get_job_anonymous(self):
        url = reverse("extras-api:job-detail", kwargs={"class_path": "local/test_api/TestJob"})
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[], JOBS_ROOT=THIS_DIRECTORY)
    def test_get_job_without_permission(self):
        url = reverse("extras-api:job-detail", kwargs={"class_path": "local/test_api/TestJob"})
        with disable_warnings("django.request"):
            response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[], JOBS_ROOT=THIS_DIRECTORY)
    def test_get_job_with_permission(self):
        self.add_permissions("extras.view_job")
        # Try GET to permitted object
        url = reverse("extras-api:job-detail", kwargs={"class_path": "local/test_api/TestJob"})
        response = self.client.get(url, **self.header)

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.TestJob.name)
        self.assertEqual(response.data["vars"]["var1"], "StringVar")
        self.assertEqual(response.data["vars"]["var2"], "IntegerVar")
        self.assertEqual(response.data["vars"]["var3"], "BooleanVar")

        # Try GET to non-existent object
        url = reverse("extras-api:job-detail", kwargs={"class_path": "local/test_api/NoSuchJob"})
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_404_NOT_FOUND)

    @skipIf(not rq_worker_running, "RQ worker not running")
    @override_settings(EXEMPT_VIEW_PERMISSIONS=[], JOBS_ROOT=THIS_DIRECTORY)
    def test_run_job_without_permission(self):
        url = reverse("extras-api:job-run", kwargs={"class_path": "local/test_api/TestJob"})
        with disable_warnings("django.request"):
            response = self.client.post(url, {}, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @skipIf(not rq_worker_running, "RQ worker not running")
    @override_settings(EXEMPT_VIEW_PERMISSIONS=[], JOBS_ROOT=THIS_DIRECTORY)
    def test_run_job_with_permission(self):
        self.add_permissions("extras.run_job")
        job_data = {
            "var1": "FooBar",
            "var2": 123,
            "var3": False,
        }

        data = {
            "data": job_data,
            "commit": True,
        }

        url = reverse("extras-api:job-run", kwargs={"class_path": "local/test_api/TestJob"})
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["result"]["status"]["value"], "pending")


class JobResultTest(APITestCase):
    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_delete_job_result_anonymous(self):
        url = reverse("extras-api:jobresult-detail", kwargs={"pk": 1})
        response = self.client.delete(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_delete_job_result_without_permission(self):
        url = reverse("extras-api:jobresult-detail", kwargs={"pk": 1})
        with disable_warnings("django.request"):
            response = self.client.delete(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_delete_job_result_with_permission(self):
        self.add_permissions("extras.delete_jobresult")
        job_result = JobResult.objects.create(
            name="test",
            job_id=uuid.uuid4(),
            obj_type=ContentType.objects.get_for_model(GitRepository),
        )
        url = reverse("extras-api:jobresult-detail", kwargs={"pk": job_result.pk})
        response = self.client.delete(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)


class CreatedUpdatedFilterTest(APITestCase):
    def setUp(self):

        super().setUp()

        self.site1 = Site.objects.create(name="Test Site 1", slug="test-site-1")
        self.rackgroup1 = RackGroup.objects.create(site=self.site1, name="Test Rack Group 1", slug="test-rack-group-1")
        self.rackrole1 = RackRole.objects.create(name="Test Rack Role 1", slug="test-rack-role-1", color="ff0000")
        self.rack1 = Rack.objects.create(
            site=self.site1,
            group=self.rackgroup1,
            role=self.rackrole1,
            name="Test Rack 1",
            u_height=42,
        )
        self.rack2 = Rack.objects.create(
            site=self.site1,
            group=self.rackgroup1,
            role=self.rackrole1,
            name="Test Rack 2",
            u_height=42,
        )

        # change the created and last_updated of one
        Rack.objects.filter(pk=self.rack2.pk).update(
            last_updated=make_aware(datetime.datetime(2001, 2, 3, 1, 2, 3, 4)),
            created=make_aware(datetime.datetime(2001, 2, 3)),
        )

    def test_get_rack_created(self):
        self.add_permissions("dcim.view_rack")
        url = reverse("dcim-api:rack-list")
        response = self.client.get("{}?created=2001-02-03".format(url), **self.header)

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.rack2.pk))

    def test_get_rack_created_gte(self):
        self.add_permissions("dcim.view_rack")
        url = reverse("dcim-api:rack-list")
        response = self.client.get("{}?created__gte=2001-02-04".format(url), **self.header)

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.rack1.pk))

    def test_get_rack_created_lte(self):
        self.add_permissions("dcim.view_rack")
        url = reverse("dcim-api:rack-list")
        response = self.client.get("{}?created__lte=2001-02-04".format(url), **self.header)

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.rack2.pk))

    def test_get_rack_last_updated(self):
        self.add_permissions("dcim.view_rack")
        url = reverse("dcim-api:rack-list")
        response = self.client.get("{}?last_updated=2001-02-03%2001:02:03.000004".format(url), **self.header)

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.rack2.pk))

    def test_get_rack_last_updated_gte(self):
        self.add_permissions("dcim.view_rack")
        url = reverse("dcim-api:rack-list")
        response = self.client.get("{}?last_updated__gte=2001-02-04%2001:02:03.000004".format(url), **self.header)

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.rack1.pk))

    def test_get_rack_last_updated_lte(self):
        self.add_permissions("dcim.view_rack")
        url = reverse("dcim-api:rack-list")
        response = self.client.get("{}?last_updated__lte=2001-02-04%2001:02:03.000004".format(url), **self.header)

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.rack2.pk))


class ContentTypeTest(APITestCase):
    @override_settings(EXEMPT_VIEW_PERMISSIONS=["contenttypes.contenttype"])
    def test_list_objects(self):
        contenttype_count = ContentType.objects.count()

        response = self.client.get(reverse("extras-api:contenttype-list"), **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], contenttype_count)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["contenttypes.contenttype"])
    def test_get_object(self):
        contenttype = ContentType.objects.first()

        url = reverse("extras-api:contenttype-detail", kwargs={"pk": contenttype.pk})
        self.assertHttpStatus(self.client.get(url, **self.header), status.HTTP_200_OK)


class CustomLinkTest(APIViewTestCases.APIViewTestCase):
    model = CustomLink
    brief_fields = ["content_type", "id", "name", "url"]
    create_data = [
        {
            "content_type": "dcim.site",
            "name": "api-test-4",
            "text": "API customlink text 4",
            "target_url": "http://api-test-4.com/test4",
            "weight": 100,
            "new_window": False,
        },
        {
            "content_type": "dcim.site",
            "name": "api-test-5",
            "text": "API customlink text 5",
            "target_url": "http://api-test-5.com/test5",
            "weight": 100,
            "new_window": False,
        },
        {
            "content_type": "dcim.site",
            "name": "api-test-6",
            "text": "API customlink text 6",
            "target_url": "http://api-test-6.com/test6",
            "weight": 100,
            "new_window": False,
        },
    ]

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Site)

        CustomLink.objects.create(
            content_type=obj_type,
            name="api-test-1",
            text="API customlink text 1",
            target_url="http://api-test-1.com/test1",
            weight=100,
            new_window=False,
        )
        CustomLink.objects.create(
            content_type=obj_type,
            name="api-test-2",
            text="API customlink text 2",
            target_url="http://api-test-2.com/test2",
            weight=100,
            new_window=False,
        )
        CustomLink.objects.create(
            content_type=obj_type,
            name="api-test-3",
            text="API customlink text 3",
            target_url="http://api-test-3.com/test3",
            weight=100,
            new_window=False,
        )


class WebhookTest(APIViewTestCases.APIViewTestCase):
    model = Webhook
    brief_fields = ["id", "name", "url"]
    create_data = [
        {
            "content_types": ["dcim.consoleport"],
            "name": "api-test-4",
            "type_create": True,
            "payload_url": "http://api-test-4.com/test4",
            "http_method": "POST",
            "http_content_type": "application/json",
            "ssl_verification": True,
        },
        {
            "content_types": ["dcim.consoleport"],
            "name": "api-test-5",
            "type_update": True,
            "payload_url": "http://api-test-5.com/test5",
            "http_method": "POST",
            "http_content_type": "application/json",
            "ssl_verification": True,
        },
        {
            "content_types": ["dcim.consoleport"],
            "name": "api-test-6",
            "type_delete": True,
            "payload_url": "http://api-test-6.com/test6",
            "http_method": "POST",
            "http_content_type": "application/json",
            "ssl_verification": True,
        },
    ]

    @classmethod
    def setUpTestData(cls):
        webhooks = (
            Webhook(
                name="api-test-1",
                type_create=True,
                payload_url="http://api-test-1.com/test1",
                http_method="POST",
                http_content_type="application/json",
                ssl_verification=True,
            ),
            Webhook(
                name="api-test-2",
                type_update=True,
                payload_url="http://api-test-2.com/test2",
                http_method="POST",
                http_content_type="application/json",
                ssl_verification=True,
            ),
            Webhook(
                name="api-test-3",
                type_delete=True,
                payload_url="http://api-test-3.com/test3",
                http_method="POST",
                http_content_type="application/json",
                ssl_verification=True,
            ),
        )

        obj_type = ContentType.objects.get_for_model(DeviceType)

        for webhook in webhooks:
            webhook.save()
            webhook.content_types.set([obj_type])


class StatusTest(APIViewTestCases.APIViewTestCase):
    model = Status
    brief_fields = ["id", "name", "slug", "url"]
    bulk_update_data = {
        "color": "000000",
    }

    create_data = [
        {
            "name": "Pizza",
            "slug": "pizza",
            "color": "0000ff",
            "content_types": ["dcim.device", "dcim.rack"],
        },
        {
            "name": "Oysters",
            "slug": "oysters",
            "color": "00ff00",
            "content_types": ["ipam.ipaddress", "ipam.prefix"],
        },
        {
            "name": "Bad combinations",
            "slug": "bad-combinations",
            "color": "ff0000",
            "content_types": ["dcim.device"],
        },
    ]

    @classmethod
    def setUpTestData(cls):
        """
        Since many `Status` objects are created as part of data migrations, we're
        testing against those. If this seems magical, it's because they are
        imported from `ChoiceSet` enum objects.

        This method is defined just so it's clear that there is no need to
        create test data for this test case.

        See `extras.management.create_custom_statuses` for context.
        """
