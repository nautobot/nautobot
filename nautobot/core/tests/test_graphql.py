import types
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse
from graphql import GraphQLError
from graphene_django import DjangoObjectType
from graphene_django.settings import graphene_settings
from graphql.error.located_error import GraphQLLocatedError
from graphql import get_default_backend
from rest_framework import status
from rest_framework.test import APIClient

from nautobot.circuits.models import Provider
from nautobot.core.graphql.generators import (
    generate_list_search_parameters,
    generate_schema_type,
)
from nautobot.core.graphql import execute_query, execute_saved_query
from nautobot.core.graphql.utils import str_to_var_name
from nautobot.core.graphql.schema import (
    extend_schema_type,
    extend_schema_type_custom_field,
    extend_schema_type_tags,
    extend_schema_type_config_context,
    extend_schema_type_relationships,
    extend_schema_type_null_field_choice,
)
from nautobot.dcim.choices import InterfaceTypeChoices, InterfaceModeChoices
from nautobot.dcim.filters import DeviceFilterSet, SiteFilterSet
from nautobot.dcim.graphql.types import DeviceType as DeviceTypeGraphQL
from nautobot.dcim.models import Cable, Device, DeviceRole, DeviceType, Interface, Manufacturer, Rack, Region, Site
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.utilities.testing.utils import create_test_user

from nautobot.extras.models import (
    ChangeLoggedModel,
    CustomField,
    ConfigContext,
    GraphQLQuery,
    Relationship,
    Status,
    Webhook,
)
from nautobot.ipam.models import IPAddress, VLAN
from nautobot.users.models import ObjectPermission, Token
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine, VMInterface

# Use the proper swappable User model
User = get_user_model()


class GraphQLTestCase(TestCase):
    @classmethod
    def setUp(self):
        self.user = create_test_user("graphql_testuser")
        GraphQLQuery.objects.create(name="GQL 1", slug="gql-1", query="{ query: sites {name} }")
        GraphQLQuery.objects.create(
            name="GQL 2", slug="gql-2", query="query ($name: [String!]) { sites(name:$name) {name} }"
        )
        self.region = Region.objects.create(name="Region")
        self.sites = (
            Site.objects.create(name="Site-1", slug="site-1", region=self.region),
            Site.objects.create(name="Site-2", slug="site-2", region=self.region),
            Site.objects.create(name="Site-3", slug="site-3", region=self.region),
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_execute_query(self):
        query = "{ query: sites {name} }"
        resp = execute_query(query, user=self.user).to_dict()
        self.assertFalse(resp["data"].get("error"))
        self.assertEquals(len(resp["data"]["query"]), 3)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_execute_query_with_variable(self):
        query = "query ($name: [String!]) { sites(name:$name) {name} }"
        resp = execute_query(query, user=self.user, variables={"name": "Site-1"}).to_dict()
        self.assertFalse(resp.get("error"))
        self.assertEquals(len(resp["data"]["sites"]), 1)

    def test_execute_query_with_error(self):
        query = "THIS TEST WILL ERROR"
        with self.assertRaises(GraphQLError):
            execute_query(query, user=self.user).to_dict()

    def test_execute_saved_query(self):
        resp = execute_saved_query("gql-1", user=self.user).to_dict()
        self.assertFalse(resp["data"].get("error"))

    def test_execute_saved_query_with_variable(self):
        resp = execute_saved_query("gql-2", user=self.user, variables={"name": "site-1"}).to_dict()
        self.assertFalse(resp["data"].get("error"))


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

    def test_extend_schema_null_field_choices(self):

        schema = extend_schema_type_null_field_choice(self.schema, Interface)

        self.assertTrue(hasattr(schema, "resolve_mode"))
        self.assertIsInstance(getattr(schema, "resolve_mode"), types.FunctionType)


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
        query ($site: [String]) {
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


class GraphQLQueryTest(TestCase):
    def setUp(self):
        """Initialize the Database with some datas."""
        super().setUp()
        self.user = User.objects.create(username="Super User", is_active=True, is_superuser=True)

        # Initialize fake request that will be required to execute GraphQL query
        self.request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        self.request.id = uuid.uuid4()
        self.request.user = self.user

        self.backend = get_default_backend()
        self.schema = graphene_settings.SCHEMA

        # Populate Data
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        self.devicetype = DeviceType.objects.create(
            manufacturer=manufacturer, model="Device Type 1", slug="device-type-1"
        )
        self.devicerole1 = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")
        self.devicerole2 = DeviceRole.objects.create(name="Device Role 2", slug="device-role-2")
        self.status1 = Status.objects.create(name="status1", slug="status1")
        self.status2 = Status.objects.create(name="status2", slug="status2")
        self.region1 = Region.objects.create(name="Region1", slug="region1")
        self.region2 = Region.objects.create(name="Region2", slug="region2")
        self.site1 = Site.objects.create(
            name="Site-1", slug="site-1", asn=65000, status=self.status1, region=self.region1
        )
        self.site2 = Site.objects.create(
            name="Site-2", slug="site-2", asn=65099, status=self.status2, region=self.region2
        )
        self.rack1 = Rack.objects.create(name="Rack 1", site=self.site1)
        self.rack2 = Rack.objects.create(name="Rack 2", site=self.site2)
        self.tenant1 = Tenant.objects.create(name="Tenant 1", slug="tenant-1")
        self.tenant2 = Tenant.objects.create(name="Tenant 2", slug="tenant-2")

        self.vlan1 = VLAN.objects.create(name="VLAN 1", vid=100, site=self.site1)
        self.vlan2 = VLAN.objects.create(name="VLAN 2", vid=200, site=self.site2)

        self.device1 = Device.objects.create(
            name="Device 1",
            device_type=self.devicetype,
            device_role=self.devicerole1,
            site=self.site1,
            status=self.status1,
            rack=self.rack1,
            tenant=self.tenant1,
            face="front",
            comments="First Device",
        )

        self.interface11 = Interface.objects.create(
            name="Int1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            device=self.device1,
            mac_address="00:11:11:11:11:11",
            mode=InterfaceModeChoices.MODE_ACCESS,
            untagged_vlan=self.vlan1,
        )
        self.interface12 = Interface.objects.create(
            name="Int2",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            device=self.device1,
        )
        self.ipaddr1 = IPAddress.objects.create(
            address="10.0.1.1/24", status=self.status1, assigned_object=self.interface11
        )

        self.device2 = Device.objects.create(
            name="Device 2",
            device_type=self.devicetype,
            device_role=self.devicerole2,
            site=self.site1,
            status=self.status2,
            rack=self.rack2,
            tenant=self.tenant2,
            face="rear",
        )

        self.interface21 = Interface.objects.create(
            name="Int1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            device=self.device2,
            untagged_vlan=self.vlan2,
            mode=InterfaceModeChoices.MODE_ACCESS,
        )
        self.interface22 = Interface.objects.create(
            name="Int2", type=InterfaceTypeChoices.TYPE_1GE_FIXED, device=self.device2, mac_address="00:12:12:12:12:12"
        )
        self.ipaddr2 = IPAddress.objects.create(
            address="10.0.2.1/30", status=self.status2, assigned_object=self.interface12
        )

        self.device3 = Device.objects.create(
            name="Device 3",
            device_type=self.devicetype,
            device_role=self.devicerole1,
            site=self.site2,
            status=self.status1,
        )

        self.interface31 = Interface.objects.create(
            name="Int1", type=InterfaceTypeChoices.TYPE_VIRTUAL, device=self.device3
        )
        self.interface31 = Interface.objects.create(
            name="Mgmt1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            device=self.device3,
            mgmt_only=True,
            enabled=False,
        )

        self.cable1 = Cable.objects.create(
            termination_a=self.interface11,
            termination_b=self.interface12,
            status=self.status1,
        )
        self.cable2 = Cable.objects.create(
            termination_a=self.interface31,
            termination_b=self.interface21,
            status=self.status2,
        )

        context1 = ConfigContext.objects.create(name="context 1", weight=101, data={"a": 123, "b": 456, "c": 777})
        context1.regions.add(self.region1)

        Provider.objects.create(name="provider 1", slug="provider-1", asn=1)
        Provider.objects.create(name="provider 2", slug="provider-2", asn=4294967295)

        webhook1 = Webhook.objects.create(name="webhook 1", type_delete=True, enabled=False)
        webhook1.content_types.add(ContentType.objects.get_for_model(Device))
        webhook2 = Webhook.objects.create(name="webhook 2", type_update=True, enabled=False)
        webhook2.content_types.add(ContentType.objects.get_for_model(Interface))

        clustertype = ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1")
        cluster = Cluster.objects.create(name="Cluster 1", type=clustertype)
        self.virtualmachine = VirtualMachine.objects.create(
            name="Virtual Machine 1",
            cluster=cluster,
            status=self.status1,
        )
        self.vminterface = VMInterface.objects.create(
            virtual_machine=self.virtualmachine,
            name="eth0",
        )
        self.vmipaddr = IPAddress.objects.create(
            address="1.1.1.1/32", status=self.status1, assigned_object=self.vminterface
        )

    def execute_query(self, query, variables=None):

        document = self.backend.document_from_string(self.schema, query)
        if variables:
            return document.execute(context_value=self.request, variable_values=variables)
        else:
            return document.execute(context_value=self.request)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_config_context(self):

        query = """
        query {
            devices {
                name
                config_context
            }
        }
        """

        expected_data = {"a": 123, "b": 456, "c": 777}

        result = self.execute_query(query)

        self.assertIsInstance(result.data["devices"], list)
        device_names = [item["name"] for item in result.data["devices"]]
        self.assertEqual(sorted(device_names), ["Device 1", "Device 2", "Device 3"])

        config_context = [item["config_context"] for item in result.data["devices"]]
        self.assertIsInstance(config_context[0], dict)
        self.assertDictEqual(config_context[0], expected_data)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_device_role_filter(self):

        query = """
            query {
                devices(role: "device-role-1") {
                    id
                    name
                }
            }
        """
        result = self.execute_query(query)

        self.assertEqual(len(result.data["devices"]), 2)
        device_names = [item["name"] for item in result.data["devices"]]
        self.assertEqual(sorted(device_names), ["Device 1", "Device 3"])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_with_bad_filter(self):

        query = """
            query {
                devices(role: "EXPECT NO ENTRIES") {
                    id
                    name
                }
            }
        """

        response = self.execute_query(query)
        self.assertEqual(len(response.errors), 1)
        self.assertIsInstance(response.errors[0], GraphQLLocatedError)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_sites_filter(self):

        filters = (
            ('name: "Site-1"', 1),
            ('name: ["Site-1"]', 1),
            ('name: ["Site-1", "Site-2"]', 2),
            ('name__ic: "Site"', 2),
            ('name__ic: ["Site"]', 2),
            ('name__nic: "Site"', 0),
            ('name__nic: ["Site"]', 0),
            ('region: "region1"', 1),
            ('region: ["region1"]', 1),
            ('region: ["region1", "region2"]', 2),
            ("asn: 65000", 1),
            ("asn: [65099]", 1),
            ("asn: [65000, 65099]", 2),
            (f'id: "{self.site1.pk}"', 1),
            (f'id: ["{self.site1.pk}"]', 1),
            (f'id: ["{self.site1.pk}", "{self.site2.pk}"]', 2),
            ('status: "status1"', 1),
            ('status: ["status2"]', 1),
            ('status: ["status1", "status2"]', 2),
        )

        for filter, nbr_expected_results in filters:
            with self.subTest(msg=f"Checking {filter}", filter=filter, nbr_expected_results=nbr_expected_results):
                query = "query { sites(" + filter + "){ name }}"
                result = self.execute_query(query)
                self.assertIsNone(result.errors)
                self.assertEqual(len(result.data["sites"]), nbr_expected_results)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_devices_filter(self):

        filters = (
            ('name: "Device 1"', 1),
            ('name: ["Device 1"]', 1),
            ('name: ["Device 1", "Device 2"]', 2),
            ('name__ic: "Device"', 3),
            ('name__ic: ["Device"]', 3),
            ('name__nic: "Device"', 0),
            ('name__nic: ["Device"]', 0),
            (f'id: "{self.device1.pk}"', 1),
            (f'id: ["{self.device1.pk}"]', 1),
            (f'id: ["{self.device1.pk}", "{self.device2.pk}"]', 2),
            ('role: "device-role-1"', 2),
            ('role: ["device-role-1"]', 2),
            ('role: ["device-role-1", "device-role-2"]', 3),
            ('site: "site-1"', 2),
            ('site: ["site-1"]', 2),
            ('site: ["site-1", "site-2"]', 3),
            ('region: "region1"', 2),
            ('region: ["region1"]', 2),
            ('region: ["region1", "region2"]', 3),
            ('face: "front"', 1),
            ('face: "rear"', 1),
            ('status: "status1"', 2),
            ('status: ["status2"]', 1),
            ('status: ["status1", "status2"]', 3),
            ("is_full_depth: true", 3),
            ("is_full_depth: false", 0),
            ("has_primary_ip: true", 0),
            ("has_primary_ip: false", 3),
            ('mac_address: "00:11:11:11:11:11"', 1),
            ('mac_address: ["00:12:12:12:12:12"]', 1),
            ('mac_address: ["00:11:11:11:11:11", "00:12:12:12:12:12"]', 2),
            ('mac_address: "99:11:11:11:11:11"', 0),
            ('q: "first"', 1),
            ('q: "notthere"', 0),
        )

        for filter, nbr_expected_results in filters:
            with self.subTest(msg=f"Checking {filter}", filter=filter, nbr_expected_results=nbr_expected_results):
                query = "query {devices(" + filter + "){ name }}"
                result = self.execute_query(query)
                self.assertIsNone(result.errors)
                self.assertEqual(len(result.data["devices"]), nbr_expected_results)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_ip_addresses_filter(self):

        filters = (
            ('address: "10.0.1.1"', 1),
            ("family: 4", 3),
            ('status: "status1"', 2),
            ('status: ["status2"]', 1),
            ('status: ["status1", "status2"]', 3),
            ("mask_length: 24", 1),
            ("mask_length: 30", 1),
            ("mask_length: 32", 1),
            ("mask_length: 28", 0),
            ('parent: "10.0.0.0/16"', 2),
            ('parent: "10.0.2.0/24"', 1),
        )

        for filter, nbr_expected_results in filters:
            with self.subTest(msg=f"Checking {filter}", filter=filter, nbr_expected_results=nbr_expected_results):
                query = "query { ip_addresses(" + filter + "){ address }}"
                result = self.execute_query(query)
                self.assertIsNone(result.errors)
                self.assertEqual(len(result.data["ip_addresses"]), nbr_expected_results)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_ip_addresses_assigned_object(self):
        """Query IP Address assigned_object values."""

        query = """\
query {
    ip_addresses {
        address
        assigned_object {
            ... on InterfaceType {
                name
                device { name }
            }
            ... on VMInterfaceType {
                name
                virtual_machine { name }
            }
        }
        interface { name }
        vminterface { name }
    }
}"""
        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(result.data["ip_addresses"]), 3)
        for entry in result.data["ip_addresses"]:
            self.assertIn(
                entry["address"], (str(self.ipaddr1.address), str(self.ipaddr2.address), str(self.vmipaddr.address))
            )
            self.assertIn("assigned_object", entry)
            if entry["address"] == str(self.vmipaddr.address):
                self.assertEqual(entry["assigned_object"]["name"], self.vminterface.name)
                self.assertEqual(entry["vminterface"]["name"], self.vminterface.name)
                self.assertIsNone(entry["interface"])
                self.assertIn("virtual_machine", entry["assigned_object"])
                self.assertNotIn("device", entry["assigned_object"])
                self.assertEqual(entry["assigned_object"]["virtual_machine"]["name"], self.virtualmachine.name)
            else:
                self.assertIn(entry["assigned_object"]["name"], (self.interface11.name, self.interface12.name))
                self.assertIn(entry["interface"]["name"], (self.interface11.name, self.interface12.name))
                self.assertIsNone(entry["vminterface"])
                self.assertIn("device", entry["assigned_object"])
                self.assertNotIn("virtual_machine", entry["assigned_object"])
                self.assertEqual(entry["assigned_object"]["device"]["name"], self.device1.name)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_cables_filter(self):

        filters = (
            (f'device_id: "{self.device1.id}"', 1),
            ('device: "Device 3"', 1),
            ('device: ["Device 1", "Device 3"]', 2),
            (f'rack_id: "{self.rack1.id}"', 1),
            ('rack: "Rack 2"', 1),
            ('rack: ["Rack 1", "Rack 2"]', 2),
            (f'site_id: "{self.site1.id}"', 2),
            ('site: "site-2"', 1),
            ('site: ["site-1", "site-2"]', 2),
            (f'tenant_id: "{self.tenant1.id}"', 1),
            ('tenant: "tenant-2"', 1),
            ('tenant: ["tenant-1", "tenant-2"]', 2),
        )

        for filter, nbr_expected_results in filters:
            with self.subTest(msg=f"Checking {filter}", filter=filter, nbr_expected_results=nbr_expected_results):
                query = "query { cables(" + filter + "){ id }}"
                result = self.execute_query(query)
                self.assertIsNone(result.errors)
                self.assertEqual(len(result.data["cables"]), nbr_expected_results)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_interfaces_filter(self):
        """Test custom interface filter fields and boolean, not other concrete fields."""

        filters = (
            (f'device_id: "{self.device1.id}"', 2),
            ('device: "Device 3"', 2),
            ('device: ["Device 1", "Device 3"]', 4),
            ('kind: "virtual"', 5),
            ('mac_address: "00:11:11:11:11:11"', 1),
            ("vlan: 100", 1),
            (f'vlan_id: "{self.vlan1.id}"', 1),
            ("mgmt_only: true", 1),
            ("enabled: false", 1),
        )

        for filter, nbr_expected_results in filters:
            with self.subTest(msg=f"Checking {filter}", filter=filter, nbr_expected_results=nbr_expected_results):
                query = "query { interfaces(" + filter + "){ id }}"
                result = self.execute_query(query)
                self.assertIsNone(result.errors)
                self.assertEqual(len(result.data["interfaces"]), nbr_expected_results)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_interfaces_connected_endpoint(self):
        """Test querying interfaces for their connected endpoints."""

        query = """\
query {
    interfaces {
        connected_endpoint {
            ... on InterfaceType {
                name
                device { name }
            }
        }
        connected_interface {
            name
            device { name }
        }
        connected_console_server_port { id }
        connected_circuit_termination { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        for interface_entry in result.data["interfaces"]:
            if interface_entry["connected_endpoint"] is None:
                self.assertIsNone(interface_entry["connected_interface"])
            else:
                self.assertEqual(
                    interface_entry["connected_endpoint"]["name"], interface_entry["connected_interface"]["name"]
                )
                self.assertEqual(
                    interface_entry["connected_endpoint"]["device"]["name"],
                    interface_entry["connected_interface"]["device"]["name"],
                )
            # TODO: it would be nice to have connections to console server ports and circuit terminations to test!
            self.assertIsNone(interface_entry["connected_console_server_port"])
            self.assertIsNone(interface_entry["connected_circuit_termination"])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_interfaces_mode(self):
        """Test querying interfaces for their mode and make sure a string or None is returned."""

        query = """\
query {
    devices(name: "Device 1") {
        interfaces {
            name
            mode
        }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        for intf in result.data["devices"][0]["interfaces"]:
            intf_name = intf["name"]
            if intf_name == "Int1":
                self.assertEqual(intf["mode"], InterfaceModeChoices.MODE_ACCESS.upper())
            elif intf_name == "Int2":
                self.assertIsNone(intf["mode"])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_providers_filter(self):
        """Test provider filtering by ASN (issue #428)."""
        filters = (
            ("asn: [4294967295]", 1),
            ("asn: [1, 4294967295]", 2),
        )

        for filterv, nbr_expected_results in filters:
            with self.subTest(msg=f"Checking {filterv}", filterv=filterv, nbr_expected_results=nbr_expected_results):
                query = "query { providers (" + filterv + "){ id asn }}"
                result = self.execute_query(query)
                self.assertIsNone(result.errors)
                self.assertEqual(len(result.data["providers"]), nbr_expected_results)
                for provider in result.data["providers"]:
                    self.assertEqual(provider["asn"], Provider.objects.get(id=provider["id"]).asn)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_webhooks_filter(self):
        """Test webhook querying and filtering with content types."""
        filters = (
            ('content_types: ["dcim.device"]', 1),
            ('content_types: ["dcim.interface"]', 1),
            # Since content_types is a many-to-many field, this query is an AND, not an OR
            ('content_types: ["dcim.device", "dcim.interface"]', 0),
            ('content_types: ["ipam.ipaddress"]', 0),
        )

        for filterv, nbr_expected_results in filters:
            with self.subTest(msg=f"Checking {filterv}", filterv=filterv, nbr_expected_results=nbr_expected_results):
                query = "query { webhooks (" + filterv + "){ id name content_types {app_label model}}}"
                result = self.execute_query(query)
                self.assertIsNone(result.errors)
                self.assertEqual(len(result.data["webhooks"]), nbr_expected_results)
