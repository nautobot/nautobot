import random
import types
from unittest import skip
import uuid

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse
from graphql import GraphQLError
import graphene.types
from graphene_django.settings import graphene_settings
from graphene_django.registry import get_global_registry
from graphql.error.located_error import GraphQLLocatedError
from graphql import get_default_backend
from rest_framework import status

from nautobot.circuits.models import Provider, CircuitTermination
from nautobot.core.graphql import execute_query, execute_saved_query
from nautobot.core.graphql.generators import (
    generate_list_search_parameters,
    generate_schema_type,
)
from nautobot.core.graphql.schema import (
    extend_schema_type,
    extend_schema_type_custom_field,
    extend_schema_type_tags,
    extend_schema_type_config_context,
    extend_schema_type_relationships,
    extend_schema_type_null_field_choice,
)
from nautobot.core.graphql.types import OptimizedNautobotObjectType
from nautobot.core.graphql.utils import str_to_var_name
from nautobot.core.testing import NautobotTestClient, create_test_user
from nautobot.dcim.choices import InterfaceTypeChoices, InterfaceModeChoices, PortTypeChoices, ConsolePortTypeChoices
from nautobot.dcim.filters import DeviceFilterSet, LocationFilterSet
from nautobot.dcim.graphql.types import DeviceType as DeviceTypeGraphQL
from nautobot.dcim.models import (
    Cable,
    ConsolePort,
    ConsoleServerPort,
    Device,
    DeviceType,
    FrontPort,
    Interface,
    Location,
    LocationType,
    PowerFeed,
    PowerPort,
    PowerOutlet,
    PowerPanel,
    Rack,
    RearPort,
)
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.models import (
    ChangeLoggedModel,
    CustomField,
    ConfigContext,
    GraphQLQuery,
    Relationship,
    RelationshipAssociation,
    Role,
    Status,
    Webhook,
)
from nautobot.extras.registry import registry
from nautobot.ipam.factory import VLANGroupFactory
from nautobot.ipam.models import IPAddress, VLAN, Namespace, Prefix
from nautobot.users.models import ObjectPermission, Token
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.factory import ClusterTypeFactory
from nautobot.virtualization.models import Cluster, VirtualMachine, VMInterface

# Use the proper swappable User model
User = get_user_model()


class GraphQLTestCase(TestCase):
    def setUp(self):
        self.user = create_test_user("graphql_testuser")
        GraphQLQuery.objects.create(name="GQL 1", query="{ query: locations {name} }")
        GraphQLQuery.objects.create(name="GQL 2", query="query ($name: [String!]) { locations(name:$name) {name} }")
        self.location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        self.locations = (
            Location.objects.create(name="Location-1", location_type=self.location_type, status=location_status),
            Location.objects.create(name="Location-2", location_type=self.location_type, status=location_status),
            Location.objects.create(name="Location-3", location_type=self.location_type, status=location_status),
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_execute_query(self):
        query = "{ query: locations {name} }"
        resp = execute_query(query, user=self.user).to_dict()
        self.assertFalse(resp["data"].get("error"))
        self.assertEqual(len(resp["data"]["query"]), Location.objects.all().count())

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_execute_query_with_variable(self):
        query = "query ($name: [String!]) { locations(name:$name) {name} }"
        resp = execute_query(query, user=self.user, variables={"name": "Location-1"}).to_dict()
        self.assertFalse(resp.get("error"))
        self.assertEqual(len(resp["data"]["locations"]), 1)

    def test_execute_query_with_error(self):
        query = "THIS TEST WILL ERROR"
        with self.assertRaises(GraphQLError):
            execute_query(query, user=self.user).to_dict()

    def test_execute_saved_query(self):
        resp = execute_saved_query("GQL 1", user=self.user).to_dict()
        self.assertFalse(resp["data"].get("error"))

    def test_execute_saved_query_with_variable(self):
        resp = execute_saved_query("GQL 2", user=self.user, variables={"name": "location-1"}).to_dict()
        self.assertFalse(resp["data"].get("error"))

    def test_graphql_types_registry(self):
        """Ensure models with graphql feature are registered in the graphene_django registry."""
        graphene_django_registry = get_global_registry()
        for app_label, models in registry["model_features"]["graphql"].items():
            for model_name in models:
                model = apps.get_model(app_label=app_label, model_name=model_name)
                self.assertIsNotNone(graphene_django_registry.get_type_for_model(model))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_graphql_url_field(self):
        """Test the url field for all graphql types."""
        schema = graphene_settings.SCHEMA.introspect()
        graphql_fields = schema["__schema"]["types"][0]["fields"]
        for graphql_field in graphql_fields:
            if graphql_field["type"]["kind"] == "LIST" or graphql_field["name"] == "content_type":
                continue
            with self.subTest(f"Testing graphql url field for {graphql_field['name']}"):
                graphene_object_type_definition = graphene_settings.SCHEMA.get_type(graphql_field["type"]["name"])

                # simple check for url field in type definition
                self.assertIn(
                    "url", graphene_object_type_definition.fields, f"Missing url field for {graphql_field['name']}"
                )

                graphene_object_type_instance = graphene_object_type_definition.graphene_type()
                model = graphene_object_type_instance._meta.model

                # if an instance of this model exists, run a test query to retrieve the url
                if model.objects.exists():
                    obj = model.objects.first()
                    query = f'{{ query: {graphql_field["name"]}(id:"{obj.pk}") {{ url }} }}'
                    request = RequestFactory(SERVER_NAME="nautobot.example.com").post("/graphql/")
                    request.user = self.user
                    resp = execute_query(query, request=request).to_dict()
                    self.assertIsNotNone(
                        resp["data"]["query"]["url"], f"No url returned in graphql for {graphql_field['name']}"
                    )
                    self.assertTrue(
                        resp["data"]["query"]["url"].endswith(f"/{obj.pk}/"),
                        f"Mismatched url returned in graphql for {graphql_field['name']}",
                    )


class GraphQLUtilsTestCase(TestCase):
    def test_str_to_var_name(self):
        self.assertEqual(str_to_var_name("IP Addresses"), "ip_addresses")
        self.assertEqual(str_to_var_name("My New VAR"), "my_new_var")
        self.assertEqual(str_to_var_name("My-VAR"), "my_var")


class GraphQLGenerateSchemaTypeTestCase(TestCase):
    def test_model_w_filterset(self):
        schema = generate_schema_type(app_name="dcim", model=Device)
        self.assertEqual(schema.__bases__[0], OptimizedNautobotObjectType)
        self.assertEqual(schema._meta.model, Device)
        self.assertEqual(schema._meta.filterset_class, DeviceFilterSet)

    def test_model_wo_filterset(self):
        schema = generate_schema_type(app_name="wrong_app", model=ChangeLoggedModel)
        self.assertEqual(schema.__bases__[0], OptimizedNautobotObjectType)
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

        obj_type = ContentType.objects.get_for_model(Location)

        # Create custom fields for Location objects
        for data in self.datas:
            cf = CustomField.objects.create(type=data["field_type"], label=data["field_name"], required=False)
            cf.content_types.set([obj_type])

        self.schema = generate_schema_type(app_name="dcim", model=Location)

    @override_settings(GRAPHQL_CUSTOM_FIELD_PREFIX="pr")
    def test_extend_custom_field_w_prefix(self):
        schema = extend_schema_type_custom_field(self.schema, Location)

        for data in self.datas:
            field_name = f"pr_{str_to_var_name(data['field_name'])}"
            self.assertIn(field_name, schema._meta.fields.keys())

    @override_settings(GRAPHQL_CUSTOM_FIELD_PREFIX="")
    def test_extend_custom_field_wo_prefix(self):
        schema = extend_schema_type_custom_field(self.schema, Location)

        for data in self.datas:
            field_name = str_to_var_name(data["field_name"])
            self.assertIn(field_name, schema._meta.fields.keys())

    @override_settings(GRAPHQL_CUSTOM_FIELD_PREFIX=None)
    def test_extend_custom_field_prefix_none(self):
        schema = extend_schema_type_custom_field(self.schema, Location)

        for data in self.datas:
            field_name = str_to_var_name(data["field_name"])
            self.assertIn(field_name, schema._meta.fields.keys())

    def test_extend_tags_enabled(self):
        schema = extend_schema_type_tags(self.schema, Location)

        self.assertTrue(hasattr(schema, "resolve_tags"))
        self.assertIsInstance(getattr(schema, "resolve_tags"), types.FunctionType)

    def test_extend_config_context(self):
        schema = extend_schema_type_config_context(DeviceTypeGraphQL, Device)
        self.assertIn("config_context", schema._meta.fields.keys())

    def test_extend_schema_device(self):
        # The below *will* log an error as DeviceTypeGraphQL has already been extended automatically...?
        schema = extend_schema_type(DeviceTypeGraphQL)
        self.assertIn("config_context", schema._meta.fields.keys())
        self.assertTrue(hasattr(schema, "resolve_tags"))
        self.assertIsInstance(getattr(schema, "resolve_tags"), types.FunctionType)

    def test_extend_schema_location(self):
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
        location_ct = ContentType.objects.get_for_model(Location)
        rack_ct = ContentType.objects.get_for_model(Rack)
        vlan_ct = ContentType.objects.get_for_model(VLAN)

        self.m2m_1 = Relationship(
            label="VLAN to Rack",
            key="vlan_rack",
            source_type=rack_ct,
            source_label="My VLANs",
            destination_type=vlan_ct,
            destination_label="My Racks",
            type="many-to-many",
        )
        self.m2m_1.validated_save()

        self.m2m_2 = Relationship(
            label="Another VLAN to Rack",
            key="vlan_rack_2",
            source_type=rack_ct,
            destination_type=vlan_ct,
            type="many-to-many",
        )
        self.m2m_2.validated_save()

        self.o2m_1 = Relationship(
            label="generic Location to VLAN",
            key="location_vlan",
            source_type=location_ct,
            destination_type=vlan_ct,
            type="one-to-many",
        )
        self.o2m_1.validated_save()

        self.o2o_1 = Relationship(
            label="Primary Rack per Location",
            key="primary_rack_location",
            source_type=rack_ct,
            source_hidden=True,
            destination_type=location_ct,
            destination_label="Primary Rack",
            type="one-to-one",
        )
        self.o2o_1.validated_save()

        self.o2os_1 = Relationship(
            label="Redundant Location",
            key="redundant_location",
            source_type=location_ct,
            destination_type=location_ct,
            type="symmetric-one-to-one",
        )
        self.o2os_1.validated_save()

        self.o2m_same_type_1 = Relationship(
            label="Some sort of location hierarchy?",
            key="location_hierarchy",
            source_type=location_ct,
            destination_type=location_ct,
            type="one-to-many",
        )
        self.o2m_same_type_1.validated_save()

        self.location_schema = generate_schema_type(app_name="dcim", model=Location)
        self.vlan_schema = generate_schema_type(app_name="ipam", model=VLAN)

    def test_extend_relationship_default_prefix(self):
        """Verify that relationships are correctly added to the schema."""
        schema = extend_schema_type_relationships(self.vlan_schema, VLAN)

        # Relationships on VLAN
        for rel, peer_side in [
            (self.m2m_1, "source"),
            (self.m2m_2, "source"),
            (self.o2m_1, "source"),
        ]:
            field_name = f"rel_{str_to_var_name(rel.key)}"
            self.assertIn(field_name, schema._meta.fields.keys())
            self.assertIsInstance(schema._meta.fields[field_name], graphene.types.field.Field)
            if rel.has_many(peer_side):
                self.assertIsInstance(schema._meta.fields[field_name].type, graphene.types.structures.List)
            else:
                self.assertNotIsInstance(schema._meta.fields[field_name].type, graphene.types.structures.List)

        # Relationships not on VLAN
        for rel in [self.o2o_1, self.o2os_1]:
            field_name = f"rel_{str_to_var_name(rel.key)}"
            self.assertNotIn(field_name, schema._meta.fields.keys())

    @override_settings(GRAPHQL_RELATIONSHIP_PREFIX="pr")
    def test_extend_relationship_w_prefix(self):
        """Verify that relationships are correctly added to the schema when using a custom prefix setting."""
        schema = extend_schema_type_relationships(self.location_schema, Location)

        # Relationships on Location
        for rel, peer_side in [
            (self.o2m_1, "destination"),
            (self.o2o_1, "source"),
            (self.o2os_1, "peer"),
        ]:
            field_name = f"pr_{str_to_var_name(rel.key)}"
            self.assertIn(field_name, schema._meta.fields.keys())
            self.assertIsInstance(schema._meta.fields[field_name], graphene.types.field.Field)
            if rel.has_many(peer_side):
                self.assertIsInstance(schema._meta.fields[field_name].type, graphene.types.structures.List)
            else:
                self.assertNotIsInstance(schema._meta.fields[field_name].type, graphene.types.structures.List)

        # Special handling of same-type non-symmetric relationships
        for rel in [self.o2m_same_type_1]:
            for peer_side in ["source", "destination"]:
                field_name = f"pr_{str_to_var_name(rel.key)}_{peer_side}"
                self.assertIn(field_name, schema._meta.fields.keys())
                self.assertIsInstance(schema._meta.fields[field_name], graphene.types.field.Field)
                if rel.has_many(peer_side):
                    self.assertIsInstance(schema._meta.fields[field_name].type, graphene.types.structures.List)
                else:
                    self.assertNotIsInstance(schema._meta.fields[field_name].type, graphene.types.structures.List)

        # Relationships not on Location
        for rel in [self.m2m_1, self.m2m_2]:
            field_name = f"pr_{str_to_var_name(rel.key)}"
            self.assertNotIn(field_name, schema._meta.fields.keys())


class GraphQLSearchParameters(TestCase):
    def setUp(self):
        self.schema = generate_schema_type(app_name="dcim", model=Location)

    def test_search_parameters(self):
        fields = LocationFilterSet().filters.keys()
        params = generate_list_search_parameters(self.schema)
        exclude_filters = ["type"]

        for field in fields:
            field = str_to_var_name(field)
            if field not in exclude_filters:
                self.assertIn(field, params.keys())
            else:
                self.assertNotIn(field, params.keys())


class GraphQLAPIPermissionTest(TestCase):
    client_class = NautobotTestClient

    @classmethod
    def setUpTestData(cls):
        """Initialize the Database with some datas and multiple users associated with different permissions."""
        cls.groups = (
            Group.objects.create(name="Group 1"),
            Group.objects.create(name="Group 2"),
        )

        cls.users = (
            User.objects.create(username="User 1", is_active=True),
            User.objects.create(username="User 2", is_active=True),
            User.objects.create(username="Super User", is_active=True, is_superuser=True),
            User.objects.create(username="Nobody", is_active=True),
        )

        cls.tokens = (
            Token.objects.create(user=cls.users[0], key="0123456789abcdef0123456789abcdef01234567"),
            Token.objects.create(user=cls.users[1], key="abcd456789abcdef0123456789abcdef01234567"),
            Token.objects.create(user=cls.users[2], key="efgh456789abcdef0123456789abcdef01234567"),
            Token.objects.create(user=cls.users[3], key="ijkl456789abcdef0123456789abcdef01234567"),
        )

        cls.clients = [cls.client_class(), cls.client_class(), cls.client_class(), cls.client_class()]
        cls.clients[0].credentials(HTTP_AUTHORIZATION=f"Token {cls.tokens[0].key}")
        cls.clients[1].credentials(HTTP_AUTHORIZATION=f"Token {cls.tokens[1].key}")
        cls.clients[2].credentials(HTTP_AUTHORIZATION=f"Token {cls.tokens[2].key}")
        cls.clients[3].credentials(HTTP_AUTHORIZATION=f"Token {cls.tokens[3].key}")

        cls.location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        cls.locations = (
            Location.objects.create(name="Location 1", location_type=cls.location_type, status=location_status),
            Location.objects.create(name="Location 2", location_type=cls.location_type, status=location_status),
        )

        location_object_type = ContentType.objects.get(app_label="dcim", model="location")
        rack_object_type = ContentType.objects.get(app_label="dcim", model="rack")

        # Apply permissions only to User 1 & 2
        for i in range(2):
            # Rack permission
            rack_obj_permission = ObjectPermission.objects.create(
                name=f"Permission Rack {i+1}",
                actions=["view", "add", "change", "delete"],
                constraints={"location__name": f"Location {i+1}"},
            )
            rack_obj_permission.object_types.add(rack_object_type)
            rack_obj_permission.groups.add(cls.groups[i])
            rack_obj_permission.users.add(cls.users[i])

            location_obj_permission = ObjectPermission.objects.create(
                name=f"Permission Location {i+1}",
                actions=["view", "add", "change", "delete"],
                constraints={"name": f"Location {i+1}"},
            )
            location_obj_permission.object_types.add(location_object_type)
            location_obj_permission.groups.add(cls.groups[i])
            location_obj_permission.users.add(cls.users[i])

        rack_status = Status.objects.get_for_model(Rack).first()
        cls.rack_grp1 = (
            Rack.objects.create(name="Rack 1-1", location=cls.locations[0], status=rack_status),
            Rack.objects.create(name="Rack 1-2", location=cls.locations[0], status=rack_status),
        )
        cls.rack_grp2 = (
            Rack.objects.create(name="Rack 2-1", location=cls.locations[1], status=rack_status),
            Rack.objects.create(name="Rack 2-2", location=cls.locations[1], status=rack_status),
        )

        cls.api_url = reverse("graphql-api")

        cls.get_racks_query = """
        query {
            racks {
                name
            }
        }
        """

        cls.get_racks_params_query = """
        query {
            racks(location: "Location 1") {
                name
            }
        }
        """

        cls.get_racks_var_query = """
        query ($location: [String]) {
            racks(location: $location) {
                name
            }
        }
        """

        cls.get_locations_racks_query = """
        query {
            locations {
                name
                racks {
                    name
                }
            }
        }
        """

        cls.get_rack_query = """
        query ($id: ID!) {
            rack (id: $id) {
                name
            }
        }
        """

    def test_graphql_api_token_with_perm(self):
        """Validate that users can query based on their permissions."""
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
        """Validate users with no permission are not able to query anything by default."""
        response = self.clients[3].post(self.api_url, {"query": self.get_racks_query}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["racks"], list)
        names = [item["name"] for item in response.data["data"]["racks"]]
        self.assertEqual(names, [])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_graphql_api_token_no_group_exempt(self):
        """Validate users with no permission are able to query based on the exempt permissions."""
        response = self.clients[3].post(self.api_url, {"query": self.get_racks_query}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["racks"], list)
        names = [item["name"] for item in response.data["data"]["racks"]]
        self.assertEqual(names, ["Rack 1-1", "Rack 1-2", "Rack 2-1", "Rack 2-2"])

    def test_graphql_api_no_token(self):
        """Validate unauthenticated users are not able to query anything by default."""
        response = self.client.post(self.api_url, {"query": self.get_racks_query}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["racks"], list)
        names = [item["name"] for item in response.data["data"]["racks"]]
        self.assertEqual(names, [])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_graphql_api_no_token_exempt(self):
        """Validate unauthenticated users are able to query based on the exempt permissions."""
        response = self.client.post(self.api_url, {"query": self.get_racks_query}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["racks"], list)
        names = [item["name"] for item in response.data["data"]["racks"]]
        self.assertEqual(names, ["Rack 1-1", "Rack 1-2", "Rack 2-1", "Rack 2-2"])

    def test_graphql_api_wrong_token(self):
        """Validate a wrong token return 403."""
        self.client.credentials(HTTP_AUTHORIZATION="Token zzzzzzzzzzabcdef0123456789abcdef01234567")
        response = self.client.post(self.api_url, {"query": self.get_racks_query}, format="json")
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
        payload = {"query": self.get_racks_var_query, "variables": {"location": "Location 1"}}
        response = self.clients[2].post(self.api_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["racks"], list)
        names = [item["name"] for item in response.data["data"]["racks"]]
        self.assertEqual(names, ["Rack 1-1", "Rack 1-2"])

        payload = {"query": self.get_racks_var_query, "variables": {"location": "Location 2"}}
        response = self.clients[2].post(self.api_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["racks"], list)
        names = [item["name"] for item in response.data["data"]["racks"]]
        self.assertEqual(names, ["Rack 2-1", "Rack 2-2"])

    def test_graphql_single_object_query(self):
        """Validate graphql query for a single object as opposed to a set of objects also works."""
        payload = {"query": self.get_rack_query, "variables": {"id": Rack.objects.first().pk}}
        response = self.clients[2].post(self.api_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["rack"], dict)
        self.assertEqual(response.data["data"]["rack"]["name"], Rack.objects.first().name)

    def test_graphql_query_multi_level(self):
        """Validate request with multiple levels return the proper information, following the permissions."""
        response = self.clients[0].post(self.api_url, {"query": self.get_locations_racks_query}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["locations"], list)
        self.assertGreater(len(response.data["data"]["locations"]), 0)
        location_names = [item["name"] for item in response.data["data"]["locations"]]
        rack_names = [item["name"] for item in response.data["data"]["locations"][0]["racks"]]
        self.assertEqual(location_names, ["Location 1"])
        self.assertEqual(rack_names, ["Rack 1-1", "Rack 1-2"])

    def test_graphql_query_format(self):
        """Validate application/graphql query is working properly."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.tokens[2].key}")
        response = self.client.post(
            self.api_url,
            data=self.get_locations_racks_query,
            content_type="application/graphql",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["data"]["locations"], list)
        location_names = [item["name"] for item in response.data["data"]["locations"]]
        location_list = list(Location.objects.values_list("name", flat=True))
        self.assertEqual(location_names, location_list)


class GraphQLQueryTest(TestCase):
    """Execute various GraphQL queries and verify their correct responses."""

    @classmethod
    def setUpTestData(cls):
        """Initialize the Database with some datas."""
        super().setUpTestData()
        cls.user = User.objects.create(username="Super User", is_active=True, is_superuser=True)

        # Remove random IPAddress fixtures for this custom test
        IPAddress.objects.all().delete()

        # Initialize fake request that will be required to execute GraphQL query
        cls.request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        cls.request.id = uuid.uuid4()
        cls.request.user = cls.user

        # Populate Data
        cls.device_type1 = DeviceType.objects.first()
        cls.device_type2 = DeviceType.objects.last()
        roles = Role.objects.get_for_model(Device)
        cls.device_role1 = roles[0]
        cls.device_role2 = roles[1]
        cls.device_role3 = random.choice(roles)
        cls.location_statuses = list(Status.objects.get_for_model(Location))[:2]
        cls.location_type = LocationType.objects.get(name="Campus")
        cls.location1 = Location.objects.filter(location_type=cls.location_type).first()
        cls.location2 = Location.objects.filter(location_type=cls.location_type).last()
        cls.location1.name = "Location-1"
        cls.location2.name = "Location-2"
        cls.location1.status = cls.location_statuses[0]
        cls.location2.status = cls.location_statuses[1]
        cls.location1.validated_save()
        cls.location2.validated_save()
        rack_statuses = Status.objects.get_for_model(Rack)
        cls.rack1 = Rack.objects.create(name="Rack 1", location=cls.location1, status=rack_statuses[0])
        cls.rack2 = Rack.objects.create(name="Rack 2", location=cls.location2, status=rack_statuses[1])
        cls.tenant1 = Tenant.objects.create(name="Tenant 1")
        cls.tenant2 = Tenant.objects.create(name="Tenant 2")

        vlan_statuses = Status.objects.get_for_model(VLAN)
        vlan_groups = (
            VLANGroupFactory.create(location=cls.location1),
            VLANGroupFactory.create(location=cls.location2),
        )
        cls.vlan1 = VLAN.objects.create(
            name="VLAN 1", vid=100, location=cls.location1, status=vlan_statuses[0], vlan_group=vlan_groups[0]
        )
        cls.vlan2 = VLAN.objects.create(
            name="VLAN 2", vid=200, location=cls.location2, status=vlan_statuses[1], vlan_group=vlan_groups[1]
        )

        cls.location1_power_panels = [
            PowerPanel.objects.create(name="location1-powerpanel1", location=cls.location1),
            PowerPanel.objects.create(name="location1-powerpanel2", location=cls.location1),
            PowerPanel.objects.create(name="location1-powerpanel3", location=cls.location1),
        ]
        powerfeed_status = Status.objects.get_for_model(PowerFeed).first()
        cls.location1_power_feeds = [
            PowerFeed.objects.create(
                name="location1-powerfeed1",
                status=powerfeed_status,
                power_panel=cls.location1_power_panels[0],
            ),
            PowerFeed.objects.create(
                name="location1-powerfeed2",
                status=powerfeed_status,
                power_panel=cls.location1_power_panels[1],
            ),
        ]

        cls.device_statuses = list(Status.objects.get_for_model(Device))[:2]
        cls.upsdevice1 = Device.objects.create(
            name="UPS 1",
            device_type=cls.device_type2,
            role=cls.device_role3,
            location=cls.location1,
            status=cls.device_statuses[0],
            rack=cls.rack1,
            tenant=cls.tenant1,
            face="front",
            comments="UPS Device",
        )
        cls.upsdevice1_power_ports = [
            PowerPort.objects.create(device=cls.upsdevice1, name="Power Port 1"),
            PowerPort.objects.create(device=cls.upsdevice1, name="Power Port 2"),
        ]
        cls.upsdevice1_power_outlets = [
            PowerOutlet.objects.create(name="Power Outlet 1", device=cls.upsdevice1),
            PowerOutlet.objects.create(name="Power Outlet 2", device=cls.upsdevice1),
        ]

        cls.device1 = Device.objects.create(
            name="Device 1",
            device_type=cls.device_type1,
            role=cls.device_role1,
            location=cls.location1,
            status=cls.device_statuses[0],
            rack=cls.rack1,
            tenant=cls.tenant1,
            face="front",
            comments="First Device",
        )

        cls.device1_rear_ports = (
            RearPort.objects.create(device=cls.device1, name="Rear Port 1", type=PortTypeChoices.TYPE_8P8C),
            RearPort.objects.create(device=cls.device1, name="Rear Port 2", type=PortTypeChoices.TYPE_8P8C),
            RearPort.objects.create(device=cls.device1, name="Rear Port 3", type=PortTypeChoices.TYPE_8P8C),
            RearPort.objects.create(device=cls.device1, name="Rear Port 4", type=PortTypeChoices.TYPE_8P4C),
        )

        cls.device1_console_ports = (
            ConsolePort.objects.create(
                device=cls.device1, name="Console Port 1", type=ConsolePortTypeChoices.TYPE_RJ45
            ),
            ConsolePort.objects.create(
                device=cls.device1, name="Console Port 2", type=ConsolePortTypeChoices.TYPE_RJ45
            ),
        )

        cls.device1_console_server_ports = (
            ConsoleServerPort.objects.create(
                device=cls.device1, name="Console Port 1", type=ConsolePortTypeChoices.TYPE_RJ45
            ),
            ConsoleServerPort.objects.create(
                device=cls.device1, name="Console Port 2", type=ConsolePortTypeChoices.TYPE_RJ45
            ),
        )

        cls.device1_power_ports = [
            PowerPort.objects.create(device=cls.device1, name="Power Port 1"),
            PowerPort.objects.create(device=cls.device1, name="Power Port 2"),
        ]

        cls.device1_front_ports = [
            FrontPort.objects.create(
                device=cls.device1,
                name="Front Port 1",
                type=PortTypeChoices.TYPE_8P8C,
                rear_port=cls.device1_rear_ports[0],
            ),
            FrontPort.objects.create(
                device=cls.device1,
                name="Front Port 2",
                type=PortTypeChoices.TYPE_8P8C,
                rear_port=cls.device1_rear_ports[1],
            ),
            FrontPort.objects.create(
                device=cls.device1,
                name="Front Port 3",
                type=PortTypeChoices.TYPE_8P8C,
                rear_port=cls.device1_rear_ports[2],
            ),
            FrontPort.objects.create(
                device=cls.device1,
                name="Front Port 4",
                type=PortTypeChoices.TYPE_8P4C,
                rear_port=cls.device1_rear_ports[3],
            ),
        ]

        interface_status = Status.objects.get_for_model(Interface).first()
        cls.interface11 = Interface.objects.create(
            name="Int1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            device=cls.device1,
            mac_address="00:11:11:11:11:11",
            mode=InterfaceModeChoices.MODE_ACCESS,
            untagged_vlan=cls.vlan1,
            status=interface_status,
        )
        cls.interface12 = Interface.objects.create(
            name="Int2",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            device=cls.device1,
            status=interface_status,
        )
        cls.ip_statuses = list(Status.objects.get_for_model(IPAddress))[:2]
        cls.prefix_statuses = list(Status.objects.get_for_model(Prefix))[:2]
        cls.namespace = Namespace.objects.first()
        cls.prefix1 = Prefix.objects.create(
            prefix="10.0.1.0/24", namespace=cls.namespace, status=cls.prefix_statuses[0]
        )
        cls.ipaddr1 = IPAddress.objects.create(
            address="10.0.1.1/24", namespace=cls.namespace, status=cls.ip_statuses[0]
        )
        cls.interface11.add_ip_addresses(cls.ipaddr1)

        cls.device2 = Device.objects.create(
            name="Device 2",
            device_type=cls.device_type1,
            role=cls.device_role2,
            location=cls.location1,
            status=cls.device_statuses[1],
            rack=cls.rack2,
            tenant=cls.tenant2,
            face="rear",
        )

        cls.interface21 = Interface.objects.create(
            name="Int1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            device=cls.device2,
            untagged_vlan=cls.vlan2,
            mode=InterfaceModeChoices.MODE_ACCESS,
            status=interface_status,
        )
        cls.interface22 = Interface.objects.create(
            name="Int2",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            device=cls.device2,
            mac_address="00:12:12:12:12:12",
            status=interface_status,
        )
        cls.prefix2 = Prefix.objects.create(
            prefix="10.0.2.0/24", namespace=cls.namespace, status=cls.prefix_statuses[1]
        )
        cls.ipaddr2 = IPAddress.objects.create(
            address="10.0.2.1/30", namespace=cls.namespace, status=cls.ip_statuses[1]
        )
        cls.interface12.add_ip_addresses(cls.ipaddr2)

        cls.device3 = Device.objects.create(
            name="Device 3",
            device_type=cls.device_type1,
            role=cls.device_role1,
            location=cls.location2,
            status=cls.device_statuses[0],
        )

        cls.interface31 = Interface.objects.create(
            name="Int1", type=InterfaceTypeChoices.TYPE_VIRTUAL, device=cls.device3, status=interface_status
        )
        cls.interface31 = Interface.objects.create(
            name="Mgmt1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            device=cls.device3,
            mgmt_only=True,
            enabled=False,
            status=interface_status,
        )

        cable_statuses = Status.objects.get_for_model(Cable)
        cls.cable1 = Cable.objects.create(
            termination_a=cls.interface11,
            termination_b=cls.interface12,
            status=cable_statuses[0],
        )
        cls.cable2 = Cable.objects.create(
            termination_a=cls.interface31,
            termination_b=cls.interface21,
            status=cable_statuses[1],
        )

        # Power Cables
        cls.cable3 = Cable.objects.create(
            termination_a=cls.device1_power_ports[0],
            termination_b=cls.upsdevice1_power_outlets[0],
            status=cable_statuses[0],
        )
        cls.cable3 = Cable.objects.create(
            termination_a=cls.upsdevice1_power_ports[0],
            termination_b=cls.location1_power_feeds[0],
            status=cable_statuses[0],
        )

        ConfigContext.objects.create(name="context 1", weight=101, data={"a": 123, "b": 456, "c": 777})

        Provider.objects.create(name="provider 1", asn=1)
        Provider.objects.create(name="provider 2", asn=4294967295)

        webhook1 = Webhook.objects.create(name="webhook 1", type_delete=True, enabled=False)
        webhook1.content_types.add(ContentType.objects.get_for_model(Device))
        webhook2 = Webhook.objects.create(name="webhook 2", type_update=True, enabled=False)
        webhook2.content_types.add(ContentType.objects.get_for_model(Interface))

        clustertype = ClusterTypeFactory.create()
        cluster = Cluster.objects.create(name="Cluster 1", cluster_type=clustertype)
        cls.virtualmachine = VirtualMachine.objects.create(
            name="Virtual Machine 1",
            cluster=cluster,
            status=Status.objects.get_for_model(VirtualMachine)[0],
        )
        vmintf_status = Status.objects.get_for_model(VMInterface).first()
        cls.vminterface = VMInterface.objects.create(
            virtual_machine=cls.virtualmachine,
            name="eth0",
            status=vmintf_status,
        )
        cls.vmprefix = Prefix.objects.create(
            prefix="1.1.1.0/24", namespace=cls.namespace, status=cls.prefix_statuses[0]
        )
        cls.vmipaddr = IPAddress.objects.create(
            address="1.1.1.1/32", namespace=cls.namespace, status=cls.ip_statuses[0]
        )
        cls.vminterface.add_ip_addresses(cls.vmipaddr)

        cls.relationship_o2o_1 = Relationship(
            label="Device to VirtualMachine",
            key="device_to_vm",
            source_type=ContentType.objects.get_for_model(Device),
            destination_type=ContentType.objects.get_for_model(VirtualMachine),
            type="one-to-one",
        )
        cls.relationship_o2o_1.validated_save()

        cls.ro2o_assoc_1 = RelationshipAssociation(
            relationship=cls.relationship_o2o_1,
            source=cls.device1,
            destination=cls.virtualmachine,
        )
        cls.ro2o_assoc_1.validated_save()

        cls.relationship_m2ms_1 = Relationship(
            label="Device Group",
            key="device_group",
            source_type=ContentType.objects.get_for_model(Device),
            destination_type=ContentType.objects.get_for_model(Device),
            type="symmetric-many-to-many",
        )
        cls.relationship_m2ms_1.validated_save()

        cls.rm2ms_assoc_1 = RelationshipAssociation(
            relationship=cls.relationship_m2ms_1,
            source=cls.device1,
            destination=cls.device2,
        )
        cls.rm2ms_assoc_1.validated_save()
        cls.rm2ms_assoc_2 = RelationshipAssociation(
            relationship=cls.relationship_m2ms_1,
            source=cls.device2,
            destination=cls.device3,
        )
        cls.rm2ms_assoc_2.validated_save()
        cls.rm2ms_assoc_3 = RelationshipAssociation(
            relationship=cls.relationship_m2ms_1,
            source=cls.device3,
            destination=cls.device1,
        )
        cls.rm2ms_assoc_3.validated_save()

        cls.backend = get_default_backend()
        cls.schema = graphene_settings.SCHEMA

    def execute_query(self, query, variables=None):
        document = self.backend.document_from_string(self.schema, query)
        if variables:
            return document.execute(context_value=self.request, variable_values=variables)
        else:
            return document.execute(context_value=self.request)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_circuit_terminations_cable_peer(self):
        """Test querying circuit terminations for their cable peers"""

        query = """\
query {
    circuit_terminations {
        id
        cable_peer_circuit_termination { id }
        cable_peer_front_port { id }
        cable_peer_interface { id }
        cable_peer_rear_port { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(CircuitTermination.objects.all()), len(result.data["circuit_terminations"]))
        for circuit_term_entry in result.data["circuit_terminations"]:
            circuit_term_obj = CircuitTermination.objects.get(id=circuit_term_entry["id"])
            cable_peer = circuit_term_obj.get_cable_peer()

            # Extract Expected Properties from CircuitTermination object
            cable_peer_circuit_termination = (
                {"id": str(cable_peer.id)} if isinstance(cable_peer, CircuitTermination) else None
            )
            cable_peer_interface = {"id": str(cable_peer.id)} if isinstance(cable_peer, Interface) else None
            cable_peer_front_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, FrontPort) else None
            cable_peer_rear_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, RearPort) else None

            # Assert GraphQL returned properties match those expected
            self.assertEqual(circuit_term_entry["cable_peer_circuit_termination"], cable_peer_circuit_termination)
            self.assertEqual(circuit_term_entry["cable_peer_interface"], cable_peer_interface)
            self.assertEqual(circuit_term_entry["cable_peer_front_port"], cable_peer_front_port)
            self.assertEqual(circuit_term_entry["cable_peer_rear_port"], cable_peer_rear_port)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_circuit_termination_connected_endpoint(self):
        """Test querying circuit terminations for their connnected endpoints."""

        query = """\
query {
    circuit_terminations {
        id
        connected_circuit_termination { id }
        connected_interface { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(CircuitTermination.objects.all()), len(result.data["circuit_terminations"]))
        for circuit_term_entry in result.data["circuit_terminations"]:
            circuit_term_obj = CircuitTermination.objects.get(id=circuit_term_entry["id"])
            connected_endpoint = circuit_term_obj.connected_endpoint

            # Extract Expected Properties from CircuitTermination object
            connected_circuit_termination = (
                {"id": str(connected_endpoint.id)} if isinstance(connected_endpoint, CircuitTermination) else None
            )
            connected_interface = (
                {"id": str(connected_endpoint.id)} if isinstance(connected_endpoint, Interface) else None
            )

            # Assert GraphQL returned properties match those expected
            self.assertEqual(circuit_term_entry["connected_circuit_termination"], connected_circuit_termination)
            self.assertEqual(circuit_term_entry["connected_interface"], connected_interface)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_config_context_and_custom_field_data(self):
        query = (
            # pylint: disable=consider-using-f-string
            """
                query {
                    devices {
                        name
                        config_context
                        _custom_field_data
                    }
                    device (id: "%s") {
                        name
                        config_context
                        _custom_field_data
                    }
                }
            """
            % (self.device1.id)
        )

        expected_data = {"a": 123, "b": 456, "c": 777}

        result = self.execute_query(query)

        self.assertIsInstance(result.data["devices"], list)
        self.assertIsInstance(result.data["device"], dict)

        device_names = [item["name"] for item in result.data["devices"]]
        self.assertEqual(sorted(device_names), ["Device 1", "Device 2", "Device 3", "UPS 1"])
        self.assertEqual(result.data["device"]["name"], "Device 1")

        config_contexts = [item["config_context"] for item in result.data["devices"]]
        self.assertIsInstance(config_contexts[0], dict)
        self.assertDictEqual(config_contexts[0], expected_data)
        self.assertEqual(result.data["device"]["config_context"], expected_data)

        custom_field_data = [item["_custom_field_data"] for item in result.data["devices"]]
        self.assertIsInstance(custom_field_data[0], dict)
        self.assertEqual(custom_field_data[0], {})
        self.assertEqual(result.data["device"]["_custom_field_data"], {})

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_console_ports_cable_peer(self):
        """Test querying console port terminations for their cable peers"""

        query = """\
query {
    console_ports {
        id
        cable_peer_console_server_port { id }
        cable_peer_front_port { id }
        cable_peer_rear_port { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(ConsolePort.objects.all()), len(result.data["console_ports"]))
        for console_port_entry in result.data["console_ports"]:
            console_port_obj = ConsolePort.objects.get(id=console_port_entry["id"])
            cable_peer = console_port_obj.get_cable_peer()

            # Extract Expected Properties from CircuitTermination object
            cable_peer_console_server_port = (
                {"id": str(cable_peer.id)} if isinstance(cable_peer, ConsoleServerPort) else None
            )
            cable_peer_front_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, FrontPort) else None
            cable_peer_rear_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, RearPort) else None

            # Assert GraphQL returned properties match those expected
            self.assertEqual(console_port_entry["cable_peer_console_server_port"], cable_peer_console_server_port)
            self.assertEqual(console_port_entry["cable_peer_front_port"], cable_peer_front_port)
            self.assertEqual(console_port_entry["cable_peer_rear_port"], cable_peer_rear_port)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_console_ports_connected_endpoint(self):
        """Test querying console ports for their connnected endpoints."""

        query = """\
query {
    console_ports {
        id
        connected_console_server_port { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(ConsolePort.objects.all()), len(result.data["console_ports"]))
        for console_port_entry in result.data["console_ports"]:
            console_port_obj = ConsolePort.objects.get(id=console_port_entry["id"])
            connected_endpoint = console_port_obj.connected_endpoint

            # Extract Expected Properties from CircuitTermination object
            connected_console_server_port = (
                {"id": str(connected_endpoint.id)} if isinstance(connected_endpoint, ConsoleServerPort) else None
            )

            # Assert GraphQL returned properties match those expected
            self.assertEqual(console_port_entry["connected_console_server_port"], connected_console_server_port)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_console_server_ports_cable_peer(self):
        """Test querying console server port terminations for their cable peers"""

        query = """\
query {
    console_server_ports {
        id
        cable_peer_console_port { id }
        cable_peer_front_port { id }
        cable_peer_rear_port { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(ConsoleServerPort.objects.all()), len(result.data["console_server_ports"]))
        for console_server_port_entry in result.data["console_server_ports"]:
            console_server_port_obj = ConsoleServerPort.objects.get(id=console_server_port_entry["id"])
            cable_peer = console_server_port_obj.get_cable_peer()

            # Extract Expected Properties from CircuitTermination object
            cable_peer_console_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, ConsolePort) else None
            cable_peer_front_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, FrontPort) else None
            cable_peer_rear_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, RearPort) else None

            # Assert GraphQL returned properties match those expected
            self.assertEqual(console_server_port_entry["cable_peer_console_port"], cable_peer_console_port)
            self.assertEqual(console_server_port_entry["cable_peer_front_port"], cable_peer_front_port)
            self.assertEqual(console_server_port_entry["cable_peer_rear_port"], cable_peer_rear_port)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_console_server_ports_connected_endpoint(self):
        """Test querying console server ports for their connnected endpoints."""

        query = """\
query {
    console_server_ports {
        id
        connected_console_port { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(ConsoleServerPort.objects.all()), len(result.data["console_server_ports"]))
        for console_server_port_entry in result.data["console_server_ports"]:
            console_server_port_obj = ConsoleServerPort.objects.get(id=console_server_port_entry["id"])
            connected_endpoint = console_server_port_obj.connected_endpoint

            # Extract Expected Properties from CircuitTermination object
            connected_console_port = (
                {"id": str(connected_endpoint.id)} if isinstance(connected_endpoint, ConsolePort) else None
            )

            # Assert GraphQL returned properties match those expected
            self.assertEqual(console_server_port_entry["connected_console_port"], connected_console_port)

    @skip(
        "Works in isolation, fails as part of the overall test suite due to issue #446, also something is broken with content types"
    )
    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_relationship_associations(self):
        """Test queries involving relationship associations."""

        # Query testing for https://github.com/nautobot/nautobot/issues/1228

        query = (
            # pylint: disable=consider-using-f-string
            """
                query {
                    device (id: "%s") {
                        name
                        rel_device_to_vm {
                            id
                        }
                        rel_device_group {
                            id
                        }
                    }
                }
            """
            % (self.device1.id)
        )
        result = self.execute_query(query)

        self.assertIsInstance(result.data, dict, result)
        self.assertIsInstance(result.data["device"], dict, result)
        self.assertEqual(result.data["device"]["name"], self.device1.name)
        self.assertIsInstance(result.data["device"]["rel_device_to_vm"], dict, result)
        self.assertEqual(result.data["device"]["rel_device_to_vm"]["id"], str(self.virtualmachine.id))
        self.assertIsInstance(result.data["device"]["rel_device_group"], list, result)
        self.assertIn(str(self.device2.id), set(item["id"] for item in result.data["device"]["rel_device_group"]))
        self.assertIn(str(self.device3.id), set(item["id"] for item in result.data["device"]["rel_device_group"]))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_device_role_filter(self):
        query = (
            # pylint: disable=consider-using-f-string
            """
                query {
                    devices(role: "%s") {
                        id
                        name
                    }
                }
            """
            % (self.device_role1.name,)
        )
        result = self.execute_query(query)

        expected = list(Device.objects.filter(role=self.device_role1).values_list("name", flat=True))
        self.assertEqual(len(result.data["devices"]), len(expected))
        device_names = [item["name"] for item in result.data["devices"]]
        self.assertEqual(sorted(device_names), sorted(expected))

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
    def test_query_locations_filter(self):
        filters = (
            ('name: "Location-1"', 1),
            ('name: ["Location-1"]', 1),
            ('name: ["Location-1", "Location-2"]', 2),
            ('name__ic: "Location"', Location.objects.filter(name__icontains="Location").count()),
            ('name__ic: ["Location"]', Location.objects.filter(name__icontains="Location").count()),
            ('name__nic: "Location"', Location.objects.exclude(name__icontains="Location").count()),
            ('name__nic: ["Location"]', Location.objects.exclude(name__icontains="Location").count()),
            ("asn: 65000", Location.objects.filter(asn="65000").count()),
            ("asn: [65099]", Location.objects.filter(asn="65099").count()),
            ("asn: [65000, 65099]", Location.objects.filter(asn__in=["65000", "65099"]).count()),
            (f'id: "{self.location1.pk}"', 1),
            (f'id: ["{self.location1.pk}"]', 1),
            (f'id: ["{self.location1.pk}", "{self.location2.pk}"]', 2),
            (
                f'status: "{self.location_statuses[0].name}"',
                Location.objects.filter(status=self.location_statuses[0]).count(),
            ),
            (
                f'status: ["{self.location_statuses[1].name}"]',
                Location.objects.filter(status=self.location_statuses[1]).count(),
            ),
            (
                f'status: ["{self.location_statuses[0].name}", "{self.location_statuses[1].name}"]',
                Location.objects.filter(status__in=self.location_statuses[:2]).count(),
            ),
        )

        for filterv, nbr_expected_results in filters:
            with self.subTest(msg=f"Checking {filterv}", filterv=filterv, nbr_expected_results=nbr_expected_results):
                query = "query { locations(" + filterv + "){ name }}"
                result = self.execute_query(query)
                self.assertIsNone(result.errors)
                self.assertEqual(len(result.data["locations"]), nbr_expected_results)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_devices_filter(self):
        filterset_class = DeviceFilterSet
        queryset = Device.objects.all()

        def _count(params, filterset_class=filterset_class, queryset=queryset):
            return filterset_class(params, queryset).qs.count()

        filters = {
            f'name: "{self.device1.name}"': _count({"name": [self.device1.name]}),
            f'name: ["{self.device1.name}"]': _count({"name": [self.device1.name]}),
            f'name: ["{self.device1.name}", "{self.device2.name}"]': _count(
                {"name": [self.device1.name, self.device2.name]}
            ),
            'name__ic: "Device"': _count({"name__ic": ["Device"]}),
            'name__ic: ["Device"]': _count({"name__ic": ["Device"]}),
            'name__nic: "Device"': _count({"name__nic": ["Device"]}),
            'name__nic: ["Device"]': _count({"name__nic": ["Device"]}),
            f'id: "{self.device1.pk}"': _count({"id": [self.device1.pk]}),
            f'id: ["{self.device1.pk}"]': _count({"id": [self.device1.pk]}),
            f'id: ["{self.device1.pk}", "{self.device2.pk}"]': _count({"id": [self.device1.pk, self.device2.pk]}),
            f'role: "{self.device_role1.name}"': _count({"role": [self.device_role1.name]}),
            f'role: ["{self.device_role1.name}"]': _count({"role": [self.device_role1.name]}),
            f'role: ["{self.device_role1.name}", "{self.device_role2.name}"]': _count(
                {"role": [self.device_role1.name, self.device_role2.name]}
            ),
            f'location: "{self.location1.name}"': _count({"location": [self.location1.name]}),
            f'location: ["{self.location1.name}"]': _count({"location": [self.location1.name]}),
            f'location: ["{self.location1.name}", "{self.location2.name}"]': _count(
                {"location": [self.location1.name, self.location2.name]}
            ),
            'face: "front"': _count({"face": ["front"]}),
            'face: "rear"': _count({"face": ["rear"]}),
            f'status: "{self.device_statuses[0].name}"': _count({"status": [self.device_statuses[0].name]}),
            f'status: ["{self.device_statuses[1].name}"]': _count({"status": [self.device_statuses[1].name]}),
            f'status: ["{self.device_statuses[0].name}", "{self.device_statuses[1].name}"]': _count(
                {"status": [self.device_statuses[0].name, self.device_statuses[1].name]}
            ),
            "is_full_depth: true": _count({"is_full_depth": True}),
            "is_full_depth: false": _count({"is_full_depth": False}),
            "has_primary_ip: true": _count({"has_primary_ip": True}),
            "has_primary_ip: false": _count({"has_primary_ip": False}),
            'mac_address: "00:11:11:11:11:11"': _count({"mac_address": ["00:11:11:11:11:11"]}),
            'mac_address: ["00:12:12:12:12:12"]': _count({"mac_address": ["00:12:12:12:12:12"]}),
            'mac_address: ["00:11:11:11:11:11", "00:12:12:12:12:12"]': _count(
                {"mac_address": ["00:11:11:11:11:11", "00:12:12:12:12:12"]}
            ),
            'mac_address: "99:11:11:11:11:11"': _count({"mac_address": ["99:11:11:11:11:11"]}),
            'q: "first"': _count({"q": "first"}),
            'q: "notthere"': _count({"q": "notthere"}),
        }

        for filterv, nbr_expected_results in filters.items():
            with self.subTest(msg=f"Checking {filterv}", filterv=filterv, nbr_expected_results=nbr_expected_results):
                query = "query {devices(" + filterv + "){ name }}"
                result = self.execute_query(query)
                self.assertIsNone(result.errors)
                self.assertEqual(len(result.data["devices"]), nbr_expected_results)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_ip_addresses_filter(self):
        filters = (
            (
                'address: "10.0.1.1"',
                IPAddress.objects.filter(host="10.0.1.1").count(),
            ),
            (
                "ip_version: 4",
                IPAddress.objects.filter(ip_version=4).count(),
            ),
            (
                f'status: "{self.ip_statuses[0].name}"',
                IPAddress.objects.filter(status=self.ip_statuses[0]).count(),
            ),
            (
                f'status: ["{self.ip_statuses[1].name}"]',
                IPAddress.objects.filter(status=self.ip_statuses[1]).count(),
            ),
            (
                f'status: ["{self.ip_statuses[0].name}", "{self.ip_statuses[1].name}"]',
                IPAddress.objects.filter(status__in=[self.ip_statuses[0], self.ip_statuses[1]]).count(),
            ),
            (
                "mask_length: 24",
                IPAddress.objects.filter(mask_length=24).count(),
            ),
            (
                "mask_length: 30",
                IPAddress.objects.filter(mask_length=30).count(),
            ),
            (
                "mask_length: 32",
                IPAddress.objects.filter(mask_length=32).count(),
            ),
            (
                "mask_length: 28",
                IPAddress.objects.filter(mask_length=28).count(),
            ),
            (
                'prefix: "10.0.0.0/16"',
                IPAddress.objects.net_host_contained("10.0.0.0/16").count(),
            ),
            (
                'prefix: "10.0.2.0/24"',
                IPAddress.objects.net_host_contained("10.0.2.0/24").count(),
            ),
        )

        for filterv, nbr_expected_results in filters:
            with self.subTest(msg=f"Checking {filterv}", filterv=filterv, nbr_expected_results=nbr_expected_results):
                query = "query { ip_addresses(" + filterv + "){ address }}"
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
        interfaces {
            name
            device { name }
        }
        vm_interfaces {
            name
            virtual_machine { name }
        }
        ip_version
    }
}"""
        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(result.data["ip_addresses"]), 3)
        for entry in result.data["ip_addresses"]:
            self.assertIn(
                entry["address"], (str(self.ipaddr1.address), str(self.ipaddr2.address), str(self.vmipaddr.address))
            )
            self.assertIn("interfaces", entry)
            self.assertIn("vm_interfaces", entry)
            self.assertIn(entry["ip_version"], (4, 6))
            if entry["address"] == str(self.vmipaddr.address):
                self.assertEqual(entry["vm_interfaces"][0]["name"], self.vminterface.name)
                self.assertEqual(entry["interfaces"], [])
                self.assertIn("virtual_machine", entry["vm_interfaces"][0])
                self.assertEqual(entry["vm_interfaces"][0]["virtual_machine"]["name"], self.virtualmachine.name)
            else:
                self.assertIn(entry["interfaces"][0]["name"], (self.interface11.name, self.interface12.name))
                self.assertEqual(entry["vm_interfaces"], [])
                self.assertIn("device", entry["interfaces"][0])
                self.assertEqual(entry["interfaces"][0]["device"]["name"], self.device1.name)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_cables_filter(self):
        filters = (
            (f'device_id: "{self.device1.id}"', 2),
            ('device: "Device 3"', 1),
            ('device: ["Device 1", "Device 3"]', 3),
            (f'rack_id: "{self.rack1.id}"', 3),
            ('rack: "Rack 2"', 1),
            ('rack: ["Rack 1", "Rack 2"]', 4),
            (f'location_id: "{self.location1.id}"', 4),
            (f'location: "{self.location2.name}"', 1),
            (f'location: ["{self.location1.name}", "{self.location2.name}"]', 4),
            (f'tenant_id: "{self.tenant1.id}"', 3),
            ('tenant: "Tenant 2"', 1),
            ('tenant: ["Tenant 1", "Tenant 2"]', 4),
        )

        for filterv, nbr_expected_results in filters:
            with self.subTest(msg=f"Checking {filterv}", filterv=filterv, nbr_expected_results=nbr_expected_results):
                query = "query { cables(" + filterv + "){ id }}"
                result = self.execute_query(query)
                self.assertIsNone(result.errors)
                self.assertEqual(len(result.data["cables"]), nbr_expected_results)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_front_port_filter_second_level(self):
        """Test "second-level" filtering of FrontPorts within a Devices query."""

        filters = (
            (
                f'name: "{self.device1_front_ports[0].name}"',
                Q(name=self.device1_front_ports[0].name),
            ),
            (
                f'device: "{self.device1.name}"',
                Q(device=self.device1),
            ),
            (
                f'_type: "{PortTypeChoices.TYPE_8P8C}"',
                Q(type=PortTypeChoices.TYPE_8P8C),
            ),
        )

        for filterv, qs_filter in filters:
            with self.subTest(msg=f"Checking {filterv}", filterv=filterv, qs_filter=qs_filter):
                matched = 0
                query = "query { devices{ id, front_ports(" + filterv + "){ id }}}"
                result = self.execute_query(query)
                self.assertIsNone(result.errors)
                for device in result.data["devices"]:
                    qs = FrontPort.objects.filter(device_id=device["id"])
                    expected_count = qs.filter(qs_filter).count()
                    matched = max(matched, len(device["front_ports"]))
                    self.assertEqual(len(device["front_ports"]), expected_count)
                self.assertGreater(matched, 0, msg="At least one object matched GraphQL query")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_front_port_filter_third_level(self):
        """Test "third-level" filtering of FrontPorts within Devices within Locations."""

        filters = (
            (
                f'name: "{self.device1_front_ports[0].name}"',
                Q(name=self.device1_front_ports[0].name),
            ),
            (
                f'device: "{self.device1.name}"',
                Q(device=self.device1),
            ),
            (
                f'_type: "{PortTypeChoices.TYPE_8P8C}"',
                Q(type=PortTypeChoices.TYPE_8P8C),
            ),
        )

        for filterv, qs_filter in filters:
            with self.subTest(msg=f"Checking {filterv}", filterv=filterv, qs_filter=qs_filter):
                matched = 0
                query = "query { locations{ devices{ id, front_ports(" + filterv + "){ id }}}}"
                result = self.execute_query(query)
                self.assertIsNone(result.errors)
                for location in result.data["locations"]:
                    for device in location["devices"]:
                        qs = FrontPort.objects.filter(device_id=device["id"])
                        expected_count = qs.filter(qs_filter).count()
                        matched = max(matched, len(device["front_ports"]))
                        self.assertEqual(len(device["front_ports"]), expected_count)
                self.assertGreater(matched, 0, msg="At least one object matched GraphQL query")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_front_ports_cable_peer(self):
        """Test querying front port terminations for their cable peers"""

        query = """\
query {
    front_ports {
        id
        cable_peer_circuit_termination { id }
        cable_peer_console_port { id }
        cable_peer_console_server_port { id }
        cable_peer_front_port { id }
        cable_peer_interface { id }
        cable_peer_rear_port { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(FrontPort.objects.all()), len(result.data["front_ports"]))
        for entry in result.data["front_ports"]:
            front_port_obj = FrontPort.objects.get(id=entry["id"])
            cable_peer = front_port_obj.get_cable_peer()

            # Extract Expected Properties from CircuitTermination object
            cable_peer_circuit_termination = (
                {"id": str(cable_peer.id)} if isinstance(cable_peer, CircuitTermination) else None
            )
            cable_peer_console_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, ConsolePort) else None
            cable_peer_console_server_port = (
                {"id": str(cable_peer.id)} if isinstance(cable_peer, ConsoleServerPort) else None
            )
            cable_peer_front_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, FrontPort) else None
            cable_peer_interface = {"id": str(cable_peer.id)} if isinstance(cable_peer, Interface) else None
            cable_peer_rear_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, RearPort) else None

            # Assert GraphQL returned properties match those expected
            self.assertEqual(entry["cable_peer_circuit_termination"], cable_peer_circuit_termination)
            self.assertEqual(entry["cable_peer_console_port"], cable_peer_console_port)
            self.assertEqual(entry["cable_peer_console_server_port"], cable_peer_console_server_port)
            self.assertEqual(entry["cable_peer_front_port"], cable_peer_front_port)
            self.assertEqual(entry["cable_peer_interface"], cable_peer_interface)
            self.assertEqual(entry["cable_peer_rear_port"], cable_peer_rear_port)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_rear_ports_cable_peer(self):
        """Test querying rear port terminations for their cable peers"""

        query = """\
query {
    rear_ports {
        id
        cable_peer_circuit_termination { id }
        cable_peer_console_port { id }
        cable_peer_console_server_port { id }
        cable_peer_front_port { id }
        cable_peer_interface { id }
        cable_peer_rear_port { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(RearPort.objects.all()), len(result.data["rear_ports"]))
        for entry in result.data["rear_ports"]:
            rear_port_obj = RearPort.objects.get(id=entry["id"])
            cable_peer = rear_port_obj.get_cable_peer()

            # Extract Expected Properties from CircuitTermination object
            cable_peer_circuit_termination = (
                {"id": str(cable_peer.id)} if isinstance(cable_peer, CircuitTermination) else None
            )
            cable_peer_console_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, ConsolePort) else None
            cable_peer_console_server_port = (
                {"id": str(cable_peer.id)} if isinstance(cable_peer, ConsoleServerPort) else None
            )
            cable_peer_front_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, FrontPort) else None
            cable_peer_interface = {"id": str(cable_peer.id)} if isinstance(cable_peer, Interface) else None
            cable_peer_rear_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, RearPort) else None

            # Assert GraphQL returned properties match those expected
            self.assertEqual(entry["cable_peer_circuit_termination"], cable_peer_circuit_termination)
            self.assertEqual(entry["cable_peer_console_port"], cable_peer_console_port)
            self.assertEqual(entry["cable_peer_console_server_port"], cable_peer_console_server_port)
            self.assertEqual(entry["cable_peer_front_port"], cable_peer_front_port)
            self.assertEqual(entry["cable_peer_interface"], cable_peer_interface)
            self.assertEqual(entry["cable_peer_rear_port"], cable_peer_rear_port)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_interfaces_filter(self):
        """Test custom interface filter fields and boolean, not other concrete fields."""

        filters = (
            (
                f'device_id: "{self.device1.id}"',
                Interface.objects.filter(device=self.device1).count(),
            ),
            (
                'device: "Device 3"',
                Interface.objects.filter(device=self.device3).count(),
            ),
            (
                'device: ["Device 1", "Device 3"]',
                Interface.objects.filter(device__in=[self.device1, self.device3]).count(),
            ),
            (
                'kind: "virtual"',
                Interface.objects.filter(type=InterfaceTypeChoices.TYPE_VIRTUAL).count(),
            ),
            (
                'mac_address: "00:11:11:11:11:11"',
                Interface.objects.filter(mac_address="00:11:11:11:11:11").count(),
            ),
            (
                "vlan: 100",
                Interface.objects.filter(Q(untagged_vlan__vid=100) | Q(tagged_vlans__vid=100)).count(),
            ),
            (
                f'vlan_id: "{self.vlan1.id}"',
                Interface.objects.filter(Q(untagged_vlan=self.vlan1) | Q(tagged_vlans=self.vlan1)).count(),
            ),
            (
                "mgmt_only: true",
                Interface.objects.filter(mgmt_only=True).count(),
            ),
            (
                "enabled: false",
                Interface.objects.filter(enabled=False).count(),
            ),
        )

        for filterv, nbr_expected_results in filters:
            with self.subTest(msg=f"Checking {filterv}", filterv=filterv, nbr_expected_results=nbr_expected_results):
                query = "query { interfaces(" + filterv + "){ id }}"
                result = self.execute_query(query)
                self.assertIsNone(result.errors)
                self.assertEqual(len(result.data["interfaces"]), nbr_expected_results)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_interfaces_filter_second_level(self):
        """Test "second-level" filtering of Interfaces within a Devices query."""

        filters = (
            (
                f'device_id: "{self.device1.id}"',
                Q(device=self.device1),
            ),
            (
                'kind: "virtual"',
                Q(type=InterfaceTypeChoices.TYPE_VIRTUAL),
            ),
            (
                'mac_address: "00:11:11:11:11:11"',
                Q(mac_address="00:11:11:11:11:11"),
            ),
            (
                "vlan: 100",
                Q(untagged_vlan__vid=100) | Q(tagged_vlans__vid=100),
            ),
            (
                f'vlan_id: "{self.vlan1.id}"',
                Q(untagged_vlan=self.vlan1) | Q(tagged_vlans=self.vlan1),
            ),
        )

        for filterv, qs_filter in filters:
            with self.subTest(msg=f"Checking {filterv}", filterv=filterv, qs_filter=qs_filter):
                matched = 0
                query = "query { devices{ id, interfaces(" + filterv + "){ id }}}"
                result = self.execute_query(query)
                self.assertIsNone(result.errors)
                for device in result.data["devices"]:
                    qs = Interface.objects.filter(device_id=device["id"])
                    expected_count = qs.filter(qs_filter).count()
                    matched = max(matched, len(device["interfaces"]))
                    self.assertEqual(len(device["interfaces"]), expected_count)
                self.assertGreater(matched, 0, msg="At least one object matched GraphQL query")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_interfaces_filter_third_level(self):
        """Test "third-level" filtering of Interfaces within Devices within Locations."""

        filters = (
            (
                f'device_id: "{self.device1.id}"',
                Q(device=self.device1),
            ),
            (
                'kind: "virtual"',
                Q(type=InterfaceTypeChoices.TYPE_VIRTUAL),
            ),
            (
                'mac_address: "00:11:11:11:11:11"',
                Q(mac_address="00:11:11:11:11:11"),
            ),
            (
                "vlan: 100",
                Q(untagged_vlan__vid=100) | Q(tagged_vlans__vid=100),
            ),
            (
                f'vlan_id: "{self.vlan1.id}"',
                Q(untagged_vlan=self.vlan1) | Q(tagged_vlans=self.vlan1),
            ),
        )

        for filterv, qs_filter in filters:
            with self.subTest(msg=f"Checking {filterv}", filter=filterv, qs_filter=qs_filter):
                matched = 0
                query = "query { locations{ devices{ id, interfaces(" + filterv + "){ id }}}}"
                result = self.execute_query(query)
                self.assertIsNone(result.errors)
                for location in result.data["locations"]:
                    for device in location["devices"]:
                        qs = Interface.objects.filter(device_id=device["id"])
                        expected_count = qs.filter(qs_filter).count()
                        matched = max(matched, len(device["interfaces"]))
                        self.assertEqual(len(device["interfaces"]), expected_count)
                self.assertGreater(matched, 0, msg="At least one object matched GraphQL query")

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
        connected_circuit_termination { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(Interface.objects.all()), len(result.data["interfaces"]))
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
            # TODO: it would be nice to have connections to circuit terminations to test!
            self.assertIsNone(interface_entry["connected_circuit_termination"])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_interfaces_cable_peer(self):
        """Test querying interfaces for their cable peers"""

        query = """\
query {
    interfaces {
        id
        cable_peer { __typename }
        cable_peer_circuit_termination { id }
        cable_peer_interface { id }
        cable_peer_front_port { id }
        cable_peer_rear_port { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(Interface.objects.all()), len(result.data["interfaces"]))
        for interface_entry in result.data["interfaces"]:
            intf_obj = Interface.objects.get(id=interface_entry["id"])
            cable_peer = intf_obj.get_cable_peer()

            # Extract Expected Properties from Interface object
            cable_peer_circuit_termination = (
                {"id": str(cable_peer.id)} if isinstance(cable_peer, CircuitTermination) else None
            )
            cable_peer_interface = {"id": str(cable_peer.id)} if isinstance(cable_peer, Interface) else None
            cable_peer_front_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, FrontPort) else None
            cable_peer_rear_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, RearPort) else None

            # Assert GraphQL returned properties match those expected
            self.assertEqual(interface_entry["cable_peer_circuit_termination"], cable_peer_circuit_termination)
            self.assertEqual(interface_entry["cable_peer_interface"], cable_peer_interface)
            self.assertEqual(interface_entry["cable_peer_front_port"], cable_peer_front_port)
            self.assertEqual(interface_entry["cable_peer_rear_port"], cable_peer_rear_port)

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

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_device_types(self):
        """Test querying of device types, specifically checking for issue #1203."""
        query = """
        query {
            device_types {
                model
            }
        }
        """
        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertIsInstance(result.data, dict, result)
        self.assertIsInstance(result.data["device_types"], list, result)
        self.assertEqual(result.data["device_types"][0]["model"], self.device_type1.model, result)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_interface_pagination(self):
        query_pagination = """\
query {
    interfaces(limit: 2, offset: 3) {
        id
        name
        device {
          name
        }
    }
}"""
        query_all = """\
query {
    interfaces {
        id
        name
        device {
          name
        }
    }
}"""

        result_1 = self.execute_query(query_pagination)
        self.assertEqual(len(result_1.data.get("interfaces", [])), 2)

        # With the limit and skip implemented in the GQL query, this should return Device 2 (Int1) and
        # Device 3 (Int2). This test will validate that the correct device/interface combinations are returned.
        device_names = [item["device"]["name"] for item in result_1.data.get("interfaces", [])]
        self.assertEqual(sorted(device_names), ["Device 2", "Device 3"])
        interface_names = [item["name"] for item in result_1.data.get("interfaces", [])]
        self.assertEqual(interface_names, ["Int2", "Int1"])

        result_2 = self.execute_query(query_all)
        self.assertEqual(len(result_2.data.get("interfaces", [])), 6)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_power_feeds_cable_peer(self):
        """Test querying power feeds for their cable peers"""

        query = """\
query {
    power_feeds {
        id
        cable_peer_power_port { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(PowerFeed.objects.all()), len(result.data["power_feeds"]))
        for entry in result.data["power_feeds"]:
            power_feed_obj = PowerFeed.objects.get(id=entry["id"])
            cable_peer = power_feed_obj.get_cable_peer()

            # Extract Expected Properties from CircuitTermination object
            cable_peer_power_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, PowerPort) else None

            # Assert GraphQL returned properties match those expected
            self.assertEqual(entry["cable_peer_power_port"], cable_peer_power_port)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_power_feeds_connected_endpoint(self):
        """Test querying power feeds for their connected endpoints"""

        query = """\
query {
    power_feeds {
        id
        connected_power_port { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(PowerFeed.objects.all()), len(result.data["power_feeds"]))
        for entry in result.data["power_feeds"]:
            power_feed_obj = PowerFeed.objects.get(id=entry["id"])
            connected_endpoint = power_feed_obj.connected_endpoint

            # Extract Expected Properties from CircuitTermination object
            connected_power_port = (
                {"id": str(connected_endpoint.id)} if isinstance(connected_endpoint, PowerPort) else None
            )

            # Assert GraphQL returned properties match those expected
            self.assertEqual(entry["connected_power_port"], connected_power_port)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_power_outlets_cable_peer(self):
        """Test querying power outlets for their cable peers"""

        query = """\
query {
    power_outlets {
        id
        cable_peer_power_port { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(PowerOutlet.objects.all()), len(result.data["power_outlets"]))
        for entry in result.data["power_outlets"]:
            power_outlet_obj = PowerOutlet.objects.get(id=entry["id"])
            cable_peer = power_outlet_obj.get_cable_peer()

            # Extract Expected Properties from CircuitTermination object
            cable_peer_power_port = {"id": str(cable_peer.id)} if isinstance(cable_peer, PowerPort) else None

            # Assert GraphQL returned properties match those expected
            self.assertEqual(entry["cable_peer_power_port"], cable_peer_power_port)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_power_outlets_connected_endpoint(self):
        """Test querying power outlets for their connected endpoints"""

        query = """\
query {
    power_outlets {
        id
        connected_power_port { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(PowerOutlet.objects.all()), len(result.data["power_outlets"]))
        for entry in result.data["power_outlets"]:
            power_outlet_obj = PowerOutlet.objects.get(id=entry["id"])
            connected_endpoint = power_outlet_obj.connected_endpoint

            # Extract Expected Properties from CircuitTermination object
            connected_power_port = (
                {"id": str(connected_endpoint.id)} if isinstance(connected_endpoint, PowerPort) else None
            )

            # Assert GraphQL returned properties match those expected
            self.assertEqual(entry["connected_power_port"], connected_power_port)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_power_ports_cable_peer(self):
        """Test querying power ports for their cable peers"""

        query = """\
query {
    power_ports {
        id
        cable_peer_power_feed { id }
        cable_peer_power_outlet { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(PowerPort.objects.all()), len(result.data["power_ports"]))
        for entry in result.data["power_ports"]:
            power_port_obj = PowerPort.objects.get(id=entry["id"])
            cable_peer = power_port_obj.get_cable_peer()

            # Extract Expected Properties from CircuitTermination object
            cable_peer_power_feed = {"id": str(cable_peer.id)} if isinstance(cable_peer, PowerFeed) else None
            cable_peer_power_outlet = {"id": str(cable_peer.id)} if isinstance(cable_peer, PowerOutlet) else None

            # Assert GraphQL returned properties match those expected
            self.assertEqual(entry["cable_peer_power_feed"], cable_peer_power_feed)
            self.assertEqual(entry["cable_peer_power_outlet"], cable_peer_power_outlet)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_power_ports_connected_endpoint(self):
        """Test querying power ports for their connected endpoints"""

        query = """\
query {
    power_ports {
        id
        connected_power_feed { id }
        connected_power_outlet { id }
    }
}"""

        result = self.execute_query(query)
        self.assertIsNone(result.errors)
        self.assertEqual(len(PowerPort.objects.all()), len(result.data["power_ports"]))
        for entry in result.data["power_ports"]:
            power_port_obj = PowerPort.objects.get(id=entry["id"])
            connected_endpoint = power_port_obj.connected_endpoint

            # Extract Expected Properties from CircuitTermination object
            connected_power_feed = (
                {"id": str(connected_endpoint.id)} if isinstance(connected_endpoint, PowerFeed) else None
            )
            connected_power_outlet = (
                {"id": str(connected_endpoint.id)} if isinstance(connected_endpoint, PowerOutlet) else None
            )

            # Assert GraphQL returned properties match those expected
            self.assertEqual(entry["connected_power_feed"], connected_power_feed)
            self.assertEqual(entry["connected_power_outlet"], connected_power_outlet)

    def test_query_with_nested_onetoone(self):
        """Test that querying a nested OneToOne field works as expected"""
        query = """
        query ($device_id: ID!) {
            device(id: $device_id) {
                interfaces {
                    ip_addresses {
                        primary_ip4_for {
                            id
                        }
                    }
                }
            }
        }
        """
        # set device1.primary_ip4
        self.device1.primary_ip4 = self.ipaddr1
        self.device1.save()
        result = self.execute_query(query, variables={"device_id": str(self.device1.id)})
        self.assertNotIn("error", str(result))
        expected_interfaces_first = {"ip_addresses": [{"primary_ip4_for": [{"id": str(self.device1.id)}]}]}
        self.assertEqual(result.data["device"]["interfaces"][0], expected_interfaces_first)
