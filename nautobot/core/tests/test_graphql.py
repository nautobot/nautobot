import types

from django.test import TestCase
from django.test import override_settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group, User
from django.urls import reverse
from graphene_django import DjangoObjectType
from rest_framework import status
from rest_framework.test import APIClient

from nautobot.utilities.testing import APITestCase
from nautobot.users.models import ObjectPermission, Token
from nautobot.dcim.models import (
    Device,
    Site,
    Region,
    Rack,
    Manufacturer,
    DeviceType,
    DeviceRole,
)
from nautobot.dcim.graphql.types import DeviceType as DeviceTypeGraphQL
from nautobot.dcim.filters import DeviceFilterSet, SiteFilterSet
from nautobot.ipam.models import VLAN
from nautobot.extras.models import (
    ChangeLoggedModel,
    CustomField,
    ConfigContext,
    Relationship,
)
from nautobot.core.graphql.utils import str_to_var_name
from nautobot.core.graphql.schema import (
    extend_schema_type,
    extend_schema_type_custom_field,
    extend_schema_type_tags,
    extend_schema_type_config_context,
    extend_schema_type_relationships,
)
from nautobot.core.graphql.generators import (
    generate_list_search_parameters,
    generate_schema_type,
)
from nautobot.extras.choices import CustomFieldTypeChoices


class GraphQLUtilsTestCase(TestCase):
    def test_str_to_var_name(self):

        self.assertEqual(str_to_var_name("IP Addresses"), "ip_addresses")
        self.assertEqual(str_to_var_name("My New VAR"), "my_new_var")
        self.assertEqual(str_to_var_name("My-VAR"), "my_var")


class GraphQLGenerateSchemaTypeTestCase(TestCase):
    def test_model_w_filterset(self):

        schema = generate_schema_type(app_name="dcim", model=Device)
        self.assertEqual(schema.__bases__[0], DjangoObjectType)
        self.assertEqual(schema._meta.model, Device)
        self.assertEqual(schema._meta.filterset_class, DeviceFilterSet)

    def test_model_wo_filterset(self):

        schema = generate_schema_type(app_name="wrong_app", model=ChangeLoggedModel)
        self.assertEqual(schema.__bases__[0], DjangoObjectType)
        self.assertEqual(schema._meta.model, ChangeLoggedModel)
        self.assertIsNone(schema._meta.filterset_class)


class GraphQLExtendSchemaType(TestCase):
    def setUp(self):

        self.datas = (
            {"field_name": "my_text", "field_type": CustomFieldTypeChoices.TYPE_TEXT},
            {
                "field_name": "my new field",
                "field_type": CustomFieldTypeChoices.TYPE_TEXT,
            },
            {
                "field_name": "my_int1",
                "field_type": CustomFieldTypeChoices.TYPE_INTEGER,
            },
            {
                "field_name": "my_int2",
                "field_type": CustomFieldTypeChoices.TYPE_INTEGER,
            },
            {
                "field_name": "my_bool_t",
                "field_type": CustomFieldTypeChoices.TYPE_BOOLEAN,
            },
            {
                "field_name": "my_bool_f",
                "field_type": CustomFieldTypeChoices.TYPE_BOOLEAN,
            },
            {"field_name": "my_date", "field_type": CustomFieldTypeChoices.TYPE_DATE},
            {"field_name": "my_url", "field_type": CustomFieldTypeChoices.TYPE_URL},
        )

        obj_type = ContentType.objects.get_for_model(Site)

        # Create custom fields for Site objects
        for data in self.datas:
            cf = CustomField.objects.create(type=data["field_type"], name=data["field_name"], required=False)
            cf.content_types.set([obj_type])

        self.schema = generate_schema_type(app_name="dcim", model=Site)

    @override_settings(GRAPHQL_CUSTOM_FIELD_PREFIX="pr")
    def test_extend_custom_field_w_prefix(self):

        schema = extend_schema_type_custom_field(self.schema, Site)

        for data in self.datas:
            field_name = f"pr_{str_to_var_name(data['field_name'])}"
            self.assertIn(field_name, schema._meta.fields.keys())

    @override_settings(GRAPHQL_CUSTOM_FIELD_PREFIX="")
    def test_extend_custom_field_wo_prefix(self):

        schema = extend_schema_type_custom_field(self.schema, Site)

        for data in self.datas:
            field_name = str_to_var_name(data["field_name"])
            self.assertIn(field_name, schema._meta.fields.keys())

    @override_settings(GRAPHQL_CUSTOM_FIELD_PREFIX=None)
    def test_extend_custom_field_prefix_none(self):

        schema = extend_schema_type_custom_field(self.schema, Site)

        for data in self.datas:
            field_name = str_to_var_name(data["field_name"])
            self.assertIn(field_name, schema._meta.fields.keys())

    def test_extend_tags_enabled(self):

        schema = extend_schema_type_tags(self.schema, Site)

        self.assertTrue(hasattr(schema, "resolve_tags"))
        self.assertIsInstance(getattr(schema, "resolve_tags"), types.FunctionType)

    def test_extend_custom_context(self):

        schema = extend_schema_type_config_context(DeviceTypeGraphQL, Device)
        self.assertIn("config_context", schema._meta.fields.keys())

    def test_extend_schema_device(self):

        schema = extend_schema_type(DeviceTypeGraphQL)
        self.assertIn("config_context", schema._meta.fields.keys())
        self.assertTrue(hasattr(schema, "resolve_tags"))
        self.assertIsInstance(getattr(schema, "resolve_tags"), types.FunctionType)

    def test_extend_schema_site(self):

        schema = extend_schema_type(self.schema)
        self.assertNotIn("config_context", schema._meta.fields.keys())
        self.assertTrue(hasattr(schema, "resolve_tags"))
        self.assertIsInstance(getattr(schema, "resolve_tags"), types.FunctionType)


class GraphQLExtendSchemaRelationship(TestCase):
    def setUp(self):

        site_ct = ContentType.objects.get_for_model(Site)
        rack_ct = ContentType.objects.get_for_model(Rack)
        vlan_ct = ContentType.objects.get_for_model(VLAN)

        self.m2m_1 = Relationship.objects.create(
            name="Vlan to Rack",
            slug="vlan-rack",
            source_type=rack_ct,
            source_label="My Vlans",
            destination_type=vlan_ct,
            destination_label="My Racks",
            type="many-to-many",
        )

        self.m2m_2 = Relationship.objects.create(
            name="Another Vlan to Rack",
            slug="vlan-rack-2",
            source_type=rack_ct,
            destination_type=vlan_ct,
            type="many-to-many",
        )

        self.o2m_1 = Relationship.objects.create(
            name="generic site to vlan",
            slug="site-vlan",
            source_type=site_ct,
            destination_type=vlan_ct,
            type="one-to-many",
        )

        self.o2o_1 = Relationship.objects.create(
            name="Primary Rack per Site",
            slug="primary-rack-site",
            source_type=rack_ct,
            source_hidden=True,
            destination_type=site_ct,
            destination_label="Primary Rack",
            type="one-to-one",
        )

        self.sites = [
            Site.objects.create(name="Site A", slug="site-a"),
            Site.objects.create(name="Site B", slug="site-b"),
            Site.objects.create(name="Site C", slug="site-c"),
        ]

        self.racks = [
            Rack.objects.create(name="Rack A", site=self.sites[0]),
            Rack.objects.create(name="Rack B", site=self.sites[1]),
            Rack.objects.create(name="Rack C", site=self.sites[2]),
        ]

        self.vlans = [
            VLAN.objects.create(name="VLAN A", vid=100, site=self.sites[0]),
            VLAN.objects.create(name="VLAN B", vid=100, site=self.sites[1]),
            VLAN.objects.create(name="VLAN C", vid=100, site=self.sites[2]),
        ]

        self.schema = generate_schema_type(app_name="dcim", model=Site)

    @override_settings(GRAPHQL_CUSTOM_RELATIONSHIP_PREFIX="pr")
    def test_extend_relationship_w_prefix(self):

        schema = extend_schema_type_relationships(self.schema, Site)

        datas = [
            {"field_slug": "primary-rack-site"},
            {"field_slug": "site-vlan"},
        ]

        for data in datas:
            field_name = f"rel_{str_to_var_name(data['field_slug'])}"
            self.assertIn(field_name, schema._meta.fields.keys())


class GraphQLSearchParameters(TestCase):
    def setUp(self):

        self.schema = generate_schema_type(app_name="dcim", model=Site)

    def test_search_parameters(self):

        fields = SiteFilterSet.get_filters().keys()
        params = generate_list_search_parameters(self.schema)
        exclude_filters = ["type"]

        for field in fields:
            if field not in exclude_filters:
                self.assertIn(field, params.keys())
            else:
                self.assertNotIn(field, params.keys())


class GraphQLAPIPermissionTest(TestCase):
    def setUp(self):
        """Initialize the Database with some datas and multiple users associated with different permissions."""
        self.groups = (
            Group.objects.create(name="Group 1"),
            Group.objects.create(name="Group 2"),
        )

        self.users = (
            User.objects.create(username="User 1", is_active=True),
            User.objects.create(username="User 2", is_active=True),
            User.objects.create(username="Super User", is_active=True, is_superuser=True),
            User.objects.create(username="Nobody", is_active=True),
        )

        self.tokens = (
            Token.objects.create(user=self.users[0], key="0123456789abcdef0123456789abcdef01234567"),
            Token.objects.create(user=self.users[1], key="abcd456789abcdef0123456789abcdef01234567"),
            Token.objects.create(user=self.users[2], key="efgh456789abcdef0123456789abcdef01234567"),
            Token.objects.create(user=self.users[3], key="ijkl456789abcdef0123456789abcdef01234567"),
        )

        self.clients = [APIClient(), APIClient(), APIClient(), APIClient()]
        self.clients[0].credentials(HTTP_AUTHORIZATION=f"Token {self.tokens[0].key}")
        self.clients[1].credentials(HTTP_AUTHORIZATION=f"Token {self.tokens[1].key}")
        self.clients[2].credentials(HTTP_AUTHORIZATION=f"Token {self.tokens[2].key}")
        self.clients[3].credentials(HTTP_AUTHORIZATION=f"Token {self.tokens[3].key}")

        self.regions = (
            Region.objects.create(name="Region 1", slug="region1"),
            Region.objects.create(name="Region 2", slug="region2"),
        )

        self.sites = (
            Site.objects.create(name="Site 1", slug="test1", region=self.regions[0]),
            Site.objects.create(name="Site 2", slug="test2", region=self.regions[1]),
        )

        site_object_type = ContentType.objects.get(app_label="dcim", model="site")
        rack_object_type = ContentType.objects.get(app_label="dcim", model="rack")

        # Apply permissions only to User 1 & 2
        for i in range(2):
            # Rack permission
            rack_obj_permission = ObjectPermission.objects.create(
                name=f"Permission Rack {i+1}",
                actions=["view", "add", "change", "delete"],
                constraints={"site__slug": f"test{i+1}"},
            )
            rack_obj_permission.object_types.add(rack_object_type)
            rack_obj_permission.groups.add(self.groups[i])
            rack_obj_permission.users.add(self.users[i])

            site_obj_permission = ObjectPermission.objects.create(
                name=f"Permission Site {i+1}",
                actions=["view", "add", "change", "delete"],
                constraints={"region__slug": f"region{i+1}"},
            )
            site_obj_permission.object_types.add(site_object_type)
            site_obj_permission.groups.add(self.groups[i])
            site_obj_permission.users.add(self.users[i])

        self.rack_grp1 = (
            Rack.objects.create(name="Rack 1-1", site=self.sites[0]),
            Rack.objects.create(name="Rack 1-2", site=self.sites[0]),
        )
        self.rack_grp2 = (
            Rack.objects.create(name="Rack 2-1", site=self.sites[1]),
            Rack.objects.create(name="Rack 2-2", site=self.sites[1]),
        )

        self.api_url = reverse("graphql-api")

        self.get_racks_query = """
        query {
            racks {
                name
            }
        }
        """

        self.get_racks_params_query = """
        query {
            racks(site: "test1") {
                name
            }
        }
        """

        self.get_racks_var_query = """
        query ($site: String!) {
            racks(site: $site) {
                name
            }
        }
        """

        self.get_sites_racks_query = """
        query {
            sites {
                name
                racks {
                    name
                }
            }
        }
        """

    def test_graphql_api_token_with_perm(self):
        """Validate a users can query basedo n their permissions."""
        # First user
        response = self.clients[0].post(self.api_url, {"query": self.get_racks_query}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["racks"], list)
        names = [item["name"] for item in response.data["data"]["racks"]]
        self.assertEqual(names, ["Rack 1-1", "Rack 1-2"])

        # Second user
        response = self.clients[1].post(self.api_url, {"query": self.get_racks_query}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["racks"], list)
        names = [item["name"] for item in response.data["data"]["racks"]]
        self.assertEqual(names, ["Rack 2-1", "Rack 2-2"])

    def test_graphql_api_token_super_user(self):
        """Validate a superuser can query everything."""
        response = self.clients[2].post(self.api_url, {"query": self.get_racks_query}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["racks"], list)
        names = [item["name"] for item in response.data["data"]["racks"]]
        self.assertEqual(names, ["Rack 1-1", "Rack 1-2", "Rack 2-1", "Rack 2-2"])

    def test_graphql_api_token_no_group(self):
        """Validate User with no permission users are not able to query anything by default."""
        response = self.clients[3].post(self.api_url, {"query": self.get_racks_query}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["racks"], list)
        names = [item["name"] for item in response.data["data"]["racks"]]
        self.assertEqual(names, [])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_graphql_api_token_no_group_exempt(self):
        """Validate User with no permission users are able to query based on the exempt permissions."""
        response = self.clients[3].post(self.api_url, {"query": self.get_racks_query}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["racks"], list)
        names = [item["name"] for item in response.data["data"]["racks"]]
        self.assertEqual(names, ["Rack 1-1", "Rack 1-2", "Rack 2-1", "Rack 2-2"])

    def test_graphql_api_no_token(self):
        """Validate unauthenticated users are not able to query anything by default."""
        client = APIClient()
        response = client.post(self.api_url, {"query": self.get_racks_query}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["racks"], list)
        names = [item["name"] for item in response.data["data"]["racks"]]
        self.assertEqual(names, [])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_graphql_api_no_token_exempt(self):
        """Validate unauthenticated users are able to query based on the exempt permissions."""
        client = APIClient()
        response = client.post(self.api_url, {"query": self.get_racks_query}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["racks"], list)
        names = [item["name"] for item in response.data["data"]["racks"]]
        self.assertEqual(names, ["Rack 1-1", "Rack 1-2", "Rack 2-1", "Rack 2-2"])

    def test_graphql_api_wrong_token(self):
        """Validate a wrong token return 403."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token zzzzzzzzzzabcdef0123456789abcdef01234567")
        response = client.post(self.api_url, {"query": self.get_racks_query}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_graphql_query_params(self):
        """Validate query parameters are available for a model."""
        response = self.clients[2].post(self.api_url, {"query": self.get_racks_params_query}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["racks"], list)
        names = [item["name"] for item in response.data["data"]["racks"]]
        self.assertEqual(names, ["Rack 1-1", "Rack 1-2"])

    def test_graphql_query_variables(self):
        """Validate graphql variables are working as expected."""
        payload = {"query": self.get_racks_var_query, "variables": {"site": "test1"}}
        response = self.clients[2].post(self.api_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["racks"], list)
        names = [item["name"] for item in response.data["data"]["racks"]]
        self.assertEqual(names, ["Rack 1-1", "Rack 1-2"])

        payload = {"query": self.get_racks_var_query, "variables": {"site": "test2"}}
        response = self.clients[2].post(self.api_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["racks"], list)
        names = [item["name"] for item in response.data["data"]["racks"]]
        self.assertEqual(names, ["Rack 2-1", "Rack 2-2"])

    def test_graphql_query_multi_level(self):
        """Validate request with multiple levels return the proper information, following the permissions."""
        response = self.clients[0].post(self.api_url, {"query": self.get_sites_racks_query}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["sites"], list)
        site_names = [item["name"] for item in response.data["data"]["sites"]]
        self.assertEqual(site_names, ["Site 1"])
        rack_names = [item["name"] for item in response.data["data"]["sites"][0]["racks"]]
        self.assertEqual(rack_names, ["Rack 1-1", "Rack 1-2"])

    def test_graphql_query_format(self):
        """Validate application/graphql query is working properly."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {self.tokens[2].key}")
        response = client.post(
            self.api_url,
            data=self.get_sites_racks_query,
            content_type="application/graphql",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["sites"], list)
        site_names = [item["name"] for item in response.data["data"]["sites"]]
        self.assertEqual(site_names, ["Site 1", "Site 2"])


class GraphQLQuery(APITestCase):
    def setUp(self):
        """Initialize the Database with some datas."""
        super().setUp()

        self.api_url = reverse("graphql-api")

        # Populate Data
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        self.devicetype = DeviceType.objects.create(
            manufacturer=manufacturer, model="Device Type 1", slug="device-type-1"
        )
        self.devicerole = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")
        self.region = Region.objects.create(name="Region")
        self.site = Site.objects.create(name="Site-1", slug="site-1", region=self.region)

        self.device = Device.objects.create(
            name="Device 1",
            device_type=self.devicetype,
            device_role=self.devicerole,
            site=self.site,
        )

        context1 = ConfigContext.objects.create(name="context 1", weight=101, data={"a": 123, "b": 456, "c": 777})
        context1.regions.add(self.region)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_config_context(self):

        get_device_config_context = """
        query {
            devices {
                name
                config_context
            }
        }
        """

        expected_data = {"a": 123, "b": 456, "c": 777}

        response = self.client.post(
            self.api_url,
            data=get_device_config_context,
            content_type="application/graphql",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["devices"], list)
        device_names = [item["name"] for item in response.data["data"]["devices"]]
        self.assertEqual(device_names, ["Device 1"])

        config_context = [item["config_context"] for item in response.data["data"]["devices"]]
        self.assertIsInstance(config_context[0], dict)
        self.assertDictEqual(config_context[0], expected_data)
