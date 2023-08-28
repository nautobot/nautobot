from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models as django_models
from django.shortcuts import reverse
from django.test import TestCase
from django.test.utils import isolate_apps

import django_filters
from tree_queries.models import TreeNodeForeignKey

from nautobot.core import filters, testing
from nautobot.core.models import fields as core_fields
from nautobot.core.utils import lookup
from nautobot.dcim import choices as dcim_choices
from nautobot.dcim import filters as dcim_filters
from nautobot.dcim import models as dcim_models
from nautobot.dcim.models import Device
from nautobot.extras import models as extras_models
from nautobot.extras.utils import FeatureQuery
from nautobot.ipam import factory as ipam_factory
from nautobot.ipam import models as ipam_models


class TreeNodeMultipleChoiceFilterTest(TestCase):
    class LocationFilterSet(filters.BaseFilterSet):
        parent = filters.TreeNodeMultipleChoiceFilter(queryset=dcim_models.Location.objects.all())

        class Meta:
            model = dcim_models.Location
            fields = []

    def setUp(self):
        super().setUp()

        self.location_type = dcim_models.LocationType.objects.get(name="Campus")
        status = extras_models.Status.objects.get_for_model(dcim_models.Location).first()
        self.parent_location_1 = dcim_models.Location.objects.create(
            name="Test Parent Location 1",
            location_type=self.location_type,
            status=status,
        )
        self.parent_location_2 = dcim_models.Location.objects.create(
            name="Test Parent Location 2",
            location_type=self.location_type,
            status=status,
        )
        self.parent_location_2a = dcim_models.Location.objects.create(
            name="Test Parent Location 2A",
            parent=self.parent_location_2,
            location_type=self.location_type,
            status=status,
        )
        self.parent_location_2ab = dcim_models.Location.objects.create(
            name="Test Parent Location 2A-B",
            parent=self.parent_location_2a,
            location_type=self.location_type,
            status=status,
        )
        self.child_location_1 = dcim_models.Location.objects.create(
            parent=self.parent_location_1,
            name="Test Child Location 1",
            location_type=self.location_type,
            status=status,
        )
        self.child_location_2 = dcim_models.Location.objects.create(
            parent=self.parent_location_2,
            name="Test Child Location 2",
            location_type=self.location_type,
            status=status,
        )
        self.child_location_2a = dcim_models.Location.objects.create(
            parent=self.parent_location_2a,
            name="Test Child Location 2a",
            location_type=self.location_type,
            status=status,
        )
        self.child_location_2ab = dcim_models.Location.objects.create(
            parent=self.parent_location_2ab,
            name="Test Child Location 2a-b",
            location_type=self.location_type,
            status=status,
        )
        self.child_location_0 = dcim_models.Location.objects.create(
            parent=None,
            name="Test Child Location 0",
            location_type=self.location_type,
            status=status,
        )
        # To ensure child objects with parents of the same name are not included in the results for filtering,
        # we create parents with the same name under different ancestors.
        self.parent_location_same_name_1 = dcim_models.Location.objects.create(
            parent=self.child_location_1,
            name="Test Parent Location Same Name",
            location_type=self.location_type,
            status=status,
        )
        self.parent_location_same_name_2 = dcim_models.Location.objects.create(
            parent=self.child_location_2ab,
            name="Test Parent Location Same Name",
            location_type=self.location_type,
            status=status,
        )
        self.child_location_same_name_1 = dcim_models.Location.objects.create(
            parent=self.parent_location_same_name_1,
            name="Test Child Location Same Name Parent 1",
            location_type=self.location_type,
            status=status,
        )
        self.child_location_same_name_2 = dcim_models.Location.objects.create(
            parent=self.parent_location_same_name_2,
            name="Test Child Location Same Name Parent 2",
            location_type=self.location_type,
            status=status,
        )
        self.queryset = dcim_models.Location.objects.filter(name__icontains="Test Child Location")

    def test_filter_single_name(self):
        kwargs = {"parent": [self.parent_location_1.name]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.child_location_1, self.child_location_same_name_1])

    def test_filter_single_pk(self):
        kwargs = {"parent": [self.parent_location_1.pk]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.child_location_1, self.child_location_same_name_1])

    def test_filter_multiple_name(self):
        kwargs = {"parent": [self.parent_location_1.name, self.parent_location_2.name]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(
            qs,
            [
                self.child_location_1,
                self.child_location_same_name_1,
                self.child_location_2,
                self.child_location_2a,
                self.child_location_2ab,
                self.child_location_same_name_2,
            ],
        )

    def test_filter_null(self):
        kwargs = {"parent": [settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.child_location_0])

    def test_filter_combined_name(self):
        kwargs = {"parent": [self.parent_location_1.name, settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.child_location_0, self.child_location_1, self.child_location_same_name_1])

    def test_filter_combined_pk(self):
        kwargs = {"parent": [self.parent_location_2.pk, settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(
            qs,
            [
                self.child_location_0,
                self.child_location_2,
                self.child_location_2a,
                self.child_location_2ab,
                self.child_location_same_name_2,
            ],
        )

    def test_filter_single_name_exclude(self):
        kwargs = {"parent__n": [self.parent_location_1.name]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(
            qs,
            [
                self.child_location_0,
                self.child_location_2,
                self.child_location_2a,
                self.child_location_2ab,
                self.child_location_same_name_2,
            ],
        )

    def test_filter_single_pk_exclude(self):
        kwargs = {"parent__n": [self.parent_location_2.pk]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.child_location_0, self.child_location_1, self.child_location_same_name_1])

    def test_filter_multiple_name_exclude(self):
        kwargs = {"parent__n": [self.parent_location_1.name, self.parent_location_2.name]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.child_location_0])

    def test_filter_null_exclude(self):
        kwargs = {"parent__n": [settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(
            qs,
            [
                self.child_location_1,
                self.child_location_same_name_1,
                self.child_location_2,
                self.child_location_2a,
                self.child_location_2ab,
                self.child_location_same_name_2,
            ],
        )

    def test_filter_combined_name_exclude(self):
        kwargs = {"parent__n": [self.parent_location_1.name, settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(
            qs,
            [self.child_location_2, self.child_location_2a, self.child_location_2ab, self.child_location_same_name_2],
        )

    def test_filter_combined_pk_exclude(self):
        kwargs = {"parent__n": [self.parent_location_2.pk, settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.child_location_1, self.child_location_same_name_1])

    def test_lookup_expr_param_ignored(self):
        """
        Test that the `lookup_expr` parameter is ignored when using this filter on filtersets.
        """
        # Since we deprecated `in` this should be ignored.
        f = filters.TreeNodeMultipleChoiceFilter(queryset=dcim_models.Location.objects.all(), lookup_expr="in")
        self.assertEqual(f.lookup_expr, django_filters.conf.settings.DEFAULT_LOOKUP_EXPR)


class NaturalKeyOrPKMultipleChoiceFilterTest(TestCase, testing.NautobotTestCaseMixin):
    class LocationFilterSet(filters.BaseFilterSet):
        power_panels = filters.NaturalKeyOrPKMultipleChoiceFilter(
            field_name="power_panels",
            queryset=dcim_models.PowerPanel.objects.all(),
            to_field_name="name",
        )

        class Meta:
            model = dcim_models.Location
            fields = []

    queryset = dcim_models.Location.objects.all()
    filterset = LocationFilterSet

    def setUp(self):
        super().setUp()
        self.location_types = dcim_models.LocationType.objects.filter(
            content_types__in=ContentType.objects.filter(FeatureQuery("locations").get_query())
        )
        self.locations = dcim_models.Location.objects.filter(location_type__in=self.location_types)[:3]

        self.power_panel1 = dcim_models.PowerPanel.objects.create(location=self.locations[0], name="test-power-panel1")
        self.power_panel2 = dcim_models.PowerPanel.objects.create(location=self.locations[1], name="test-power-panel2")
        self.power_panel2a = dcim_models.PowerPanel.objects.create(
            location=self.locations[1], name="test-power-panel2a"
        )
        self.power_panel2b = dcim_models.PowerPanel.objects.create(
            location=self.locations[1], name="test-power-panel2b"
        )
        self.power_panel3 = dcim_models.PowerPanel.objects.create(location=self.locations[0], name="test-power-panel3")
        self.power_panel3a = dcim_models.PowerPanel.objects.create(location=self.locations[1], name="test-power-panel3")

    def test_filter_single_name(self):
        kwargs = {"power_panels": ["test-power-panel1"]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqualAndNotEmpty(qs, [self.locations[0]])

    def test_filter_single_pk(self):
        kwargs = {"power_panels": [self.power_panel1.pk]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqualAndNotEmpty(qs, [self.locations[0]])

    def test_filter_multiple_name(self):
        kwargs = {"power_panels": ["test-power-panel1", "test-power-panel2"]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqualAndNotEmpty(qs, [self.locations[0], self.locations[1]])

    def test_filter_duplicate_name(self):
        kwargs = {"power_panels": ["test-power-panel3"]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqualAndNotEmpty(qs, [self.locations[0], self.locations[1]])

    def test_filter_null(self):
        kwargs = {"power_panels": [settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs
        expected_result = dcim_models.Location.objects.filter(power_panels__isnull=True)

        self.assertQuerysetEqualAndNotEmpty(qs, expected_result)

    def test_filter_combined_name(self):
        kwargs = {"power_panels": ["test-power-panel1", settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs
        expected_result = dcim_models.Location.objects.filter(
            power_panels__isnull=True
        ) | dcim_models.Location.objects.filter(power_panels__name__in=["test-power-panel1"])

        self.assertQuerysetEqualAndNotEmpty(qs, expected_result)

    def test_filter_combined_pk(self):
        kwargs = {"power_panels": [self.power_panel2.pk, settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs
        expected_result = dcim_models.Location.objects.filter(
            power_panels__isnull=True
        ) | dcim_models.Location.objects.filter(power_panels__pk__in=[self.power_panel2.pk])

        self.assertQuerysetEqualAndNotEmpty(qs, expected_result)

    def test_filter_single_name_exclude(self):
        kwargs = {"power_panels__n": ["test-power-panel1"]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs
        expected_result = dcim_models.Location.objects.exclude(power_panels__name__in=["test-power-panel1"])

        self.assertQuerysetEqualAndNotEmpty(qs, expected_result)

    def test_filter_single_pk_exclude(self):
        kwargs = {"power_panels__n": [self.power_panel2.pk]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs
        expected_result = dcim_models.Location.objects.exclude(power_panels__pk__in=[self.power_panel2.pk])

        self.assertQuerysetEqualAndNotEmpty(qs, expected_result)

    def test_filter_multiple_name_exclude(self):
        kwargs = {"power_panels__n": ["test-power-panel1", "test-power-panel2"]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs
        expected_result = dcim_models.Location.objects.exclude(power_panels__name__in=["test-power-panel1"]).exclude(
            power_panels__name__in=["test-power-panel2"]
        )

        self.assertQuerysetEqualAndNotEmpty(qs, expected_result)

    def test_filter_duplicate_name_exclude(self):
        kwargs = {"power_panels__n": ["test-power-panel3"]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs
        expected_result = dcim_models.Location.objects.exclude(power_panels__name__in=["test-power-panel3"])

        self.assertQuerysetEqualAndNotEmpty(qs, expected_result)

    def test_filter_null_exclude(self):
        kwargs = {"power_panels__n": [settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqualAndNotEmpty(qs, [self.locations[0], self.locations[1]])

    def test_filter_combined_name_exclude(self):
        kwargs = {"power_panels__n": ["test-power-panel1", settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqualAndNotEmpty(qs, [self.locations[1]])

    def test_filter_combined_pk_exclude(self):
        kwargs = {"power_panels__n": [self.power_panel2.pk, settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.LocationFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqualAndNotEmpty(qs, [self.locations[0]])

    def test_get_filter_predicate(self):
        """
        Test that `get_filter_predicate()` has hybrid results depending on whether value is a UUID or a name.
        """

        # Test UUID (pk)
        uuid_obj = self.power_panel1.pk
        kwargs = {"power_panels": [uuid_obj]}
        fs = self.LocationFilterSet(kwargs, self.queryset)
        self.assertQuerysetEqualAndNotEmpty(fs.qs, [self.locations[0]])
        self.assertEqual(
            fs.filters["power_panels"].get_filter_predicate(uuid_obj),
            {"power_panels": str(uuid_obj)},
        )

        # Test model instance (pk)
        instance = self.power_panel1
        kwargs = {"power_panels": [instance]}
        fs = self.LocationFilterSet(kwargs, self.queryset)
        self.assertQuerysetEqualAndNotEmpty(fs.qs, [self.locations[0]])
        self.assertEqual(
            fs.filters["power_panels"].get_filter_predicate(instance),
            {"power_panels": str(instance.pk)},
        )

        # Test string (name in this case)
        name = self.power_panel1.name
        kwargs = {"power_panels": [name]}
        fs = self.LocationFilterSet(kwargs, self.queryset)
        self.assertQuerysetEqualAndNotEmpty(fs.qs, [self.locations[0]])
        self.assertEqual(
            fs.filters["power_panels"].get_filter_predicate(name),
            {"power_panels__name": name},
        )


@isolate_apps("nautobot.core.tests")
class BaseFilterSetTest(TestCase):
    """
    Ensure that a BaseFilterSet automatically creates the expected set of filters for each filter type.
    """

    class TestFilterSet(filters.BaseFilterSet):
        """Filterset for testing various fields."""

        class TestModel(django_models.Model):
            """
            Test model used by BaseFilterSetTest for filter validation. Should never appear in a schema migration.
            """

            charfield = django_models.CharField(max_length=10)
            choicefield = django_models.IntegerField(choices=(("A", 1), ("B", 2), ("C", 3)))
            charchoicefield = django_models.CharField(
                choices=(("1", "Option 1"), ("2", "Option 2"), ("3", "Option 3")), max_length=10
            )
            datefield = django_models.DateField()
            datetimefield = django_models.DateTimeField()
            decimalfield = django_models.DecimalField(max_digits=9, decimal_places=6)
            floatfield = django_models.FloatField()
            integerfield = django_models.IntegerField()
            macaddressfield = core_fields.MACAddressCharField()
            textfield = django_models.TextField()
            timefield = django_models.TimeField()
            treeforeignkeyfield = TreeNodeForeignKey(to="self", on_delete=django_models.CASCADE)

            tags = core_fields.TagsField()

        charfield = django_filters.CharFilter()
        macaddressfield = filters.MACAddressFilter()
        modelchoicefield = django_filters.ModelChoiceFilter(
            field_name="integerfield",  # We're pretending this is a ForeignKey field
            queryset=dcim_models.Location.objects.all(),
        )
        modelmultiplechoicefield = django_filters.ModelMultipleChoiceFilter(
            field_name="integerfield",  # We're pretending this is a ForeignKey field
            queryset=dcim_models.Location.objects.all(),
        )
        multiplechoicefield = django_filters.MultipleChoiceFilter(field_name="choicefield")
        multivaluecharfield = filters.MultiValueCharFilter(field_name="charfield")
        treeforeignkeyfield = filters.TreeNodeMultipleChoiceFilter(queryset=TestModel.objects.all())

        # declared this way because `class Meta: model = TestModel` gives a NameError otherwise.
        Meta = type(
            "Meta",
            (),
            {
                "model": TestModel,
                "fields": (
                    "charfield",
                    "choicefield",
                    "charchoicefield",
                    "datefield",
                    "datetimefield",
                    "decimalfield",
                    "floatfield",
                    "integerfield",
                    "macaddressfield",
                    "modelchoicefield",
                    "modelmultiplechoicefield",
                    "multiplechoicefield",
                    "tags",
                    "textfield",
                    "timefield",
                    "treeforeignkeyfield",
                ),
            },
        )

    @classmethod
    def setUpTestData(cls):
        cls.filters = cls.TestFilterSet().filters

    def test_generated_lookup_expression_filters(self):
        """
        Tests to ensure the internal helper method expands a CharFilter out to all natural lookup expressions.

        Used by declared filters expansion and adding new filters.
        """
        magic_lookups = self.TestFilterSet._generate_lookup_expression_filters(
            "magic_charfield", django_filters.CharFilter(field_name="charfield")
        )

        self.assertEqual(magic_lookups["magic_charfield__n"].lookup_expr, "exact")
        self.assertEqual(magic_lookups["magic_charfield__n"].exclude, True)
        self.assertEqual(magic_lookups["magic_charfield__ie"].lookup_expr, "iexact")
        self.assertEqual(magic_lookups["magic_charfield__ie"].exclude, False)
        self.assertEqual(magic_lookups["magic_charfield__nie"].lookup_expr, "iexact")
        self.assertEqual(magic_lookups["magic_charfield__nie"].exclude, True)
        self.assertEqual(magic_lookups["magic_charfield__ic"].lookup_expr, "icontains")
        self.assertEqual(magic_lookups["magic_charfield__ic"].exclude, False)
        self.assertEqual(magic_lookups["magic_charfield__nic"].lookup_expr, "icontains")
        self.assertEqual(magic_lookups["magic_charfield__nic"].exclude, True)
        self.assertEqual(magic_lookups["magic_charfield__isw"].lookup_expr, "istartswith")
        self.assertEqual(magic_lookups["magic_charfield__isw"].exclude, False)
        self.assertEqual(magic_lookups["magic_charfield__nisw"].lookup_expr, "istartswith")
        self.assertEqual(magic_lookups["magic_charfield__nisw"].exclude, True)
        self.assertEqual(magic_lookups["magic_charfield__iew"].lookup_expr, "iendswith")
        self.assertEqual(magic_lookups["magic_charfield__iew"].exclude, False)
        self.assertEqual(magic_lookups["magic_charfield__niew"].lookup_expr, "iendswith")
        self.assertEqual(magic_lookups["magic_charfield__niew"].exclude, True)
        self.assertEqual(magic_lookups["magic_charfield__re"].lookup_expr, "regex")
        self.assertEqual(magic_lookups["magic_charfield__re"].exclude, False)
        self.assertEqual(magic_lookups["magic_charfield__nre"].lookup_expr, "regex")
        self.assertEqual(magic_lookups["magic_charfield__nre"].exclude, True)
        self.assertEqual(magic_lookups["magic_charfield__ire"].lookup_expr, "iregex")
        self.assertEqual(magic_lookups["magic_charfield__ire"].exclude, False)
        self.assertEqual(magic_lookups["magic_charfield__nire"].lookup_expr, "iregex")
        self.assertEqual(magic_lookups["magic_charfield__nire"].exclude, True)

    def test_add_filter_field(self):
        """
        Testing to ensure add_filter method adds provided filter to resulting list as well as automagic expanded lookup expressions.
        """
        new_filter_set_field_name = "tacos"
        new_filter_set_field = django_filters.CharFilter(field_name="charfield")

        self.assertNotIn("tacos", self.TestFilterSet().filters.keys())

        self.TestFilterSet.add_filter(new_filter_name=new_filter_set_field_name, new_filter_field=new_filter_set_field)

        new_filter_keys = self.TestFilterSet().filters.keys()
        self.assertIn("tacos", new_filter_keys)
        self.assertIn("tacos__n", new_filter_keys)
        self.assertIn("tacos__ie", new_filter_keys)

        with self.assertRaises(TypeError):
            self.TestFilterSet.add_filter(new_filter_name="tacos", new_filter_field=None)

        with self.assertRaises(AttributeError):
            self.TestFilterSet.add_filter(new_filter_name="charfield", new_filter_field=new_filter_set_field)

    def test_char_filter(self):
        self.assertIsInstance(self.filters["charfield"], django_filters.CharFilter)
        self.assertEqual(self.filters["charfield"].lookup_expr, "exact")
        self.assertEqual(self.filters["charfield"].exclude, False)
        self.assertEqual(self.filters["charfield__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["charfield__n"].exclude, True)
        self.assertEqual(self.filters["charfield__ie"].lookup_expr, "iexact")
        self.assertEqual(self.filters["charfield__ie"].exclude, False)
        self.assertEqual(self.filters["charfield__nie"].lookup_expr, "iexact")
        self.assertEqual(self.filters["charfield__nie"].exclude, True)
        self.assertEqual(self.filters["charfield__ic"].lookup_expr, "icontains")
        self.assertEqual(self.filters["charfield__ic"].exclude, False)
        self.assertEqual(self.filters["charfield__nic"].lookup_expr, "icontains")
        self.assertEqual(self.filters["charfield__nic"].exclude, True)
        self.assertEqual(self.filters["charfield__isw"].lookup_expr, "istartswith")
        self.assertEqual(self.filters["charfield__isw"].exclude, False)
        self.assertEqual(self.filters["charfield__nisw"].lookup_expr, "istartswith")
        self.assertEqual(self.filters["charfield__nisw"].exclude, True)
        self.assertEqual(self.filters["charfield__iew"].lookup_expr, "iendswith")
        self.assertEqual(self.filters["charfield__iew"].exclude, False)
        self.assertEqual(self.filters["charfield__niew"].lookup_expr, "iendswith")
        self.assertEqual(self.filters["charfield__niew"].exclude, True)
        self.assertEqual(self.filters["charfield__re"].lookup_expr, "regex")
        self.assertEqual(self.filters["charfield__re"].exclude, False)
        self.assertEqual(self.filters["charfield__nre"].lookup_expr, "regex")
        self.assertEqual(self.filters["charfield__nre"].exclude, True)
        self.assertEqual(self.filters["charfield__ire"].lookup_expr, "iregex")
        self.assertEqual(self.filters["charfield__ire"].exclude, False)
        self.assertEqual(self.filters["charfield__nire"].lookup_expr, "iregex")
        self.assertEqual(self.filters["charfield__nire"].exclude, True)

    def test_mac_address_filter(self):
        self.assertIsInstance(self.filters["macaddressfield"], filters.MACAddressFilter)
        self.assertEqual(self.filters["macaddressfield"].lookup_expr, "exact")
        self.assertEqual(self.filters["macaddressfield"].exclude, False)
        self.assertEqual(self.filters["macaddressfield__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["macaddressfield__n"].exclude, True)
        self.assertEqual(self.filters["macaddressfield__ie"].lookup_expr, "iexact")
        self.assertEqual(self.filters["macaddressfield__ie"].exclude, False)
        self.assertEqual(self.filters["macaddressfield__nie"].lookup_expr, "iexact")
        self.assertEqual(self.filters["macaddressfield__nie"].exclude, True)
        self.assertEqual(self.filters["macaddressfield__ic"].lookup_expr, "icontains")
        self.assertEqual(self.filters["macaddressfield__ic"].exclude, False)
        self.assertEqual(self.filters["macaddressfield__nic"].lookup_expr, "icontains")
        self.assertEqual(self.filters["macaddressfield__nic"].exclude, True)
        self.assertEqual(self.filters["macaddressfield__isw"].lookup_expr, "istartswith")
        self.assertEqual(self.filters["macaddressfield__isw"].exclude, False)
        self.assertEqual(self.filters["macaddressfield__nisw"].lookup_expr, "istartswith")
        self.assertEqual(self.filters["macaddressfield__nisw"].exclude, True)
        self.assertEqual(self.filters["macaddressfield__iew"].lookup_expr, "iendswith")
        self.assertEqual(self.filters["macaddressfield__iew"].exclude, False)
        self.assertEqual(self.filters["macaddressfield__niew"].lookup_expr, "iendswith")
        self.assertEqual(self.filters["macaddressfield__niew"].exclude, True)
        self.assertEqual(self.filters["macaddressfield__re"].lookup_expr, "regex")
        self.assertEqual(self.filters["macaddressfield__re"].exclude, False)
        self.assertEqual(self.filters["macaddressfield__nre"].lookup_expr, "regex")
        self.assertEqual(self.filters["macaddressfield__nre"].exclude, True)
        self.assertEqual(self.filters["macaddressfield__ire"].lookup_expr, "iregex")
        self.assertEqual(self.filters["macaddressfield__ire"].exclude, False)
        self.assertEqual(self.filters["macaddressfield__nire"].lookup_expr, "iregex")
        self.assertEqual(self.filters["macaddressfield__nire"].exclude, True)

    def test_model_choice_filter(self):
        self.assertIsInstance(self.filters["modelchoicefield"], django_filters.ModelChoiceFilter)
        self.assertEqual(self.filters["modelchoicefield"].lookup_expr, "exact")
        self.assertEqual(self.filters["modelchoicefield"].exclude, False)
        self.assertEqual(self.filters["modelchoicefield__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["modelchoicefield__n"].exclude, True)

    def test_model_multiple_choice_filter(self):
        self.assertIsInstance(
            self.filters["modelmultiplechoicefield"],
            django_filters.ModelMultipleChoiceFilter,
        )
        self.assertEqual(self.filters["modelmultiplechoicefield"].lookup_expr, "exact")
        self.assertEqual(self.filters["modelmultiplechoicefield"].exclude, False)
        self.assertEqual(self.filters["modelmultiplechoicefield__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["modelmultiplechoicefield__n"].exclude, True)

    def test_multi_value_char_filter(self):
        self.assertIsInstance(self.filters["multivaluecharfield"], filters.MultiValueCharFilter)
        self.assertEqual(self.filters["multivaluecharfield"].lookup_expr, "exact")
        self.assertEqual(self.filters["multivaluecharfield"].exclude, False)
        self.assertEqual(self.filters["multivaluecharfield__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["multivaluecharfield__n"].exclude, True)
        self.assertEqual(self.filters["multivaluecharfield__ie"].lookup_expr, "iexact")
        self.assertEqual(self.filters["multivaluecharfield__ie"].exclude, False)
        self.assertEqual(self.filters["multivaluecharfield__nie"].lookup_expr, "iexact")
        self.assertEqual(self.filters["multivaluecharfield__nie"].exclude, True)
        self.assertEqual(self.filters["multivaluecharfield__ic"].lookup_expr, "icontains")
        self.assertEqual(self.filters["multivaluecharfield__ic"].exclude, False)
        self.assertEqual(self.filters["multivaluecharfield__nic"].lookup_expr, "icontains")
        self.assertEqual(self.filters["multivaluecharfield__nic"].exclude, True)
        self.assertEqual(self.filters["multivaluecharfield__isw"].lookup_expr, "istartswith")
        self.assertEqual(self.filters["multivaluecharfield__isw"].exclude, False)
        self.assertEqual(self.filters["multivaluecharfield__nisw"].lookup_expr, "istartswith")
        self.assertEqual(self.filters["multivaluecharfield__nisw"].exclude, True)
        self.assertEqual(self.filters["multivaluecharfield__iew"].lookup_expr, "iendswith")
        self.assertEqual(self.filters["multivaluecharfield__iew"].exclude, False)
        self.assertEqual(self.filters["multivaluecharfield__niew"].lookup_expr, "iendswith")
        self.assertEqual(self.filters["multivaluecharfield__niew"].exclude, True)
        self.assertEqual(self.filters["multivaluecharfield__re"].lookup_expr, "regex")
        self.assertEqual(self.filters["multivaluecharfield__re"].exclude, False)
        self.assertEqual(self.filters["multivaluecharfield__nre"].lookup_expr, "regex")
        self.assertEqual(self.filters["multivaluecharfield__nre"].exclude, True)
        self.assertEqual(self.filters["multivaluecharfield__ire"].lookup_expr, "iregex")
        self.assertEqual(self.filters["multivaluecharfield__ire"].exclude, False)
        self.assertEqual(self.filters["multivaluecharfield__nire"].lookup_expr, "iregex")
        self.assertEqual(self.filters["multivaluecharfield__nire"].exclude, True)

    def test_textfield_multi_value_char_filter(self):
        self.assertIsInstance(self.filters["textfield"], filters.MultiValueCharFilter)
        self.assertEqual(self.filters["textfield"].lookup_expr, "exact")
        self.assertEqual(self.filters["textfield"].exclude, False)
        self.assertEqual(self.filters["textfield__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["textfield__n"].exclude, True)
        self.assertEqual(self.filters["textfield__ie"].lookup_expr, "iexact")
        self.assertEqual(self.filters["textfield__ie"].exclude, False)
        self.assertEqual(self.filters["textfield__nie"].lookup_expr, "iexact")
        self.assertEqual(self.filters["textfield__nie"].exclude, True)
        self.assertEqual(self.filters["textfield__ic"].lookup_expr, "icontains")
        self.assertEqual(self.filters["textfield__ic"].exclude, False)
        self.assertEqual(self.filters["textfield__nic"].lookup_expr, "icontains")
        self.assertEqual(self.filters["textfield__nic"].exclude, True)
        self.assertEqual(self.filters["textfield__isw"].lookup_expr, "istartswith")
        self.assertEqual(self.filters["textfield__isw"].exclude, False)
        self.assertEqual(self.filters["textfield__nisw"].lookup_expr, "istartswith")
        self.assertEqual(self.filters["textfield__nisw"].exclude, True)
        self.assertEqual(self.filters["textfield__iew"].lookup_expr, "iendswith")
        self.assertEqual(self.filters["textfield__iew"].exclude, False)
        self.assertEqual(self.filters["textfield__niew"].lookup_expr, "iendswith")
        self.assertEqual(self.filters["textfield__niew"].exclude, True)
        self.assertEqual(self.filters["textfield__re"].lookup_expr, "regex")
        self.assertEqual(self.filters["textfield__re"].exclude, False)
        self.assertEqual(self.filters["textfield__nre"].lookup_expr, "regex")
        self.assertEqual(self.filters["textfield__nre"].exclude, True)
        self.assertEqual(self.filters["textfield__ire"].lookup_expr, "iregex")
        self.assertEqual(self.filters["textfield__ire"].exclude, False)
        self.assertEqual(self.filters["textfield__nire"].lookup_expr, "iregex")
        self.assertEqual(self.filters["textfield__nire"].exclude, True)

    def test_multi_value_date_filter(self):
        self.assertIsInstance(self.filters["datefield"], filters.MultiValueDateFilter)
        self.assertEqual(self.filters["datefield"].lookup_expr, "exact")
        self.assertEqual(self.filters["datefield"].exclude, False)
        self.assertEqual(self.filters["datefield__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["datefield__n"].exclude, True)
        self.assertEqual(self.filters["datefield__lt"].lookup_expr, "lt")
        self.assertEqual(self.filters["datefield__lt"].exclude, False)
        self.assertEqual(self.filters["datefield__lte"].lookup_expr, "lte")
        self.assertEqual(self.filters["datefield__lte"].exclude, False)
        self.assertEqual(self.filters["datefield__gt"].lookup_expr, "gt")
        self.assertEqual(self.filters["datefield__gt"].exclude, False)
        self.assertEqual(self.filters["datefield__gte"].lookup_expr, "gte")
        self.assertEqual(self.filters["datefield__gte"].exclude, False)

    def test_multi_value_datetime_filter(self):
        self.assertIsInstance(self.filters["datetimefield"], filters.MultiValueDateTimeFilter)
        self.assertEqual(self.filters["datetimefield"].lookup_expr, "exact")
        self.assertEqual(self.filters["datetimefield"].exclude, False)
        self.assertEqual(self.filters["datetimefield__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["datetimefield__n"].exclude, True)
        self.assertEqual(self.filters["datetimefield__lt"].lookup_expr, "lt")
        self.assertEqual(self.filters["datetimefield__lt"].exclude, False)
        self.assertEqual(self.filters["datetimefield__lte"].lookup_expr, "lte")
        self.assertEqual(self.filters["datetimefield__lte"].exclude, False)
        self.assertEqual(self.filters["datetimefield__gt"].lookup_expr, "gt")
        self.assertEqual(self.filters["datetimefield__gt"].exclude, False)
        self.assertEqual(self.filters["datetimefield__gte"].lookup_expr, "gte")
        self.assertEqual(self.filters["datetimefield__gte"].exclude, False)

    def test_multi_value_number_filter(self):
        self.assertIsInstance(self.filters["integerfield"], filters.MultiValueNumberFilter)
        self.assertEqual(self.filters["integerfield"].lookup_expr, "exact")
        self.assertEqual(self.filters["integerfield"].exclude, False)
        self.assertEqual(self.filters["integerfield__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["integerfield__n"].exclude, True)
        self.assertEqual(self.filters["integerfield__lt"].lookup_expr, "lt")
        self.assertEqual(self.filters["integerfield__lt"].exclude, False)
        self.assertEqual(self.filters["integerfield__lte"].lookup_expr, "lte")
        self.assertEqual(self.filters["integerfield__lte"].exclude, False)
        self.assertEqual(self.filters["integerfield__gt"].lookup_expr, "gt")
        self.assertEqual(self.filters["integerfield__gt"].exclude, False)
        self.assertEqual(self.filters["integerfield__gte"].lookup_expr, "gte")
        self.assertEqual(self.filters["integerfield__gte"].exclude, False)

    def test_multi_value_decimal_filter(self):
        self.assertIsInstance(self.filters["decimalfield"], filters.MultiValueDecimalFilter)
        self.assertEqual(self.filters["decimalfield"].lookup_expr, "exact")
        self.assertEqual(self.filters["decimalfield"].exclude, False)
        self.assertEqual(self.filters["decimalfield__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["decimalfield__n"].exclude, True)
        self.assertEqual(self.filters["decimalfield__lt"].lookup_expr, "lt")
        self.assertEqual(self.filters["decimalfield__lt"].exclude, False)
        self.assertEqual(self.filters["decimalfield__lte"].lookup_expr, "lte")
        self.assertEqual(self.filters["decimalfield__lte"].exclude, False)
        self.assertEqual(self.filters["decimalfield__gt"].lookup_expr, "gt")
        self.assertEqual(self.filters["decimalfield__gt"].exclude, False)
        self.assertEqual(self.filters["decimalfield__gte"].lookup_expr, "gte")
        self.assertEqual(self.filters["decimalfield__gte"].exclude, False)

    def test_multi_value_float_filter(self):
        self.assertIsInstance(self.filters["floatfield"], filters.MultiValueFloatFilter)
        self.assertEqual(self.filters["floatfield"].lookup_expr, "exact")
        self.assertEqual(self.filters["floatfield"].exclude, False)
        self.assertEqual(self.filters["floatfield__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["floatfield__n"].exclude, True)
        self.assertEqual(self.filters["floatfield__lt"].lookup_expr, "lt")
        self.assertEqual(self.filters["floatfield__lt"].exclude, False)
        self.assertEqual(self.filters["floatfield__lte"].lookup_expr, "lte")
        self.assertEqual(self.filters["floatfield__lte"].exclude, False)
        self.assertEqual(self.filters["floatfield__gt"].lookup_expr, "gt")
        self.assertEqual(self.filters["floatfield__gt"].exclude, False)
        self.assertEqual(self.filters["floatfield__gte"].lookup_expr, "gte")
        self.assertEqual(self.filters["floatfield__gte"].exclude, False)

    def test_multi_value_time_filter(self):
        self.assertIsInstance(self.filters["timefield"], filters.MultiValueTimeFilter)
        self.assertEqual(self.filters["timefield"].lookup_expr, "exact")
        self.assertEqual(self.filters["timefield"].exclude, False)
        self.assertEqual(self.filters["timefield__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["timefield__n"].exclude, True)
        self.assertEqual(self.filters["timefield__lt"].lookup_expr, "lt")
        self.assertEqual(self.filters["timefield__lt"].exclude, False)
        self.assertEqual(self.filters["timefield__lte"].lookup_expr, "lte")
        self.assertEqual(self.filters["timefield__lte"].exclude, False)
        self.assertEqual(self.filters["timefield__gt"].lookup_expr, "gt")
        self.assertEqual(self.filters["timefield__gt"].exclude, False)
        self.assertEqual(self.filters["timefield__gte"].lookup_expr, "gte")
        self.assertEqual(self.filters["timefield__gte"].exclude, False)

    def test_multiple_choice_filter(self):
        for field in ["multiplechoicefield", "charchoicefield", "choicefield"]:
            self.assertIsInstance(self.filters[field], django_filters.MultipleChoiceFilter)
            self.assertEqual(self.filters[field].lookup_expr, "exact")
            self.assertEqual(self.filters[field].exclude, False)
            self.assertEqual(self.filters[f"{field}__n"].lookup_expr, "exact")
            self.assertEqual(self.filters[f"{field}__n"].exclude, True)
            self.assertEqual(self.filters[f"{field}__ie"].lookup_expr, "iexact")
            self.assertEqual(self.filters[f"{field}__ie"].exclude, False)
            self.assertEqual(self.filters[f"{field}__nie"].lookup_expr, "iexact")
            self.assertEqual(self.filters[f"{field}__nie"].exclude, True)
            self.assertEqual(self.filters[f"{field}__ic"].lookup_expr, "icontains")
            self.assertEqual(self.filters[f"{field}__ic"].exclude, False)
            self.assertEqual(self.filters[f"{field}__nic"].lookup_expr, "icontains")
            self.assertEqual(self.filters[f"{field}__nic"].exclude, True)
            self.assertEqual(self.filters[f"{field}__isw"].lookup_expr, "istartswith")
            self.assertEqual(self.filters[f"{field}__isw"].exclude, False)
            self.assertEqual(self.filters[f"{field}__nisw"].lookup_expr, "istartswith")
            self.assertEqual(self.filters[f"{field}__nisw"].exclude, True)
            self.assertEqual(self.filters[f"{field}__iew"].lookup_expr, "iendswith")
            self.assertEqual(self.filters[f"{field}__iew"].exclude, False)
            self.assertEqual(self.filters[f"{field}__niew"].lookup_expr, "iendswith")
            self.assertEqual(self.filters[f"{field}__niew"].exclude, True)
            self.assertEqual(self.filters[f"{field}__re"].lookup_expr, "regex")
            self.assertEqual(self.filters[f"{field}__re"].exclude, False)
            self.assertEqual(self.filters[f"{field}__nre"].lookup_expr, "regex")
            self.assertEqual(self.filters[f"{field}__nre"].exclude, True)
            self.assertEqual(self.filters[f"{field}__ire"].lookup_expr, "iregex")
            self.assertEqual(self.filters[f"{field}__ire"].exclude, False)
            self.assertEqual(self.filters[f"{field}__nire"].lookup_expr, "iregex")
            self.assertEqual(self.filters[f"{field}__nire"].exclude, True)

    def test_tag_filter(self):
        self.assertIsInstance(self.filters["tags"], filters.TagFilter)
        self.assertEqual(self.filters["tags"].lookup_expr, "exact")
        self.assertEqual(self.filters["tags"].exclude, False)
        self.assertEqual(self.filters["tags__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["tags__n"].exclude, True)

    def test_tree_node_multiple_choice_filter(self):
        self.assertIsInstance(self.filters["treeforeignkeyfield"], filters.TreeNodeMultipleChoiceFilter)
        self.assertEqual(self.filters["treeforeignkeyfield"].lookup_expr, "exact")
        self.assertEqual(self.filters["treeforeignkeyfield"].exclude, False)
        self.assertEqual(self.filters["treeforeignkeyfield__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["treeforeignkeyfield__n"].exclude, True)


class DynamicFilterLookupExpressionTest(TestCase):
    """
    Validate function of automatically generated filters using the Device model as an example.
    """

    device_queryset = dcim_models.Device.objects.all()
    device_filterset = dcim_filters.DeviceFilterSet
    location_queryset = dcim_models.Location.objects.all()
    location_filterset = dcim_filters.LocationFilterSet

    @classmethod
    def setUpTestData(cls):
        manufacturers = dcim_models.Manufacturer.objects.all()[:3]

        device_types = (
            dcim_models.DeviceType(
                manufacturer=manufacturers[0],
                model="Model 1",
                is_full_depth=True,
            ),
            dcim_models.DeviceType(
                manufacturer=manufacturers[1],
                model="Model 2",
                is_full_depth=True,
            ),
            dcim_models.DeviceType(
                manufacturer=manufacturers[2],
                model="Model 3",
                is_full_depth=False,
            ),
        )
        dcim_models.DeviceType.objects.bulk_create(device_types)

        device_roles = extras_models.Role.objects.get_for_model(Device)

        device_statuses = extras_models.Status.objects.get_for_model(dcim_models.Device)

        platforms = dcim_models.Platform.objects.all()[:3]
        cls.location_type = dcim_models.LocationType.objects.filter(parent__isnull=False).first()
        cls.location_type.content_types.add(
            ContentType.objects.get_for_model(dcim_models.Rack), ContentType.objects.get_for_model(dcim_models.Device)
        )
        cls.locations = dcim_models.Location.objects.filter(location_type=cls.location_type)[:3]
        cls.locations[0].asn = 65001
        cls.locations[1].asn = 65101
        cls.locations[2].asn = 65201

        rack_status = extras_models.Status.objects.get_for_model(dcim_models.Rack).first()
        racks = (
            dcim_models.Rack(name="Rack 1", location=cls.locations[0], status=rack_status),
            dcim_models.Rack(name="Rack 2", location=cls.locations[1], status=rack_status),
            dcim_models.Rack(name="Rack 3", location=cls.locations[2], status=rack_status),
        )
        dcim_models.Rack.objects.bulk_create(racks)

        devices = (
            dcim_models.Device(
                name="Device 1",
                device_type=device_types[0],
                role=device_roles[0],
                platform=platforms[0],
                serial="ABC",
                asset_tag="1001",
                location=cls.locations[0],
                rack=racks[0],
                position=1,
                face=dcim_choices.DeviceFaceChoices.FACE_FRONT,
                status=device_statuses[0],
                local_config_context_data={"foo": 123},
                comments="Device 1 comments",
            ),
            dcim_models.Device(
                name="Device 2",
                device_type=device_types[1],
                role=device_roles[1],
                platform=platforms[1],
                serial="DEF",
                asset_tag="1002",
                location=cls.locations[1],
                rack=racks[1],
                position=2,
                face=dcim_choices.DeviceFaceChoices.FACE_FRONT,
                status=device_statuses[2],
                comments="Device 2 comments",
            ),
            dcim_models.Device(
                name="Device 3",
                device_type=device_types[2],
                role=device_roles[2],
                platform=platforms[2],
                serial="GHI",
                asset_tag="1003",
                location=cls.locations[2],
                rack=racks[2],
                position=3,
                face=dcim_choices.DeviceFaceChoices.FACE_REAR,
                status=device_statuses[1],
                comments="Device 3 comments",
            ),
        )
        dcim_models.Device.objects.bulk_create(devices)

        intf_status = extras_models.Status.objects.get_for_model(dcim_models.Interface).first()
        interfaces = (
            dcim_models.Interface(
                device=devices[0], name="Interface 1", mac_address="00-00-00-00-00-01", status=intf_status
            ),
            dcim_models.Interface(
                device=devices[0], name="Interface 2", mac_address="aa-00-00-00-00-01", status=intf_status
            ),
            dcim_models.Interface(
                device=devices[1], name="Interface 3", mac_address="00-00-00-00-00-02", status=intf_status
            ),
            dcim_models.Interface(
                device=devices[1], name="Interface 4", mac_address="bb-00-00-00-00-02", status=intf_status
            ),
            dcim_models.Interface(
                device=devices[2], name="Interface 5", mac_address="00-00-00-00-00-03", status=intf_status
            ),
            dcim_models.Interface(
                device=devices[2], name="Interface 6", mac_address="cc-00-00-00-00-03", status=intf_status
            ),
        )
        dcim_models.Interface.objects.bulk_create(interfaces)

    class DeviceFilterSetWithComments(dcim_filters.DeviceFilterSet):
        class Meta:
            model = dcim_models.Device
            fields = [
                "comments",
            ]

    def test_location_name_negation(self):
        params = {"name__n": ["Location 1"]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.exclude(name="Location 1"),
        )

    def test_location_name_icontains(self):
        params = {"name__ic": ["-1"]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.filter(name__icontains="-1"),
        )

    def test_location_name_icontains_negation(self):
        params = {"name__nic": ["-1"]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.exclude(name__icontains="-1"),
        )

    def test_location_name_startswith(self):
        startswith = dcim_models.Location.objects.first().name[:3]
        params = {"name__isw": [startswith]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.filter(name__istartswith=startswith),
        )

    def test_location_name_startswith_negation(self):
        startswith = dcim_models.Location.objects.first().name[:3]
        params = {"name__nisw": [startswith]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.exclude(name__icontains=startswith),
        )

    def test_location_name_endswith(self):
        endswith = dcim_models.Location.objects.first().name[-2:]
        params = {"name__iew": [endswith]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.filter(name__iendswith=endswith),
        )

    def test_location_name_endswith_negation(self):
        endswith = dcim_models.Location.objects.first().name[-2:]
        params = {"name__niew": [endswith]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.exclude(name__iendswith=endswith),
        )

    def test_location_name_regex(self):
        params = {"name__re": ["-1$"]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.filter(name__regex="-1$"),
        )

    def test_location_name_regex_negation(self):
        params = {"name__nre": ["-1$"]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.exclude(name__regex="-1$"),
        )

    def test_location_name_iregex(self):
        params = {"name__ire": ["location"]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.filter(name__iregex="location"),
        )

    def test_location_name_iregex_negation(self):
        params = {"name__nire": ["location"]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.exclude(name__iregex="location"),
        )

    def test_location_asn_lt(self):
        asn = dcim_models.Location.objects.filter(asn__isnull=False).first().asn
        params = {"asn__lt": [asn]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.filter(asn__lt=asn),
        )

    def test_location_asn_lte(self):
        asn = dcim_models.Location.objects.filter(asn__isnull=False).first().asn
        params = {"asn__lte": [asn]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.filter(asn__lte=asn),
        )

    def test_location_asn_gt(self):
        asn = dcim_models.Location.objects.filter(asn__isnull=False).first().asn
        params = {"asn__gt": [asn]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.filter(asn__gt=asn),
        )

    def test_location_asn_gte(self):
        asn = dcim_models.Location.objects.filter(asn__isnull=False).first().asn
        params = {"asn__gte": [asn]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.filter(asn__gte=asn),
        )

    def test_location_parent_negation(self):
        params = {"parent__n": [self.locations[0].parent.name]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.exclude(parent__name__in=[self.locations[0].parent.name]),
        )

    def test_location_parent_id_negation(self):
        params = {"parent__n": [self.locations[0].parent.pk]}
        self.assertQuerysetEqual(
            dcim_filters.LocationFilterSet(params, self.location_queryset).qs,
            dcim_models.Location.objects.exclude(parent__in=[self.locations[0].parent.pk]),
        )

    def test_device_name_eq(self):
        params = {"name": ["Device 1"]}
        self.assertQuerysetEqual(
            dcim_filters.DeviceFilterSet(params, self.device_queryset).qs,
            dcim_models.Device.objects.filter(name="Device 1"),
        )

    def test_device_name_negation(self):
        params = {"name__n": ["Device 1"]}
        self.assertQuerysetEqual(
            dcim_filters.DeviceFilterSet(params, self.device_queryset).qs,
            dcim_models.Device.objects.exclude(name="Device 1"),
        )

    def test_device_name_startswith(self):
        params = {"name__isw": ["Device"]}
        self.assertQuerysetEqual(
            dcim_filters.DeviceFilterSet(params, self.device_queryset).qs,
            dcim_models.Device.objects.filter(name__istartswith="Device"),
        )

    def test_device_name_startswith_negation(self):
        params = {"name__nisw": ["Device 1"]}
        self.assertQuerysetEqual(
            dcim_filters.DeviceFilterSet(params, self.device_queryset).qs,
            dcim_models.Device.objects.exclude(name__istartswith="Device 1"),
        )

    def test_device_name_endswith(self):
        params = {"name__iew": [" 1"]}
        self.assertQuerysetEqual(
            dcim_filters.DeviceFilterSet(params, self.device_queryset).qs,
            dcim_models.Device.objects.filter(name__iendswith=" 1"),
        )

    def test_device_name_endswith_negation(self):
        params = {"name__niew": [" 1"]}
        self.assertQuerysetEqual(
            dcim_filters.DeviceFilterSet(params, self.device_queryset).qs,
            dcim_models.Device.objects.exclude(name__iendswith=" 1"),
        )

    def test_device_name_icontains(self):
        params = {"name__ic": [" 2"]}
        self.assertQuerysetEqual(
            dcim_filters.DeviceFilterSet(params, self.device_queryset).qs,
            dcim_models.Device.objects.filter(name__icontains=" 2"),
        )

    def test_device_name_icontains_negation(self):
        params = {"name__nic": [" "]}
        self.assertQuerysetEqual(
            dcim_filters.DeviceFilterSet(params, self.device_queryset).qs,
            dcim_models.Device.objects.exclude(name__icontains=" "),
        )

    def test_device_mac_address_negation(self):
        params = {"mac_address__n": ["00-00-00-00-00-01", "aa-00-00-00-00-01"]}
        self.assertEqual(dcim_filters.DeviceFilterSet(params, self.device_queryset).qs.count(), 2)

    def test_device_mac_address_startswith(self):
        params = {"mac_address__isw": ["aa:"]}
        self.assertEqual(dcim_filters.DeviceFilterSet(params, self.device_queryset).qs.count(), 1)

    def test_device_mac_address_startswith_negation(self):
        params = {"mac_address__nisw": ["aa:"]}
        self.assertEqual(dcim_filters.DeviceFilterSet(params, self.device_queryset).qs.count(), 2)

    def test_device_mac_address_endswith(self):
        params = {"mac_address__iew": [":02"]}
        self.assertEqual(dcim_filters.DeviceFilterSet(params, self.device_queryset).qs.count(), 1)

    def test_device_mac_address_endswith_negation(self):
        params = {"mac_address__niew": [":02"]}
        self.assertEqual(dcim_filters.DeviceFilterSet(params, self.device_queryset).qs.count(), 2)

    def test_device_mac_address_icontains(self):
        params = {"mac_address__ic": ["aa:", "bb"]}
        self.assertEqual(dcim_filters.DeviceFilterSet(params, self.device_queryset).qs.count(), 2)

    def test_device_mac_address_icontains_negation(self):
        params = {"mac_address__nic": ["aa:", "bb"]}
        self.assertEqual(dcim_filters.DeviceFilterSet(params, self.device_queryset).qs.count(), 1)

    def test_device_mac_address_regex(self):
        params = {"mac_address__re": ["^AA:"]}
        self.assertEqual(dcim_filters.DeviceFilterSet(params, self.device_queryset).qs.count(), 1)

    def test_device_mac_address_iregex(self):
        params = {"mac_address__ire": ["^aa:"]}
        self.assertEqual(dcim_filters.DeviceFilterSet(params, self.device_queryset).qs.count(), 1)

    def test_device_mac_address_regex_negation(self):
        params = {"mac_address__nre": ["^AA:"]}
        self.assertEqual(dcim_filters.DeviceFilterSet(params, self.device_queryset).qs.count(), 2)

    def test_device_mac_address_iregex_negation(self):
        params = {"mac_address__nire": ["^aa:"]}
        self.assertEqual(dcim_filters.DeviceFilterSet(params, self.device_queryset).qs.count(), 2)

    def test_device_comments_multiple_value_charfield(self):
        params = {"comments": ["Device 1 comments"]}
        self.assertQuerysetEqual(
            self.DeviceFilterSetWithComments(params, self.device_queryset).qs,
            dcim_models.Device.objects.filter(comments="Device 1 comments"),
        )
        params = {"comments": ["Device 1 comments", "Device 2 comments"]}
        self.assertQuerysetEqual(
            self.DeviceFilterSetWithComments(params, self.device_queryset).qs,
            dcim_models.Device.objects.filter(comments__in=["Device 1 comments", "Device 2 comments"]),
        )
        params = {"comments": ["Device 1 comments", "Device 2 comments", "Device 3 comments"]}
        self.assertQuerysetEqual(
            self.DeviceFilterSetWithComments(params, self.device_queryset).qs,
            dcim_models.Device.objects.filter(
                comments__in=["Device 1 comments", "Device 2 comments", "Device 3 comments"]
            ),
        )

    def test_device_comments_multiple_value_charfield_regex(self):
        params = {"comments__re": ["^Device"]}
        self.assertQuerysetEqual(
            self.DeviceFilterSetWithComments(params, self.device_queryset).qs,
            dcim_models.Device.objects.filter(comments__regex="^Device"),
        )

    def test_device_comments_multiple_value_charfield_regex_negation(self):
        params = {"comments__nre": ["^Device"]}
        self.assertQuerysetEqual(
            self.DeviceFilterSetWithComments(params, self.device_queryset).qs,
            dcim_models.Device.objects.exclude(comments__regex="^Device"),
        )

    def test_device_comments_multiple_value_charfield_iregex(self):
        params = {"comments__ire": ["^device"]}
        self.assertQuerysetEqual(
            self.DeviceFilterSetWithComments(params, self.device_queryset).qs,
            dcim_models.Device.objects.filter(comments__iregex="^device"),
        )

    def test_device_comments_multiple_value_charfield_iregex_negation(self):
        params = {"comments__nire": ["^device"]}
        self.assertQuerysetEqual(
            self.DeviceFilterSetWithComments(params, self.device_queryset).qs,
            dcim_models.Device.objects.exclude(comments__iregex="^device"),
        )


class GetFiltersetTestValuesTest(testing.FilterTestCases.BaseFilterTestCase):
    """Tests for `BaseFilterTestCase.get_filterset_test_values()`."""

    queryset = dcim_models.Location.objects.filter(name__startswith="getfiltersettest")
    exception_message = "Cannot find enough valid test data for Location field description"

    @classmethod
    def setUpTestData(cls):
        statuses = extras_models.Status.objects.get_for_model(dcim_models.Location)
        cls.status = statuses[0]

    def test_empty_queryset(self):
        with self.assertRaisesMessage(ValueError, self.exception_message):
            self.get_filterset_test_values("description")

    def test_object_return_count(self):
        location_type = dcim_models.LocationType.objects.get(name="Campus")
        for n in range(1, 11):
            dcim_models.Location.objects.create(
                name=f"getfiltersettestLocation{n}",
                status=self.status,
                description=f"description {n}",
                location_type=location_type,
            )
        test_values = self.get_filterset_test_values("description", self.queryset)
        self.assertNotEqual(len(test_values), 0)
        self.assertNotEqual(len(test_values), self.queryset.count())

    def test_insufficient_unique_values(self):
        location_type = dcim_models.LocationType.objects.get(name="Campus")
        dcim_models.Location.objects.create(
            name="getfiltersettestUniqueLocation",
            description="UniqueLocation description",
            location_type=location_type,
            status=self.status,
        )
        with self.assertRaisesMessage(ValueError, self.exception_message):
            self.get_filterset_test_values("description")
        dcim_models.Location.objects.create(
            name="getfiltersettestLocation1", status=self.status, location_type=location_type
        )
        dcim_models.Location.objects.create(
            name="getfiltersettestLocation2", status=self.status, location_type=location_type
        )
        with self.assertRaisesMessage(ValueError, self.exception_message):
            self.get_filterset_test_values("description")

    def test_no_unique_values(self):
        location_type = dcim_models.LocationType.objects.get(name="Campus")
        for n in range(1, 11):
            dcim_models.Location.objects.create(
                name=f"getfiltersettestLocation{n}", status=self.status, location_type=location_type
            )
        for location in self.queryset:
            location.delete()
            with self.assertRaisesMessage(ValueError, self.exception_message):
                self.get_filterset_test_values("description")


class SearchFilterTest(TestCase, testing.NautobotTestCaseMixin):
    """Tests for the `SearchFilter` filter class."""

    filterset_class = dcim_filters.LocationFilterSet

    def setUp(self):
        super().setUp()
        self.lt = dcim_models.LocationType.objects.get(name="Campus")
        status = extras_models.Status.objects.get_for_model(dcim_models.Location).first()
        self.parent_location_1 = dcim_models.Location.objects.create(
            name="Test Parent Location 1", location_type=self.lt, status=status
        )
        self.parent_location_2 = dcim_models.Location.objects.create(
            name="Test Parent Location 2", location_type=self.lt, status=status
        )
        self.child_location_1 = dcim_models.Location.objects.create(
            parent=self.parent_location_1,
            name="Test Child Location 1",
            location_type=self.lt,
            asn=1234,
            status=status,
        )
        self.child_location_2 = dcim_models.Location.objects.create(
            parent=self.parent_location_2,
            name="Test Child Location 2",
            location_type=self.lt,
            asn=12345,
            status=status,
        )
        self.child_location_3 = dcim_models.Location.objects.create(
            parent=None,
            name="Test Child Location 3",
            location_type=self.lt,
            status=status,
        )
        self.child_location_4 = dcim_models.Location.objects.create(
            parent=None,
            name="Test Child Location4",
            location_type=self.lt,
            status=status,
        )
        self.queryset = dcim_models.Location.objects.all()

    def get_filterset_count(self, params, klass=None):
        """To save ourselves some boilerplate."""
        if klass is None:
            klass = self.filterset_class
        return klass(params, self.queryset).qs.count()

    def test_default_icontains(self):
        """Test a default search for an "icontains" value."""
        params = {"q": "Test Child Location"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset_class(params, self.queryset).qs, self.queryset.filter(name__icontains="Test Child Location")
        )
        params = {"q": "Test Child Location 3"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset_class(params, self.queryset).qs,
            self.queryset.filter(name__icontains="Test Child Location 3"),
        )
        # Trailing space should only match the first 3.
        params = {"q": "Test Child Location "}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset_class(params, self.queryset).qs, self.queryset.filter(name__icontains="Test Child Location ")
        )

    def test_default_exact(self):
        """Test a default search for an "exact" value."""
        params = {"q": "1234"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset_class(params, self.queryset).qs, self.queryset.filter(asn__exact="1234")
        )
        asn = (
            dcim_models.Location.objects.exclude(asn="1234")
            .exclude(asn__isnull=True)
            .values_list("asn", flat=True)
            .first()
        )
        params = {"q": str(asn)}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset_class(params, self.queryset).qs, self.queryset.filter(asn__exact=str(asn))
        )

    def test_default_id(self):
        """Test default search on "id" field."""
        # Search is iexact so UUID search for lower/upper return the same result.
        obj_pk = str(self.child_location_1.pk)
        params = {"q": obj_pk.lower()}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset_class(params, self.queryset).qs, self.queryset.filter(id__iexact=obj_pk.lower())
        )
        params = {"q": obj_pk.upper()}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset_class(params, self.queryset).qs, self.queryset.filter(id__iexact=obj_pk.upper())
        )

    def test_typed_valid(self):
        """Test that validly-typed predicate mappings are handled correctly."""

        class MyLocationFilterSet(dcim_filters.LocationFilterSet):
            """Overload the default just to illustrate that it's all we're testing for here."""

            q = filters.SearchFilter(filter_predicates={"asn": {"lookup_expr": "exact", "preprocessor": int}})

        params = {"q": "1234"}
        self.assertQuerysetEqualAndNotEmpty(
            MyLocationFilterSet(params, self.queryset).qs, self.queryset.filter(asn__exact="1234")
        )
        params = {"q": "123"}
        # Both querysets are empty so we dont use assertQuerysetEqualAndNotEmpty here.
        self.assertQuerysetEqual(MyLocationFilterSet(params, self.queryset).qs, self.queryset.filter(asn__exact="123"))

        # Further an invalid type (e.g. dict) will just result in the predicate for ASN to be skipped
        class MyLocationFilterSet2(dcim_filters.LocationFilterSet):
            """Overload the default just to illustrate that it's all we're testing for here."""

            q = filters.SearchFilter(filter_predicates={"asn": {"lookup_expr": "exact", "preprocessor": dict}})

        params = {"q": "1234"}
        # Both querysets are empty so we dont use assertQuerysetEqualAndNotEmpty here.
        self.assertEqual(self.get_filterset_count(params, MyLocationFilterSet2), 0)

    def test_typed_icontains(self):
        """Test a preprocessor to strip icontains (which wouldn't be by default)."""

        class MyLocationFilterSet(dcim_filters.LocationFilterSet):
            """Overload the default just to illustrate that it's all we're testing for here."""

            q = filters.SearchFilter(
                filter_predicates={"name": {"lookup_expr": "icontains", "preprocessor": str.strip}}
            )

        # Both searches should return the same results.
        params = {"q": "Test Child Location"}
        self.assertQuerysetEqualAndNotEmpty(
            MyLocationFilterSet(params, self.queryset).qs, self.queryset.filter(name__icontains="Test Child Location")
        )
        params = {"q": "Test Child Location "}
        self.assertQuerysetEqualAndNotEmpty(
            MyLocationFilterSet(params, self.queryset).qs, self.queryset.filter(name__icontains="Test Child Location")
        )

    def test_typed_invalid(self):
        """Test that incorrectly-typed predicate mappings are handled correctly."""
        # Bad preprocessor callable in expanded form
        with self.assertRaises(TypeError):
            barf = None

            class BarfLocationFilterSet(dcim_filters.LocationFilterSet):  # pylint: disable=unused-variable
                q = filters.SearchFilter(
                    filter_predicates={
                        "asn": {"preprocessor": barf, "lookup_expr": "exact"},
                    },
                )

        # Missing preprocessor callable in expanded form should also fail
        with self.assertRaises(TypeError):

            class MissingLocationFilterSet(dcim_filters.LocationFilterSet):  # pylint: disable=unused-variable
                q = filters.SearchFilter(filter_predicates={"asn": {"lookup_expr": "exact"}})

        # Incorrect lookup_info type (must be str or dict)
        with self.assertRaises(TypeError):

            class InvalidLocationFilterSet(dcim_filters.LocationFilterSet):  # pylint: disable=unused-variable
                q = filters.SearchFilter(filter_predicates={"asn": ["icontains"]})


class FilterTypeTest(TestCase):
    client_class = testing.NautobotTestClient

    def test_numberfilter(self):
        """
        Simple test to show the bug identified in https://github.com/nautobot/nautobot/issues/2837 no longer exists
        """
        user = get_user_model().objects.create_user(username="testuser", is_superuser=True)
        self.client.force_login(user)
        ipam_factory.PrefixFactory()
        prefix_list_url = reverse(lookup.get_route_for_model(ipam_models.Prefix, "list"))
        response = self.client.get(f"{prefix_list_url}?prefix_length__lte=20")
        self.assertNotContains(response, "Invalid filters were specified")
