"""N+1 detection for GraphQL nested filtered relations.

Auto-discovers every filterable nested list field in the built GraphQL schema and verifies that
applying a filter does not produce a query-count explosion proportional to the number of parent objects.
"""

import uuid

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.test.client import RequestFactory
import graphene
import graphene.types.definitions
from graphene_django.settings import graphene_settings
from graphql import get_default_backend, execute
from graphql.type import definition


from nautobot.core.testing import AssertNoRepeatedQueries, TestCase

User = get_user_model()


def _unwrap_type(gql_type):
    """Strip NonNull / List wrappers and return (is_list, named_type)."""
    is_list = False
    t = gql_type
    while True:
        if isinstance(t, definition.GraphQLList):
            is_list = True
            t = t.of_type
        elif isinstance(t, definition.GraphQLNonNull):
            t = t.of_type
        else:
            break
    return is_list, t


def _pick_string_filter_arg(gql_field):
    """Return the name of a usable string-type filter arg on *gql_field*, or ``None``.

    Prefers ``name`` because virtually every Nautobot model exposes it as a
    simple string / ``[String]`` filter.
    """
    skip = {"limit", "offset"}
    best = None
    for arg_name, arg in gql_field.args.items():
        if arg_name in skip:
            continue
        _, inner = _unwrap_type(arg.type)
        type_name = getattr(inner, "name", None)
        if type_name != "String":
            continue
        if arg_name == "name":
            return "name"
        if best is None:
            best = arg_name
    return best


def discover_filterable_nested_list_fields(schema):
    """Walk the schema and return ``[(parent_field, nested_field, filter_arg), ...]``.

    Each tuple represents a top-level list query field (e.g. ``devices``) that contains a nested
    list field (e.g. ``interfaces``) accepting at least one string-typed filter argument.
    """
    results = []

    for parent_field in schema.introspect()["__schema"]["types"][0]["fields"]:
        parent_name = parent_field["name"]
        if parent_field["type"]["kind"] == "LIST":
            parent_type = schema.get_type(parent_field["type"]["ofType"]["name"])
        else:
            continue

        for nested_name, nested_field in parent_type.fields.items():
            nested_is_list, nested_named = _unwrap_type(nested_field.type)
            if not nested_is_list:
                continue
            if not isinstance(nested_named, graphene.types.definitions.GrapheneObjectType):
                continue
            if not nested_field.args:
                continue

            filter_arg = _pick_string_filter_arg(nested_field)
            if filter_arg:
                results.append((parent_name, nested_name, filter_arg))

    return results


N_PLUS_ONE_THRESHOLD = 10

# Known N+1 patterns to skip testing for.
KNOWN_N_PLUS_ONE = {
    # TODO: GenericRelation to ObjectMetadata (via BaseModel.associated_object_metadata) causes per-instance
    # lookups when resolving the assigned_object GenericForeignKey back to the concrete model. Fixing requires
    # a custom GraphQL resolver that batches GFK resolution (group by content type, bulk-fetch per type).
    "associated_object_metadata",
    # TODO: GenericRelation to StaticGroupAssociation (via DynamicGroupsModelMixin.static_group_association_set)
    # causes per-instance lookups when resolving the associated_object GenericForeignKey back to the concrete
    # model. Same root cause and fix approach as associated_object_metadata above.
    "static_group_association_set",
}


class GraphQLNPlusOneTest(TestCase):
    """Test that auto-discovers all filterable nested list fields and asserts none produce N+1 queries."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="n_plus_one_test_user", is_active=True, is_superuser=True)

    def setUp(self):
        super().setUp()
        self.schema = graphene_settings.SCHEMA

    def _execute(self, query):
        """Execute a GraphQL query with a **fresh** request context (empty filter cache)."""
        request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        request.id = uuid.uuid4()
        request.user = self.user
        backend = get_default_backend()
        document = backend.document_from_string(self.schema, query)
        return document.execute(context_value=request)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_no_n_plus_one_on_filtered_nested_relations(self):
        """For every nested list field that accepts a string filter, verify no N+1 pattern occurs."""
        cases = discover_filterable_nested_list_fields(self.schema)
        self.assertGreater(len(cases), 0, "Schema introspection found no filterable nested list fields")

        # Filter out known-broken cases (see KNOWN_N_PLUS_ONE for details)
        tested_cases = [(p, n, f) for p, n, f in cases if n not in KNOWN_N_PLUS_ONE]

        self.assertGreater(len(tested_cases), 0, "All cases were skipped as known N+1 patterns")

        # Single prewarm run to populate internal caches (ContentType, Relationship, etc.)
        first_parent, first_nested, first_arg = tested_cases[0]
        self._execute(f'{{ {first_parent} {{ {first_nested}({first_arg}: "{uuid.uuid4()}") {{ id }} }} }}')

        for parent_name, nested_name, filter_arg in tested_cases:
            with self.subTest(parent=parent_name, nested=nested_name, filter=filter_arg):
                query = f'{{ {parent_name} {{ {nested_name}({filter_arg}: "{uuid.uuid4()}") {{ id }} }} }}'

                # Prewarm this specific query path
                self._execute(query)

                # Measured run with fresh request context
                with AssertNoRepeatedQueries(self, threshold=N_PLUS_ONE_THRESHOLD):
                    result = self._execute(query)

                # The query should execute without hard errors (GraphQL filter-validation
                # errors are acceptable since we pass a dummy value).
                if result.errors:
                    for err in result.errors:
                        if not hasattr(err, "original_error") or not isinstance(err.original_error, Exception):
                            if "invalid parameter to prefetch_related" not in str(err):  # graphene-django-optimizer bad
                                self.fail(f"Unexpected hard error for {parent_name}.{nested_name}: {err}")
