from datetime import datetime, timedelta
import os.path
import urllib.parse
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings, SimpleTestCase
from django.urls import reverse
from django.utils import timezone
from unittest import mock

from nautobot.dcim.models import ConsolePort, Device, DeviceRole, DeviceType, Interface, Manufacturer, Site
from nautobot.extras.choices import CustomFieldTypeChoices, JobExecutionType, ObjectChangeActionChoices
from nautobot.extras.constants import *
from nautobot.extras.jobs import Job
from nautobot.extras.models import (
    ConfigContext,
    ConfigContextSchema,
    CustomField,
    CustomLink,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    JobResult,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    ScheduledJob,
    Status,
    Tag,
    Webhook,
    ComputedField,
)
from nautobot.extras.views import JobView, ScheduledJobView
from nautobot.ipam.models import VLAN
from nautobot.utilities.testing import ViewTestCases, TestCase, extract_page_body, extract_form_failures
from nautobot.utilities.testing.utils import post_data


# Use the proper swappable User model
User = get_user_model()

THIS_DIRECTORY = os.path.dirname(__file__)
DUMMY_JOBS = os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")


class ComputedFieldTestCase(
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = ComputedField

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Site)

        computed_fields = (
            ComputedField(
                content_type=obj_type,
                label="Computed Field One",
                slug="computed_field_one",
                template="Site name is {{ obj.name }}",
                fallback_value="Template error",
                weight=100,
            ),
            ComputedField(
                content_type=obj_type,
                slug="computed_field_two",
                label="Computed Field Two",
                template="Site name is {{ obj.name }}",
                fallback_value="Template error",
                weight=100,
            ),
            ComputedField(
                content_type=obj_type,
                slug="computed_field_three",
                label="Computed Field Three",
                template="Site name is {{ obj.name }}",
                weight=100,
            ),
            ComputedField(
                content_type=obj_type,
                label="Computed Field Five",
                template="Site name is {{ obj.name }}",
                fallback_value="Template error",
                weight=100,
            ),
        )

        cls.site1 = Site(name="NYC")
        cls.site1.save()

        for cf in computed_fields:
            cf.save()

        cls.form_data = {
            "content_type": obj_type.pk,
            "slug": "computed_field_four",
            "label": "Computed Field Four",
            "template": "{{ obj.name }} is the best Site!",
            "fallback_value": ":skull_emoji:",
            "weight": 100,
        }

        cls.slug_source = "label"
        cls.slug_test_object = "Computed Field Five"


# TODO: Change base class to PrimaryObjectViewTestCase
# Blocked by absence of standard create/edit, bulk create views
class ConfigContextTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
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
            "device_types": [],
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

    def test_schema_validation_pass(self):
        """
        Given a config context schema
        And a config context that conforms to that schema
        Assert that the config context passes schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1", slug="schema-1", data_schema={"type": "object", "properties": {"foo": {"type": "string"}}}
        )
        self.add_permissions("extras.add_configcontext")
        self.add_permissions("extras.view_configcontextschema")

        form_data = {
            "name": "Config Context with schema",
            "weight": 200,
            "description": "A new config context",
            "is_active": True,
            "regions": [],
            "sites": [],
            "roles": [],
            "device_types": [],
            "platforms": [],
            "tenant_groups": [],
            "tenants": [],
            "tags": [],
            "data": '{"foo": "bar"}',
            "schema": schema.pk,
        }

        # Try POST with model-level permission
        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertEqual(self._get_queryset().get(name="Config Context with schema").schema.pk, schema.pk)

    def test_schema_validation_fails(self):
        """
        Given a config context schema
        And a config context that *does not* conform to that schema
        Assert that the config context fails schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1", slug="schema-1", data_schema={"type": "object", "properties": {"foo": {"type": "integer"}}}
        )
        self.add_permissions("extras.add_configcontext")
        self.add_permissions("extras.view_configcontextschema")

        form_data = {
            "name": "Config Context with bad schema",
            "weight": 200,
            "description": "A new config context",
            "is_active": True,
            "regions": [],
            "sites": [],
            "roles": [],
            "device_types": [],
            "platforms": [],
            "tenant_groups": [],
            "tenants": [],
            "tags": [],
            "data": '{"foo": "bar"}',
            "schema": schema.pk,
        }

        # Try POST with model-level permission
        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 200)
        self.assertEqual(self._get_queryset().filter(name="Config Context with schema").count(), 0)


# This OrganizationalObjectViewTestCase less BulkImportObjectsViewTestCase
# because it doesn't make sense to support CSV for schemas.
class ConfigContextSchemaTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
):
    model = ConfigContextSchema

    @classmethod
    def setUpTestData(cls):

        # Create three ConfigContextSchema records
        ConfigContextSchema.objects.create(
            name="Schema 1", slug="schema-1", data_schema={"type": "object", "properties": {"foo": {"type": "string"}}}
        ),
        ConfigContextSchema.objects.create(
            name="Schema 2", slug="schema-2", data_schema={"type": "object", "properties": {"bar": {"type": "string"}}}
        ),
        ConfigContextSchema.objects.create(
            name="Schema 3", slug="schema-3", data_schema={"type": "object", "properties": {"baz": {"type": "string"}}}
        ),
        ConfigContextSchema.objects.create(
            name="Schema 4", data_schema={"type": "object", "properties": {"baz": {"type": "string"}}}
        ),

        cls.form_data = {
            "name": "Schema X",
            "slug": "schema-x",
            "data_schema": '{"type": "object", "properties": {"baz": {"type": "string"}}}',
        }

        cls.bulk_edit_data = {
            "description": "New description",
        }

        cls.slug_source = "name"
        cls.slug_test_object = "Schema 4"


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


class CustomFieldTestCase(
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = CustomField
    reverse_url_attribute = "name"

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Site)

        custom_fields = [
            CustomField(
                type=CustomFieldTypeChoices.TYPE_BOOLEAN,
                name="Custom Field Boolean",
                label="Custom Field Boolean",
                default="",
            ),
            CustomField(
                type=CustomFieldTypeChoices.TYPE_TEXT,
                name="Custom Field Text",
                label="Custom Field Text",
                default="",
            ),
            CustomField(
                type=CustomFieldTypeChoices.TYPE_INTEGER,
                name="Custom Field Integer",
                label="Custom Field Integer",
                default="",
            ),
        ]

        for custom_field in custom_fields:
            custom_field.validated_save()
            custom_field.content_types.set([obj_type])

        cls.form_data = {
            "content_types": [obj_type.pk],
            "type": CustomFieldTypeChoices.TYPE_BOOLEAN,
            "name": "Custom Field Boolean",
            "label": "Custom Field Boolean",
            "default": None,
            "filter_logic": "loose",
            "weight": 100,
        }

    def test_create_object_without_permission(self):
        # Can't have two CustomFields with the same "name"
        for cf in CustomField.objects.all():
            cf.delete()
        super().test_create_object_without_permission()

    def test_create_object_with_permission(self):
        # Can't have two CustomFields with the same "name"
        for cf in CustomField.objects.all():
            cf.delete()
        super().test_create_object_with_permission()

    def test_create_object_with_constrained_permission(self):
        # Can't have two CustomFields with the same "name"
        for cf in CustomField.objects.all():
            cf.delete()
        super().test_create_object_with_constrained_permission()


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
        content = extract_page_body(response.content.decode(response.charset))
        self.assertIn(f"FOO {site.name} BAR", content, content)


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

        # Create four GitRepository records
        repos = (
            GitRepository(name="Repo 1", slug="repo-1", remote_url="https://example.com/repo1.git"),
            GitRepository(name="Repo 2", slug="repo-2", remote_url="https://example.com/repo2.git"),
            GitRepository(name="Repo 3", slug="repo-3", remote_url="https://example.com/repo3.git"),
            GitRepository(name="Repo 4", remote_url="https://example.com/repo4.git"),
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

        cls.slug_source = "name"
        cls.slug_test_object = "Repo 4"


class GraphQLQueriesTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = GraphQLQuery

    @classmethod
    def setUpTestData(cls):
        graphqlqueries = (
            GraphQLQuery(
                name="graphql-query-1",
                slug="graphql-query-1",
                query="{ query: sites {name} }",
            ),
            GraphQLQuery(
                name="graphql-query-2",
                slug="graphql-query-2",
                query='{ devices(role: "edge") { id, name, device_role { name slug } } }',
            ),
            GraphQLQuery(
                name="graphql-query-3",
                slug="graphql-query-3",
                query="""
query ($device: String!) {
  devices(name: $device) {
    config_context
    name
    position
    serial
    primary_ip4 {
      id
      primary_ip4_for {
        id
        name
      }
    }
    tenant {
      name
    }
    tags {
      name
      slug
    }
    device_role {
      name
    }
    platform {
      name
      slug
      manufacturer {
        name
      }
      napalm_driver
    }
    site {
      name
      slug
      vlans {
        id
        name
        vid
      }
      vlan_groups {
        id
      }
    }
    interfaces {
      description
      mac_address
      enabled
      name
      ip_addresses {
        address
        tags {
          id
        }
      }
      connected_circuit_termination {
        circuit {
          cid
          commit_rate
          provider {
            name
          }
        }
      }
      tagged_vlans {
        id
      }
      untagged_vlan {
        id
      }
      cable {
        termination_a_type
        status {
          name
        }
        color
      }
      tagged_vlans {
        site {
          name
        }
        id
      }
      tags {
        id
      }
    }
  }
}""",
            ),
            GraphQLQuery(
                name="Graphql Query 5",
                query='{ devices(role: "edge") { id, name, device_role { name slug } } }',
            ),
        )

        for query in graphqlqueries:
            query.full_clean()
            query.save()

        cls.form_data = {
            "name": "graphql-query-4",
            "slug": "graphql-query-4",
            "query": "{query: sites {name}}",
        }

        cls.slug_source = "name"
        cls.slug_test_object = "Graphql Query 5"


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


class RelationshipTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    # TODO? ViewTestCases.GetObjectViewTestCase,
    # TODO? ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = Relationship

    @classmethod
    def setUpTestData(cls):
        device_type = ContentType.objects.get_for_model(Device)
        interface_type = ContentType.objects.get_for_model(Interface)
        vlan_type = ContentType.objects.get_for_model(VLAN)

        Relationship.objects.create(
            name="Device VLANs",
            slug="device-vlans",
            type="many-to-many",
            source_type=device_type,
            destination_type=vlan_type,
        )
        Relationship.objects.create(
            name="Primary VLAN",
            slug="primary-vlan",
            type="one-to-many",
            source_type=vlan_type,
            destination_type=device_type,
        )
        Relationship.objects.create(
            name="Primary Interface",
            type="one-to-one",
            source_type=device_type,
            destination_type=interface_type,
        )

        cls.form_data = {
            "name": "VLAN-to-Interface",
            "slug": "vlan-to-interface",
            "type": "many-to-many",
            "source_type": vlan_type.pk,
            "source_label": "Interfaces",
            "source_hidden": False,
            "source_filter": '{"status": ["active"]}',
            "destination_type": interface_type.pk,
            "destination_label": "VLANs",
            "destination_hidden": True,
            "destination_filter": None,
        }

        cls.slug_source = "name"
        cls.slug_test_object = "Primary Interface"


class RelationshipAssociationTestCase(
    # TODO? ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    # TODO? ViewTestCases.EditObjectViewTestCase,
    # TODO? ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = RelationshipAssociation

    @classmethod
    def setUpTestData(cls):
        device_type = ContentType.objects.get_for_model(Device)
        vlan_type = ContentType.objects.get_for_model(VLAN)

        relationship = Relationship.objects.create(
            name="Device VLANs",
            slug="device-vlans",
            type="many-to-many",
            source_type=device_type,
            destination_type=vlan_type,
        )
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        devicerole = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")
        site = Site.objects.create(name="Site 1", slug="site-1")
        devices = (
            Device.objects.create(name="Device 1", device_type=devicetype, device_role=devicerole, site=site),
            Device.objects.create(name="Device 2", device_type=devicetype, device_role=devicerole, site=site),
            Device.objects.create(name="Device 3", device_type=devicetype, device_role=devicerole, site=site),
        )
        vlans = (
            VLAN.objects.create(vid=1, name="VLAN 1"),
            VLAN.objects.create(vid=2, name="VLAN 2"),
            VLAN.objects.create(vid=3, name="VLAN 3"),
        )

        RelationshipAssociation.objects.create(
            relationship=relationship,
            source_type=device_type,
            source_id=devices[0].pk,
            destination_type=vlan_type,
            destination_id=vlans[0].pk,
        )
        RelationshipAssociation.objects.create(
            relationship=relationship,
            source_type=device_type,
            source_id=devices[1].pk,
            destination_type=vlan_type,
            destination_id=vlans[1].pk,
        )
        RelationshipAssociation.objects.create(
            relationship=relationship,
            source_type=device_type,
            source_id=devices[2].pk,
            destination_type=vlan_type,
            destination_id=vlans[2].pk,
        )


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
        Status.objects.create(name="Status 4")

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
            'test_status4,,ffffff,"dcim.device,dcim.site"'
        )

        cls.bulk_edit_data = {
            "color": "000000",
        }

        cls.slug_source = "name"
        cls.slug_test_object = "Status 4"


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


@override_settings(JOBS_ROOT=THIS_DIRECTORY)
class TestJobMixin(SimpleTestCase):
    class TestJob(Job):
        pass

    def get_test_job_class(self, class_path):
        if class_path.startswith("local/test_view"):
            return self.TestJob
        raise Http404

    def setUp(self):
        super().setUp()

        # Monkey-patch the viewsets' _get_job methods to return our test class above
        JobView._get_job = self.get_test_job_class
        ScheduledJobView._get_job = self.get_test_job_class


class ScheduledJobTestCase(
    TestJobMixin,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
):
    model = ScheduledJob

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="user1", is_active=True)
        ScheduledJob.objects.create(
            name="test1",
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class="local/test_views/TestJob",
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=user,
            start_time=datetime.now(),
        )
        ScheduledJob.objects.create(
            name="test2",
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class="local/test_views/TestJob",
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=user,
            start_time=datetime.now(),
        )
        ScheduledJob.objects.create(
            name="test3",
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class="local/test_views/TestJob",
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=user,
            start_time=datetime.now(),
        )
        # this should not appear, since it’s not enabled
        ScheduledJob.objects.create(
            enabled=False,
            name="test4",
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class="local/test_views/TestJob",
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=user,
            start_time=datetime.now(),
        )

    def test_only_enabled_is_listed(self):
        self.add_permissions("extras.view_scheduledjob")

        response = self.client.get(self._get_url("list"))
        self.assertHttpStatus(response, 200)
        self.assertNotIn("test4", extract_page_body(response.content.decode(response.charset)))


class ApprovalQueueTestCase(
    ViewTestCases.ListObjectsViewTestCase,
):
    model = ScheduledJob

    def _get_url(self, action, instance=None):
        if action != "list":
            raise ValueError("This override is only valid for list test cases")
        return reverse("extras:scheduledjob_approval_queue_list")

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="user1", is_active=True)
        ScheduledJob.objects.create(
            name="test1",
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class="-",
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=user,
            approval_required=True,
            start_time=datetime.now(),
        )
        ScheduledJob.objects.create(
            name="test2",
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class="-",
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=user,
            approval_required=True,
            start_time=datetime.now(),
        )
        ScheduledJob.objects.create(
            name="test3",
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class="-",
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=user,
            approval_required=True,
            start_time=datetime.now(),
        )
        ScheduledJob.objects.create(
            name="test4",
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class="-",
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=user,
            approval_required=False,
            start_time=datetime.now(),
        )

    def test_only_approvable_is_listed(self):
        self.add_permissions("extras.view_scheduledjob")

        response = self.client.get(self._get_url("list"))
        self.assertHttpStatus(response, 200)
        self.assertNotIn("test4", extract_page_body(response.content.decode(response.charset)))


class JobResultTestCase(
    TestJobMixin,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = JobResult

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get(app_label="extras", model="job")
        JobResult.objects.create(
            name="local/test_view/TestJob",
            job_id=uuid.uuid4(),
            obj_type=obj_type,
        )
        JobResult.objects.create(
            name="local/test_view/TestJob2",
            job_id=uuid.uuid4(),
            obj_type=obj_type,
        )
        JobResult.objects.create(
            name="local/test_view/TestJob3",
            job_id=uuid.uuid4(),
            obj_type=obj_type,
        )


class JobTestCase(
    TestCase,
):
    """
    The Job view test cases.

    Since Job is not an actual model, we have to improvise and test the views
    manually.
    """

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_list_without_permission(self):
        self.assertHttpStatus(self.client.get(reverse("extras:job_list")), 403)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_list(self):
        response = self.client.get(reverse("extras:job_list"))
        self.assertHttpStatus(response, 200)

        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("DummyJob", response_body)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[], JOBS_ROOT=DUMMY_JOBS)
    def test_get_without_permission(self):
        response = self.client.get(reverse("extras:job", kwargs={"class_path": "local/test_pass/TestPass"}))
        self.assertHttpStatus(response, 403)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], JOBS_ROOT=DUMMY_JOBS)
    def test_get(self):
        response = self.client.get(reverse("extras:job", kwargs={"class_path": "local/test_pass/TestPass"}))
        self.assertHttpStatus(response, 200)

        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("TestPass", response_body)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[], JOBS_ROOT=DUMMY_JOBS)
    def test_post_without_permission(self):
        response = self.client.post(reverse("extras:job", kwargs={"class_path": "local/test_pass/TestPass"}))
        self.assertHttpStatus(response, 403)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], JOBS_ROOT=DUMMY_JOBS)
    def test_run_without_schedule(self):
        self.add_permissions("extras.run_job")

        response = self.client.post(reverse("extras:job", kwargs={"class_path": "local/test_pass/TestPass"}))

        self.assertHttpStatus(response, 200)
        errors = extract_form_failures(response.content.decode(response.charset))
        self.assertEqual(errors, ["_schedule_type: This field is required."])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], JOBS_ROOT=DUMMY_JOBS)
    def test_run_now_no_worker(self):
        self.add_permissions("extras.run_job")

        data = {
            "_schedule_type": "immediately",
        }

        response = self.client.post(reverse("extras:job", kwargs={"class_path": "local/test_pass/TestPass"}), data)

        self.assertHttpStatus(response, 200)
        content = extract_page_body(response.content.decode(response.charset))
        self.assertIn("Celery worker process not running.", content)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], JOBS_ROOT=DUMMY_JOBS)
    @mock.patch("nautobot.extras.views.get_worker_count")
    def test_run_now(self, patched):
        self.add_permissions("extras.run_job")

        data = {
            "_schedule_type": "immediately",
        }

        patched.return_value = 1
        response = self.client.post(reverse("extras:job", kwargs={"class_path": "local/test_pass/TestPass"}), data)

        result = JobResult.objects.last()
        self.assertRedirects(response, reverse("extras:job_jobresult", kwargs={"pk": result.pk}))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], JOBS_ROOT=DUMMY_JOBS)
    def test_run_now_missing_args(self):
        self.add_permissions("extras.run_job")

        data = {
            "_schedule_type": "immediately",
        }

        response = self.client.post(
            reverse("extras:job", kwargs={"class_path": "local/test_required_args/TestRequired"}), data
        )

        self.assertHttpStatus(response, 200)
        errors = extract_form_failures(response.content.decode(response.charset))
        self.assertEqual(errors, ["var: This field is required."])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], JOBS_ROOT=DUMMY_JOBS)
    @mock.patch("nautobot.extras.views.get_worker_count")
    def test_run_now_with_args(self, patched):
        self.add_permissions("extras.run_job")

        data = {
            "_schedule_type": "immediately",
            "var": "12",
        }

        patched.return_value = 1
        response = self.client.post(
            reverse("extras:job", kwargs={"class_path": "local/test_required_args/TestRequired"}), data
        )

        result = JobResult.objects.last()
        self.assertRedirects(response, reverse("extras:job_jobresult", kwargs={"pk": result.pk}))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], JOBS_ROOT=DUMMY_JOBS)
    @mock.patch("nautobot.extras.views.get_worker_count")
    def test_run_later_missing_name(self, patched):
        self.add_permissions("extras.run_job")

        data = {
            "_schedule_type": "future",
        }

        patched.return_value = 1
        response = self.client.post(reverse("extras:job", kwargs={"class_path": "local/test_pass/TestPass"}), data)

        self.assertHttpStatus(response, 200)
        errors = extract_form_failures(response.content.decode(response.charset))
        self.assertEqual(errors, ["_schedule_name: Please provide a name for the job schedule."])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], JOBS_ROOT=DUMMY_JOBS)
    @mock.patch("nautobot.extras.views.get_worker_count")
    def test_run_later_missing_date(self, patched):
        self.add_permissions("extras.run_job")

        data = {
            "_schedule_type": "future",
            "_schedule_name": "test",
        }

        patched.return_value = 1
        response = self.client.post(reverse("extras:job", kwargs={"class_path": "local/test_pass/TestPass"}), data)

        self.assertHttpStatus(response, 200)
        errors = extract_form_failures(response.content.decode(response.charset))
        self.assertEqual(
            errors,
            [
                "_schedule_start_time: Please enter a valid date and time greater than or equal to the current date and time."
            ],
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], JOBS_ROOT=DUMMY_JOBS)
    @mock.patch("nautobot.extras.views.get_worker_count")
    def test_run_later_date_passed(self, patched):
        self.add_permissions("extras.run_job")

        data = {
            "_schedule_type": "future",
            "_schedule_name": "test",
            "_schedule_start_time": str(datetime.now() - timedelta(minutes=1)),
        }

        patched.return_value = 1
        response = self.client.post(reverse("extras:job", kwargs={"class_path": "local/test_pass/TestPass"}), data)

        self.assertHttpStatus(response, 200)
        errors = extract_form_failures(response.content.decode(response.charset))
        self.assertEqual(
            errors,
            [
                "_schedule_start_time: Please enter a valid date and time greater than or equal to the current date and time."
            ],
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], JOBS_ROOT=DUMMY_JOBS)
    @mock.patch("nautobot.extras.views.get_worker_count")
    def test_run_later(self, patched):
        self.add_permissions("extras.run_job")

        start_time = timezone.now() + timedelta(minutes=1)
        data = {
            "_schedule_type": "future",
            "_schedule_name": "test",
            "_schedule_start_time": str(start_time),
        }

        patched.return_value = 1
        response = self.client.post(reverse("extras:job", kwargs={"class_path": "local/test_pass/TestPass"}), data)

        self.assertRedirects(response, reverse("extras:scheduledjob_list"))

        scheduled = ScheduledJob.objects.last()

        self.assertEqual(scheduled.name, "test")
        self.assertEqual(scheduled.start_time, start_time)
