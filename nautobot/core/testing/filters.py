import random
import string
from typing import ClassVar, Iterable, Optional

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q, QuerySet
from django.db.models.fields import CharField, TextField
from django.db.models.fields.related import ManyToManyField
from django.db.models.fields.reverse_related import ManyToManyRel, ManyToOneRel
from django.test import tag
from django_filters import FilterSet

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.filters import (
    ContentTypeChoiceFilter,
    ContentTypeFilter,
    ContentTypeMultipleChoiceFilter,
    NaturalKeyOrPKMultipleChoiceFilter,
    RelatedMembershipBooleanFilter,
    SearchFilter,
)
from nautobot.core.models.generics import PrimaryModel
from nautobot.core.testing import views
from nautobot.core.utils.deprecation import class_deprecated_in_favor_of
from nautobot.extras.models import Contact, ContactAssociation, Role, Status, Tag, Team
from nautobot.tenancy import models


@tag("unit")
class FilterTestCases:
    class BaseFilterTestCase(views.TestCase):
        """Base class for testing of FilterSets."""

        queryset: ClassVar[Optional[QuerySet]] = None  # TODO: declared as Optional only to avoid a breaking change

        def get_filterset_test_values(self, field_name, queryset=None):
            """Returns a list of distinct values from the requested queryset field to use in filterset tests.

            Returns a list for use in testing multiple choice filters. The size of the returned list is random
            but will contain at minimum 2 unique values. The list of values will match at least 2 instances when
            passed to the queryset's filter(field_name__in=[]) method but will fail to match at least one instance.

            Args:
                field_name (str): The name of the field to retrieve test values from.
                queryset (QuerySet): The queryset to retrieve test values. Defaults to `self.queryset`.

            Returns:
                (list): A list of unique values derived from the queryset.

            Raises:
                ValueError: Raised if unable to find a combination of 2 or more unique values
                    to filter the queryset to a subset of the total instances.
            """
            test_values = []
            if queryset is None:
                queryset = self.queryset
            qs_count = queryset.count()
            values_with_count = queryset.values(field_name).annotate(count=Count(field_name)).order_by("count")
            for value in values_with_count:
                # randomly break out of loop after 2 values have been selected
                if len(test_values) > 1 and random.choice([True, False]):  # noqa: S311  # suspicious-non-cryptographic-random-usage
                    break
                if value[field_name] and value["count"] < qs_count:
                    qs_count -= value["count"]
                    test_values.append(str(value[field_name]))

            if len(test_values) < 2:
                raise ValueError(
                    f"Cannot find enough valid test data for {queryset.model._meta.object_name} field {field_name} "
                    f"(found {len(test_values)} option(s): {test_values}) but need at least 2 of them"
                )
            return test_values

    class FilterTestCase(BaseFilterTestCase):
        """Add common tests for all FilterSets."""

        filterset: ClassVar[Optional[type[FilterSet]]] = None  # TODO: declared Optional only to avoid breaking change

        # filter predicate fields that should be excluded from q test case
        exclude_q_filter_predicates = []

        # list of filters to be tested by `test_filters_generic`
        # list of iterables with filter name and optional field name
        # example:
        #   generic_filter_tests = [
        #       ["filter1"],
        #       ["filter2", "field2__name"],
        #   ]
        generic_filter_tests: ClassVar[Iterable] = ()

        def setUp(self):
            for attr in ["queryset", "filterset", "generic_filter_tests"]:
                if not hasattr(self, attr):
                    raise NotImplementedError(f'{self} is missing a value for required attribute "{attr}"')
            super().setUp()

        def get_q_filter(self):
            """Helper method to return q filter."""
            self.assertIsNotNone(self.filterset)
            return self.filterset.declared_filters["q"].filter_predicates

        def test_id(self):
            """Verify that the filterset supports filtering by id with only lookup `__n`."""
            self.assertIsNotNone(self.filterset)

            with self.subTest("Assert `id`"):
                params = {"id": list(self.queryset.values_list("pk", flat=True)[:2])}
                expected_queryset = self.queryset.filter(id__in=params["id"])
                filterset = self.filterset(params, self.queryset)  # pylint: disable=not-callable  # see assertion above
                self.assertTrue(filterset.is_valid())
                self.assertQuerysetEqualAndNotEmpty(filterset.qs.order_by("id"), expected_queryset.order_by("id"))

            with self.subTest("Assert negate lookup"):
                params = {"id__n": list(self.queryset.values_list("pk", flat=True)[:2])}
                expected_queryset = self.queryset.exclude(id__in=params["id__n"])
                filterset = self.filterset(params, self.queryset)  # pylint: disable=not-callable  # see assertion above
                self.assertTrue(filterset.is_valid())
                self.assertQuerysetEqualAndNotEmpty(filterset.qs.order_by("id"), expected_queryset.order_by("id"))

            with self.subTest("Assert invalid lookup"):
                params = {"id__in": list(self.queryset.values_list("pk", flat=True)[:2])}
                filterset = self.filterset(params, self.queryset)  # pylint: disable=not-callable  # see assertion above
                self.assertFalse(filterset.is_valid())
                self.assertIn("Unknown filter field", filterset.errors.as_text())

        def test_invalid_filter(self):
            """Verify that the filterset reports as invalid when initialized with an unsupported filter parameter."""
            params = {"ice_cream_flavor": ["chocolate"]}
            self.assertIsNotNone(self.filterset)
            self.assertFalse(self.filterset(params, self.queryset).is_valid())  # pylint: disable=not-callable

        def test_filters_generic(self):
            """Test all multiple choice filters declared in `self.generic_filter_tests`.

            This test uses `get_filterset_test_values()` to retrieve a valid set of test data and asserts
            that the filterset filter output matches the corresponding queryset filter.
            The majority of Nautobot filters use conjoined=False, so the extra logic to support conjoined=True has not
            been implemented here. TagFilter and similar "AND" filters are not supported.

            Examples:
                Multiple tests can be performed for the same filter by adding multiple entries in
                `generic_filter_tests` with explicit field names.
                For example, to test a NaturalKeyOrPKMultipleChoiceFilter, use:
                    generic_filter_tests = (
                        ["filter_name", "field_name__name"],
                        ["filter_name", "field_name__id"],
                    )

                If a field name is not declared, the filter name will be used for the field name:
                    generic_filter_tests = (
                        ["devices"],
                    )
                This expects a field named `devices` on the model and a filter named `devices` on the filterset.
            """
            if not any(test[0] == "id" for test in self.generic_filter_tests):
                self.generic_filter_tests = (["id"], *self.generic_filter_tests)

            if getattr(self.queryset.model, "is_contact_associable_model", False):
                if not any(test[0] == "contacts" for test in self.generic_filter_tests):
                    self.generic_filter_tests = (
                        *self.generic_filter_tests,
                        ["contacts", "associated_contacts__contact__name"],
                        ["contacts", "associated_contacts__contact__id"],
                    )
                if not any(test[0] == "teams" for test in self.generic_filter_tests):
                    self.generic_filter_tests = (
                        *self.generic_filter_tests,
                        ["teams", "associated_contacts__team__name"],
                        ["teams", "associated_contacts__team__id"],
                    )

                # Make sure we have at least 3 contacts and 3 teams in the database
                if Contact.objects.count() < 3:
                    Contact.objects.create(name="Generic Filter Test Contact 1")
                    Contact.objects.create(name="Generic Filter Test Contact 2")
                    Contact.objects.create(name="Generic Filter Test Contact 3")

                if Team.objects.count() < 3:
                    Team.objects.create(name="Generic Filter Test Team 1")
                    Team.objects.create(name="Generic Filter Test Team 2")
                    Team.objects.create(name="Generic Filter Test Team 3")

                # Make sure we have some valid contact-associations:
                for contact, team, instance in zip(Contact.objects.all()[:3], Team.objects.all()[:3], self.queryset):
                    ContactAssociation.objects.create(
                        contact=contact,
                        associated_object=instance,
                        role=Role.objects.get_for_model(ContactAssociation).first(),
                        status=Status.objects.get_for_model(ContactAssociation).first(),
                    )
                    ContactAssociation.objects.create(
                        team=team,
                        associated_object=instance,
                        role=Role.objects.get_for_model(ContactAssociation).last(),
                        status=Status.objects.get_for_model(ContactAssociation).last(),
                    )

            if self.generic_filter_tests:
                self.assertIsNotNone(self.filterset)

            for test in self.generic_filter_tests:
                filter_name = test[0]
                field_name = test[-1]  # default to filter_name if a second list item was not supplied
                with self.subTest(f"{self.filterset.__name__} filter {filter_name} ({field_name})"):
                    test_data = self.get_filterset_test_values(field_name)
                    params = {filter_name: test_data}
                    filterset_result = self.filterset(params, self.queryset).qs  # pylint: disable=not-callable
                    qs_result = self.queryset.filter(**{f"{field_name}__in": test_data}).distinct()
                    self.assertQuerysetEqualAndNotEmpty(filterset_result, qs_result, ordered=False)

        def test_automagic_filters(self):
            """https://github.com/nautobot/nautobot/issues/6656"""
            self.assertIsNotNone(self.filterset)
            fs = self.filterset()  # pylint: disable=not-callable
            if getattr(self.queryset.model, "is_contact_associable_model", False):
                self.assertIsInstance(fs.filters["contacts"], NaturalKeyOrPKMultipleChoiceFilter)
                self.assertIsInstance(fs.filters["contacts__n"], NaturalKeyOrPKMultipleChoiceFilter)
                self.assertIsInstance(fs.filters["teams"], NaturalKeyOrPKMultipleChoiceFilter)
                self.assertIsInstance(fs.filters["teams__n"], NaturalKeyOrPKMultipleChoiceFilter)

            if getattr(self.queryset.model, "is_dynamic_group_associable_model", False):
                self.assertIsInstance(fs.filters["dynamic_groups"], NaturalKeyOrPKMultipleChoiceFilter)
                self.assertIsInstance(fs.filters["dynamic_groups__n"], NaturalKeyOrPKMultipleChoiceFilter)

        def test_boolean_filters_generic(self):
            """Test all `RelatedMembershipBooleanFilter` filters found in `self.filterset.filters`
            except for the ones with custom filter logic defined in its `method` attribute.

            This test asserts that `filter=True` matches `self.queryset.filter(field__isnull=False)` and
            that `filter=False` matches `self.queryset.filter(field__isnull=True)`.
            """
            self.assertIsNotNone(self.filterset)
            for filter_name, filter_object in self.filterset().filters.items():  # pylint: disable=not-callable
                if not isinstance(filter_object, RelatedMembershipBooleanFilter):
                    continue
                if filter_object.method is not None:
                    continue
                field_name = filter_object.field_name
                with self.subTest(f"{self.filterset.__name__} RelatedMembershipBooleanFilter {filter_name} (True)"):
                    filterset_result = self.filterset({filter_name: True}, self.queryset).qs  # pylint: disable=not-callable
                    qs_result = self.queryset.filter(**{f"{field_name}__isnull": filter_object.exclude}).distinct()
                    self.assertQuerysetEqualAndNotEmpty(filterset_result, qs_result)
                with self.subTest(f"{self.filterset.__name__} RelatedMembershipBooleanFilter {filter_name} (False)"):
                    filterset_result = self.filterset({filter_name: False}, self.queryset).qs  # pylint: disable=not-callable
                    qs_result = self.queryset.exclude(**{f"{field_name}__isnull": filter_object.exclude}).distinct()
                    self.assertQuerysetEqualAndNotEmpty(filterset_result, qs_result)

        def test_tags_filter(self):
            """Test the `tags` filter which should be present on all PrimaryModel filtersets."""
            if not issubclass(self.queryset.model, PrimaryModel):
                self.skipTest("Not a PrimaryModel")

            self.assertIsNotNone(self.filterset)

            # Find an instance with at least two tags (should be common given our factory design)
            for instance in list(self.queryset):
                if len(instance.tags.all()) >= 2:
                    tags = list(instance.tags.all()[:2])
                    break

            # Otherwise, create some tags and apply to an instance for this test
            else:
                model_ct = ContentType.objects.get_for_model(self.queryset.model)
                test_tags_filter_a = Tag.objects.get_or_create(name="test tags filter a")[0]
                test_tags_filter_a.content_types.add(model_ct)
                test_tags_filter_b = Tag.objects.get_or_create(name="test tags filter b")[0]
                test_tags_filter_b.content_types.add(model_ct)
                self.queryset.first().tags.add(test_tags_filter_a, test_tags_filter_b)
                tags = [test_tags_filter_a, test_tags_filter_b]
            params = {"tags": [tags[0].name, tags[1].pk]}
            filterset_result = self.filterset(params, self.queryset).qs  # pylint: disable=not-callable
            # Tags is an AND filter not an OR filter
            qs_result = self.queryset.filter(tags=tags[0]).filter(tags=tags[1]).distinct()
            self.assertQuerysetEqualAndNotEmpty(filterset_result, qs_result)

        def _assert_valid_filter_predicates(self, obj, field_name):
            self.assertTrue(
                hasattr(obj, field_name),
                f"`{field_name}` is an Invalid `q` filter predicate for `{self.filterset.__name__}`",
            )

        def _get_nested_related_obj_and_its_field_name(self, obj, model_field_name):
            """
            Get the nested related object and its field name.

            Args:
                obj: The object to extract the related object from.
                model_field_name: The field name containing the related object.

            Examples:
                >>> _get_nested_related_obj_and_its_field_name(<RelationshipAssociation: One>, "relationship__label")
                (<Relationship: RelationshipExample>, "label")
                >>> _get_nested_related_obj_and_its_field_name(<Device: DeviceOne>, "rack__rack_group__name")
                (<RackGroup: RackGroupExample>, "name")

            Returns:
                Tuple: A tuple containing the related object and its field name.
            """
            rel_obj = obj
            rel_obj_field_name = model_field_name
            while "__" in rel_obj_field_name:
                filter_field_name, rel_obj_field_name = rel_obj_field_name.split("__", 1)
                field = rel_obj._meta.get_field(filter_field_name)
                if isinstance(field, (ManyToOneRel, ManyToManyRel, ManyToManyField)):
                    rel_obj = getattr(rel_obj, filter_field_name).first()
                else:
                    rel_obj = getattr(rel_obj, filter_field_name)
            return rel_obj, rel_obj_field_name

        def _assert_q_filter_predicate_validity(self, obj, obj_field_name, filter_field_name, lookup_method):
            """
            Assert the validity of a `q` filter predicate.

            Args:
                obj: The object to filter.
                obj_field_name: The field name of the object to filter.
                filter_field_name: The field name of the FilterSet q filter predicate to test.
                lookup_method: The method used for the lookup e.g icontains.
            """
            self._assert_valid_filter_predicates(obj, obj_field_name)

            self.assertIsNotNone(self.filterset)

            # Generic test only supports CharField or TextFields, skip all other types
            obj_field = obj._meta.get_field(obj_field_name)
            if not isinstance(obj_field, (CharField, TextField)):
                self.skipTest("Not a CharField or TextField")

            # Create random lowercase string to use for icontains lookup
            max_length = obj_field.max_length or CHARFIELD_MAX_LENGTH
            randomized_attr_value = "".join(random.choices(string.ascii_lowercase, k=max_length))  # noqa: S311 # pseudo-random generator
            setattr(obj, obj_field_name, randomized_attr_value)
            obj.save()

            # if lookup_method is iexact use the full updated attr
            if lookup_method == "iexact":
                lookup = randomized_attr_value.upper()
                model_queryset = self.queryset.filter(**{f"{filter_field_name}__iexact": lookup})
            else:
                lookup = randomized_attr_value[1:].upper()
                model_queryset = self.queryset.filter(**{f"{filter_field_name}__icontains": lookup})
            params = {"q": lookup}
            filterset_result = self.filterset(params, self.queryset)  # pylint: disable=not-callable

            self.assertTrue(filterset_result.is_valid())
            self.assertQuerysetEqualAndNotEmpty(
                filterset_result.qs,
                model_queryset,
                ordered=False,
                msg=lookup,
            )

        def _get_relevant_filterset_queryset(self, queryset, *filter_params):
            """Gets the relevant queryset based on filter parameters."""

            q_query = Q()
            for param in filter_params:
                q_query &= Q(**{f"{param}__isnull": False})
            queryset = queryset.filter(q_query)

            if not queryset.count():
                raise ValueError(
                    f"Cannot find valid test data for {queryset.model.__name__} with params {filter_params}"
                )
            return queryset

        def test_q_filter_valid(self):
            """Test the `q` filter based on attributes in `filter_predicates`."""
            if not self.filterset.declared_filters.get("q"):
                raise ValueError("`q` filter not implemented")

            if not isinstance(self.filterset.declared_filters.get("q"), SearchFilter):
                # Some FilterSets like IPAddress,Prefix etc might implement a custom `q` filtering
                self.skipTest("`q` filter is not a SearchFilter")

            for filter_field_name, lookup_method in self.get_q_filter().items():
                should_skip_test = (
                    (lookup_method not in ["icontains", "iexact"])  # only testing icontains and iexact filter lookups
                    or (
                        filter_field_name == "id"
                    )  # Ignore `id` because `SearchFilter` always dynamically includes `id: exact` predicate, only testing on user input `filter_predicates`
                    or (filter_field_name in self.exclude_q_filter_predicates)
                )
                if should_skip_test:
                    continue
                with self.subTest(f"Asserting '{filter_field_name}' `q` filter predicates"):
                    queryset = self._get_relevant_filterset_queryset(self.queryset, filter_field_name)
                    obj = queryset.first()
                    obj_field_name = filter_field_name

                    is_nested_filter_name = "__" in filter_field_name

                    if is_nested_filter_name:
                        obj, obj_field_name = self._get_nested_related_obj_and_its_field_name(obj, obj_field_name)
                    self._assert_q_filter_predicate_validity(obj, obj_field_name, filter_field_name, lookup_method)

        def test_content_type_related_fields_uses_content_type_filter(self):
            self.assertIsNotNone(self.filterset)
            fs = self.filterset()  # pylint: disable=not-callable
            for field in self.queryset.model._meta.fields:
                related_model = getattr(field, "related_model", None)
                if not related_model or related_model != ContentType:
                    continue
                with self.subTest(
                    f"Assert {self.filterset.__class__.__name__}.{field.name} implements ContentTypeFilter"
                ):
                    filter_field = fs.filters.get(field.name)
                    if not filter_field:
                        # This field is not part of the Filterset.
                        continue
                    self.assertIsInstance(
                        filter_field, (ContentTypeFilter, ContentTypeMultipleChoiceFilter, ContentTypeChoiceFilter)
                    )

    # Test cases should just explicitly include `name` as a generic_filter_tests entry
    @class_deprecated_in_favor_of(FilterTestCase)  # pylint: disable=undefined-variable
    class NameOnlyFilterTestCase(FilterTestCase):
        """Add simple tests for filtering by name."""

        def test_filters_generic(self):
            if not any(test[0] == "name" for test in self.generic_filter_tests):
                self.generic_filter_tests = (["name"], *self.generic_filter_tests)
            super().test_filters_generic()

    # Test cases should just explicitly include `name` and `slug` as generic_filter_tests entries
    @class_deprecated_in_favor_of(FilterTestCase)  # pylint: disable=undefined-variable
    class NameSlugFilterTestCase(FilterTestCase):
        """Add simple tests for filtering by name and by slug."""

        def test_filters_generic(self):
            if not any(test[0] == "slug" for test in self.generic_filter_tests):
                self.generic_filter_tests = (["slug"], *self.generic_filter_tests)
            if not any(test[0] == "name" for test in self.generic_filter_tests):
                self.generic_filter_tests = (["name"], *self.generic_filter_tests)
            super().test_filters_generic()

    class TenancyFilterTestCaseMixin(views.TestCase):
        """Add test cases for tenant and tenant-group filters."""

        tenancy_related_name = ""

        def test_tenant(self):
            tenants = list(models.Tenant.objects.filter(**{f"{self.tenancy_related_name}__isnull": False}))[:2]
            params = {"tenant_id": [tenants[0].pk, tenants[1].pk]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs, self.queryset.filter(tenant__in=tenants), ordered=False
            )
            params = {"tenant": [tenants[0].name, tenants[1].name]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs, self.queryset.filter(tenant__in=tenants), ordered=False
            )

        def test_tenant_group(self):
            tenant_groups = list(
                models.TenantGroup.objects.filter(
                    tenants__isnull=False, **{f"tenants__{self.tenancy_related_name}__isnull": False}
                )
            )[:2]
            tenant_groups_including_children = []
            for tenant_group in tenant_groups:
                tenant_groups_including_children += tenant_group.descendants(include_self=True)

            params = {"tenant_group": [tenant_groups[0].pk, tenant_groups[1].pk]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(tenant__tenant_group__in=tenant_groups_including_children),
                ordered=False,
            )

            params = {"tenant_group": [tenant_groups[0].name, tenant_groups[1].name]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(tenant__tenant_group__in=tenant_groups_including_children),
                ordered=False,
            )
