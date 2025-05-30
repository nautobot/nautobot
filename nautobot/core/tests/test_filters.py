import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models as django_models
from django.shortcuts import reverse
from django.test import TestCase
from django.test.utils import isolate_apps
import django_filters
from tree_queries.models import TreeNodeForeignKey

from nautobot.circuits.filters import CircuitFilterSet
from nautobot.circuits.models import Circuit, CircuitType, Provider
from nautobot.core import filters, testing
from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import fields as core_fields
from nautobot.core.utils import lookup
from nautobot.dcim import choices as dcim_choices, filters as dcim_filters, models as dcim_models
from nautobot.dcim.models import Controller, Device
from nautobot.extras import models as extras_models
from nautobot.extras.utils import FeatureQuery
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
            ordered=False,
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
            ordered=False,
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

    class TestFilterSet(filters.BaseFilterSet):  # pylint: disable=used-before-assignment  # appears to be a pylint bug
        """Filterset for testing various fields."""

        class TestModel(django_models.Model):  # noqa: DJ008  # django-model-without-dunder-str -- fine since this isn't a "real" model
            """
            Test model used by BaseFilterSetTest for filter validation. Should never appear in a schema migration.
            """

            charfield = django_models.CharField(max_length=CHARFIELD_MAX_LENGTH)
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

    def _test_lookups(self, filter_name, lookups_map, expected_type):
        for key, (exclude, lookup_expr) in lookups_map.items():
            with self.subTest(field=key):
                filter_key = f"{filter_name}__{key}" if key else filter_name
                self.assertIsInstance(self.filters[filter_key], expected_type)
                self.assertEqual(self.filters[filter_key].lookup_expr, lookup_expr)
                self.assertEqual(self.filters[filter_key].exclude, exclude)

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
        char_field_lookups = {
            "": (False, "exact"),
            "n": (True, "exact"),
            "ie": (False, "iexact"),
            "nie": (True, "iexact"),
            "ic": (False, "icontains"),
            "nic": (True, "icontains"),
            "isw": (False, "istartswith"),
            "nisw": (True, "istartswith"),
            "iew": (False, "iendswith"),
            "niew": (True, "iendswith"),
            "re": (False, "regex"),
            "nre": (True, "regex"),
            "ire": (False, "iregex"),
            "nire": (True, "iregex"),
        }

        self._test_lookups("charfield", char_field_lookups, django_filters.CharFilter)

    def test_mac_address_filter(self):
        mac_address_field_lookups = {
            "": (False, "exact"),
            "n": (True, "exact"),
            "ie": (False, "iexact"),
            "nie": (True, "iexact"),
            "ic": (False, "icontains"),
            "nic": (True, "icontains"),
            "isw": (False, "istartswith"),
            "nisw": (True, "istartswith"),
            "iew": (False, "iendswith"),
            "niew": (True, "iendswith"),
            "re": (False, "regex"),
            "nre": (True, "regex"),
            "ire": (False, "iregex"),
            "nire": (True, "iregex"),
        }

        self._test_lookups("macaddressfield", mac_address_field_lookups, filters.MACAddressFilter)

    def test_model_choice_filter(self):
        model_choice_field_lookups = {
            "": (False, "exact"),
            "n": (True, "exact"),
        }

        self._test_lookups("modelchoicefield", model_choice_field_lookups, django_filters.ModelChoiceFilter)

    def test_model_multiple_choice_filter(self):
        model_multiple_choice_field_lookups = {
            "": (False, "exact"),
            "n": (True, "exact"),
        }

        self._test_lookups(
            "modelmultiplechoicefield", model_multiple_choice_field_lookups, django_filters.ModelMultipleChoiceFilter
        )

    def test_multi_value_char_filter(self):
        multi_value_char_field_lookups = {
            "": (False, "exact"),
            "n": (True, "exact"),
            "ie": (False, "iexact"),
            "nie": (True, "iexact"),
            "ic": (False, "icontains"),
            "nic": (True, "icontains"),
            "isw": (False, "istartswith"),
            "nisw": (True, "istartswith"),
            "iew": (False, "iendswith"),
            "niew": (True, "iendswith"),
            "re": (False, "regex"),
            "nre": (True, "regex"),
            "ire": (False, "iregex"),
            "nire": (True, "iregex"),
        }

        self._test_lookups("multivaluecharfield", multi_value_char_field_lookups, filters.MultiValueCharFilter)

    def test_textfield_multi_value_char_filter(self):
        text_field_lookups = {
            "": (False, "exact"),
            "n": (True, "exact"),
            "ie": (False, "iexact"),
            "nie": (True, "iexact"),
            "ic": (False, "icontains"),
            "nic": (True, "icontains"),
            "isw": (False, "istartswith"),
            "nisw": (True, "istartswith"),
            "iew": (False, "iendswith"),
            "niew": (True, "iendswith"),
            "re": (False, "regex"),
            "nre": (True, "regex"),
            "ire": (False, "iregex"),
            "nire": (True, "iregex"),
        }

        self._test_lookups("textfield", text_field_lookups, filters.MultiValueCharFilter)

    def test_multi_value_date_filter(self):
        date_field_lookups = {
            "": (False, "exact"),
            "n": (True, "exact"),
            "lt": (False, "lt"),
            "lte": (False, "lte"),
            "gt": (False, "gt"),
            "gte": (False, "gte"),
        }

        self._test_lookups("datefield", date_field_lookups, filters.MultiValueDateFilter)

    def test_multi_value_datetime_filter(self):
        datetime_field_lookups = {
            "": (False, "exact"),
            "n": (True, "exact"),
            "lt": (False, "lt"),
            "lte": (False, "lte"),
            "gt": (False, "gt"),
            "gte": (False, "gte"),
        }

        self._test_lookups("datetimefield", datetime_field_lookups, filters.MultiValueDateTimeFilter)

    def test_multi_value_number_filter(self):
        integer_field_lookups = {
            "": (False, "exact"),
            "n": (True, "exact"),
            "lt": (False, "lt"),
            "lte": (False, "lte"),
            "gt": (False, "gt"),
            "gte": (False, "gte"),
        }

        self._test_lookups("integerfield", integer_field_lookups, filters.MultiValueNumberFilter)

    def test_multi_value_decimal_filter(self):
        decimal_field_lookups = {
            "": (False, "exact"),
            "n": (True, "exact"),
            "lt": (False, "lt"),
            "lte": (False, "lte"),
            "gt": (False, "gt"),
            "gte": (False, "gte"),
        }

        self._test_lookups("decimalfield", decimal_field_lookups, filters.MultiValueDecimalFilter)

    def test_multi_value_float_filter(self):
        float_field_lookups = {
            "": (False, "exact"),
            "n": (True, "exact"),
            "lt": (False, "lt"),
            "lte": (False, "lte"),
            "gt": (False, "gt"),
            "gte": (False, "gte"),
        }

        self._test_lookups("floatfield", float_field_lookups, filters.MultiValueFloatFilter)

    def test_multi_value_time_filter(self):
        time_field_lookups = {
            "": (False, "exact"),
            "n": (True, "exact"),
            "lt": (False, "lt"),
            "lte": (False, "lte"),
            "gt": (False, "gt"),
            "gte": (False, "gte"),
        }

        self._test_lookups("timefield", time_field_lookups, filters.MultiValueTimeFilter)

    def test_multiple_choice_filter(self):
        choice_field_lookups = {
            "": (False, "exact"),
            "n": (True, "exact"),
            "ie": (False, "iexact"),
            "nie": (True, "iexact"),
            "ic": (False, "icontains"),
            "nic": (True, "icontains"),
            "isw": (False, "istartswith"),
            "nisw": (True, "istartswith"),
            "iew": (False, "iendswith"),
            "niew": (True, "iendswith"),
            "re": (False, "regex"),
            "nre": (True, "regex"),
            "ire": (False, "iregex"),
            "nire": (True, "iregex"),
        }

        for field in ["charchoicefield", "choicefield"]:
            self._test_lookups(field, choice_field_lookups, django_filters.MultipleChoiceFilter)

    def test_multiple_choice_filter_has_different_type_for_lookups(self):
        choice_field_lookups = {
            "": (False, "exact"),
            "n": (True, "exact"),
        }

        self._test_lookups("multiplechoicefield", choice_field_lookups, django_filters.MultipleChoiceFilter)

        string_type_lookups = {
            "ie": (False, "iexact"),
            "nie": (True, "iexact"),
            "ic": (False, "icontains"),
            "nic": (True, "icontains"),
            "isw": (False, "istartswith"),
            "nisw": (True, "istartswith"),
            "iew": (False, "iendswith"),
            "niew": (True, "iendswith"),
            "re": (False, "regex"),
            "nre": (True, "regex"),
            "ire": (False, "iregex"),
            "nire": (True, "iregex"),
        }

        self._test_lookups("multiplechoicefield", string_type_lookups, filters.MultiValueCharFilter)

    def test_tag_filter(self):
        tags_lookups = {
            "": (False, "exact"),
            "n": (True, "exact"),
        }

        self._test_lookups("tags", tags_lookups, filters.TagFilter)

    def test_tree_node_multiple_choice_filter(self):
        tree_foreign_key_lookups = {
            "": (False, "exact"),
            "n": (True, "exact"),
        }

        self._test_lookups("treeforeignkeyfield", tree_foreign_key_lookups, filters.TreeNodeMultipleChoiceFilter)


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
        Controller.objects.filter(controller_device__isnull=False).delete()
        Device.objects.all().delete()

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
            asn=12345,
            status=status,
        )
        self.child_location_2 = dcim_models.Location.objects.create(
            parent=self.parent_location_2,
            name="Test Child Location 2",
            location_type=self.lt,
            asn=123456,
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
        params = {"q": "12345"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset_class(params, self.queryset).qs, self.queryset.filter(asn__exact=12345)
        )
        asn = (
            dcim_models.Location.objects.exclude(asn="12345")
            .exclude(asn__isnull=True)
            .values_list("asn", flat=True)
            .first()
        )
        params = {"q": str(asn)}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset_class(params, self.queryset).qs, self.queryset.filter(asn__exact=asn)
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

        params = {"q": "12345"}
        self.assertQuerysetEqualAndNotEmpty(
            MyLocationFilterSet(params, self.queryset).qs, self.queryset.filter(asn__exact="12345")
        )
        params = {"q": "123"}
        # Both querysets are empty so we dont use assertQuerysetEqualAndNotEmpty here.
        self.assertQuerysetEqual(MyLocationFilterSet(params, self.queryset).qs, self.queryset.filter(asn__exact="123"))

        # Further an invalid type (e.g. dict) will just result in the predicate for ASN to be skipped
        class MyLocationFilterSet2(dcim_filters.LocationFilterSet):
            """Overload the default just to illustrate that it's all we're testing for here."""

            q = filters.SearchFilter(filter_predicates={"asn": {"lookup_expr": "exact", "preprocessor": dict}})

        params = {"q": "12345"}
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


class LookupIsNullTest(TestCase, testing.NautobotTestCaseMixin):
    """
    Validate isnull is properly applied and filtering.
    """

    platform_queryset = dcim_models.Platform.objects.all()
    platform_filterset = dcim_filters.PlatformFilterSet
    circuit_queryset = Circuit.objects.all()
    circuit_filterset = CircuitFilterSet
    device_queryset = dcim_models.Device.objects.all()
    device_filterset = dcim_filters.DeviceFilterSet

    @classmethod
    def setUpTestData(cls):
        location_type = dcim_models.LocationType.objects.create(name="Location Type 1")
        location_status = extras_models.Status.objects.get_for_model(dcim_models.Location).first()
        location = dcim_models.Location.objects.create(
            name="Location 1",
            location_type=location_type,
            status=location_status,
        )
        manufacturer = dcim_models.Manufacturer.objects.create(name="Manufacturer 1")
        dcim_models.Platform.objects.create(name="Platform 1")
        platform = dcim_models.Platform.objects.create(name="Platform 2", manufacturer=manufacturer)

        device_type = dcim_models.DeviceType.objects.create(
            manufacturer=manufacturer,
            model="Model 1",
            is_full_depth=True,
        )
        device_role = extras_models.Role.objects.create(name="Active Test")
        device_role.content_types.add(ContentType.objects.get_for_model(dcim_models.Device))

        device_status = extras_models.Status.objects.get_for_model(dcim_models.Device).first()

        dcim_models.Device.objects.create(
            name="Device 1",
            device_type=device_type,
            role=device_role,
            platform=platform,
            location=location,
            status=device_status,
        )
        dcim_models.Device.objects.create(
            device_type=device_type,
            role=device_role,
            platform=platform,
            location=location,
            status=device_status,
        )

        provider = Provider.objects.create(name="provider 1", asn=1)
        circuit_type = CircuitType.objects.create(name="Circuit Type 1")
        circuit_status = extras_models.Status.objects.get_for_model(dcim_models.Location).first()

        Circuit.objects.create(
            cid="Circuit 1",
            provider=provider,
            install_date=datetime.date(2020, 1, 1),
            commit_rate=1000,
            circuit_type=circuit_type,
            status=circuit_status,
        )
        Circuit.objects.create(
            cid="Circuit 2",
            provider=provider,
            circuit_type=circuit_type,
            status=circuit_status,
        )

    def test_isnull_on_fk(self):
        """Test that the `isnull` filter is applied for True and False queries on foreign key fields."""
        params = {"manufacturer__isnull": True}
        self.assertQuerysetEqualAndNotEmpty(
            dcim_filters.PlatformFilterSet(params, self.platform_queryset).qs,
            dcim_models.Platform.objects.filter(manufacturer__isnull=True),
        )
        params = {"manufacturer__isnull": False}
        self.assertQuerysetEqualAndNotEmpty(
            dcim_filters.PlatformFilterSet(params, self.platform_queryset).qs,
            dcim_models.Platform.objects.filter(manufacturer__isnull=False),
        )

    def test_isnull_on_integer(self):
        """Test that the `isnull` filter is applied for True and False queries on integer fields."""
        params = {"commit_rate__isnull": True}
        self.assertQuerysetEqualAndNotEmpty(
            CircuitFilterSet(params, self.circuit_queryset).qs,
            Circuit.objects.filter(commit_rate__isnull=True),
        )
        params = {"commit_rate__isnull": False}
        self.assertQuerysetEqualAndNotEmpty(
            CircuitFilterSet(params, self.circuit_queryset).qs,
            Circuit.objects.filter(commit_rate__isnull=False),
        )

    def test_isnull_on_date(self):
        """Test that the `isnull` filter is applied for True and False queries on datetime fields."""
        params = {"install_date__isnull": True}
        self.assertQuerysetEqualAndNotEmpty(
            CircuitFilterSet(params, self.circuit_queryset).qs,
            Circuit.objects.filter(install_date__isnull=True),
        )
        params = {"install_date__isnull": False}
        self.assertQuerysetEqualAndNotEmpty(
            CircuitFilterSet(params, self.circuit_queryset).qs,
            Circuit.objects.filter(install_date__isnull=False),
        )

    def test_isnull_on_char(self):
        """Test that the `isnull` filter is applied for True and False queries on char fields."""
        params = {"name__isnull": True}
        self.assertQuerysetEqualAndNotEmpty(
            dcim_filters.DeviceFilterSet(params, self.device_queryset).qs,
            dcim_models.Device.objects.filter(name__isnull=True),
        )
        params = {"name__isnull": False}
        self.assertQuerysetEqualAndNotEmpty(
            dcim_filters.DeviceFilterSet(params, self.device_queryset).qs,
            dcim_models.Device.objects.filter(name__isnull=False),
        )


class FilterTypeTest(TestCase):
    client_class = testing.NautobotTestClient

    def test_numberfilter(self):
        """
        Simple test to show the bug identified in https://github.com/nautobot/nautobot/issues/2837 no longer exists
        """
        user = get_user_model().objects.create_user(username="testuser", is_superuser=True)
        self.client.force_login(user)
        prefix_list_url = reverse(lookup.get_route_for_model(ipam_models.Prefix, "list"))
        response = self.client.get(f"{prefix_list_url}?prefix_length__lte=20")
        self.assertNotContains(response, "Invalid filters were specified")
