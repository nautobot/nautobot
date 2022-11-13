import django_filters
from django.conf import settings
from django.db import models
from django.test import TestCase
from mptt.fields import TreeForeignKey
from taggit.managers import TaggableManager

from nautobot.dcim.choices import DeviceFaceChoices
from nautobot.dcim.fields import MACAddressCharField
from nautobot.dcim.filters import DeviceFilterSet, SiteFilterSet
from nautobot.dcim.models import (
    Device,
    DeviceRole,
    DeviceType,
    Interface,
    Manufacturer,
    Platform,
    PowerPanel,
    Rack,
    Region,
    Site,
)
from nautobot.extras.models import Status, TaggedItem
from nautobot.utilities.filters import (
    BaseFilterSet,
    MACAddressFilter,
    MultiValueCharFilter,
    MultiValueDateFilter,
    MultiValueDateTimeFilter,
    MultiValueNumberFilter,
    MultiValueTimeFilter,
    NaturalKeyOrPKMultipleChoiceFilter,
    SearchFilter,
    TagFilter,
    TreeNodeMultipleChoiceFilter,
)
from nautobot.utilities.testing import FilterTestCases
from nautobot.utilities.testing import mixins


class TreeNodeMultipleChoiceFilterTest(TestCase):
    class SiteFilterSet(BaseFilterSet):
        region = TreeNodeMultipleChoiceFilter(queryset=Region.objects.all())

        class Meta:
            model = Site
            fields = []

    def setUp(self):

        super().setUp()

        self.region1 = Region.objects.create(name="Test Region 1", slug="test-region-1")
        self.region2 = Region.objects.create(name="Test Region 2", slug="test-region-2")
        self.region2a = Region.objects.create(name="Test Region 2A", slug="test-region-2a", parent=self.region2)
        self.region2ab = Region.objects.create(name="Test Region 2A-B", slug="test-region-2a-b", parent=self.region2a)
        self.site1 = Site.objects.create(region=self.region1, name="Test Site 1", slug="test-site1")
        self.site2 = Site.objects.create(region=self.region2, name="Test Site 2", slug="test-site2")
        self.site2a = Site.objects.create(region=self.region2a, name="Test Site 2a", slug="test-site2a")
        self.site2ab = Site.objects.create(region=self.region2ab, name="Test Site 2a-b", slug="test-site2a-b")
        self.site0 = Site.objects.create(region=None, name="Test Site 0", slug="test-site0")

        self.queryset = Site.objects.filter(name__icontains="Test Site")

    def test_filter_single_slug(self):

        kwargs = {"region": ["test-region-1"]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.site1])

    def test_filter_single_pk(self):

        kwargs = {"region": [self.region1.pk]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.site1])

    def test_filter_multiple_slug(self):

        kwargs = {"region": ["test-region-1", "test-region-2"]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.site1, self.site2, self.site2a, self.site2ab])

    def test_filter_null(self):

        kwargs = {"region": [settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.site0])

    def test_filter_combined_slug(self):

        kwargs = {"region": ["test-region-1", settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.site0, self.site1])

    def test_filter_combined_pk(self):

        kwargs = {"region": [self.region2.pk, settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.site0, self.site2, self.site2a, self.site2ab])

    def test_filter_single_slug_exclude(self):

        kwargs = {"region__n": ["test-region-1"]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.site0, self.site2, self.site2a, self.site2ab])

    def test_filter_single_pk_exclude(self):

        kwargs = {"region__n": [self.region2.pk]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.site0, self.site1])

    def test_filter_multiple_slug_exclude(self):

        kwargs = {"region__n": ["test-region-1", "test-region-2"]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.site0])

    def test_filter_null_exclude(self):

        kwargs = {"region__n": [settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.site1, self.site2, self.site2a, self.site2ab])

    def test_filter_combined_slug_exclude(self):

        kwargs = {"region__n": ["test-region-1", settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.site2, self.site2a, self.site2ab])

    def test_filter_combined_pk_exclude(self):

        kwargs = {"region__n": [self.region2.pk, settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqual(qs, [self.site1])

    def test_lookup_expr_param_ignored(self):
        """
        Test that the `lookup_expr` parameter is ignored when using this filter on filtersets.
        """
        # Since we deprecated `in` this should be ignored.
        f = TreeNodeMultipleChoiceFilter(queryset=Region.objects.all(), lookup_expr="in")
        self.assertEqual(f.lookup_expr, django_filters.conf.settings.DEFAULT_LOOKUP_EXPR)


class NaturalKeyOrPKMultipleChoiceFilterTest(TestCase, mixins.NautobotTestCaseMixin):
    class SiteFilterSet(BaseFilterSet):
        power_panels = NaturalKeyOrPKMultipleChoiceFilter(
            field_name="powerpanel",
            queryset=PowerPanel.objects.all(),
            to_field_name="name",
        )

        class Meta:
            model = Site
            fields = []

    queryset = Site.objects.all()
    filterset = SiteFilterSet

    def setUp(self):

        super().setUp()

        self.site0 = Site.objects.create(name="Test Site 0", slug="test-site0")
        self.site1 = Site.objects.create(name="Test Site 1", slug="test-site1")
        self.site2 = Site.objects.create(name="Test Site 2", slug="test-site2")

        self.power_panel1 = PowerPanel.objects.create(site=self.site1, name="test-power-panel1")
        self.power_panel2 = PowerPanel.objects.create(site=self.site2, name="test-power-panel2")
        self.power_panel2a = PowerPanel.objects.create(site=self.site2, name="test-power-panel2a")
        self.power_panel2b = PowerPanel.objects.create(site=self.site2, name="test-power-panel2b")
        self.power_panel3 = PowerPanel.objects.create(site=self.site1, name="test-power-panel3")
        self.power_panel3a = PowerPanel.objects.create(site=self.site2, name="test-power-panel3")

    def test_filter_single_name(self):

        kwargs = {"power_panels": ["test-power-panel1"]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqualAndNotEmpty(qs, [self.site1])

    def test_filter_single_pk(self):

        kwargs = {"power_panels": [self.power_panel1.pk]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqualAndNotEmpty(qs, [self.site1])

    def test_filter_multiple_name(self):

        kwargs = {"power_panels": ["test-power-panel1", "test-power-panel2"]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqualAndNotEmpty(qs, [self.site1, self.site2])

    def test_filter_duplicate_name(self):

        kwargs = {"power_panels": ["test-power-panel3"]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqualAndNotEmpty(qs, [self.site1, self.site2])

    def test_filter_null(self):

        kwargs = {"power_panels": [settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs
        expected_result = Site.objects.filter(powerpanel__isnull=True)

        self.assertQuerysetEqualAndNotEmpty(qs, expected_result)

    def test_filter_combined_name(self):

        kwargs = {"power_panels": ["test-power-panel1", settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs
        expected_result = Site.objects.filter(powerpanel__isnull=True) | Site.objects.filter(
            powerpanel__name="test-power-panel1"
        )

        self.assertQuerysetEqualAndNotEmpty(qs, expected_result)

    def test_filter_combined_pk(self):

        kwargs = {"power_panels": [self.power_panel2.pk, settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs
        expected_result = Site.objects.filter(powerpanel__isnull=True) | Site.objects.filter(
            powerpanel__pk=self.power_panel2.pk
        )

        self.assertQuerysetEqualAndNotEmpty(qs, expected_result)

    def test_filter_single_name_exclude(self):

        kwargs = {"power_panels__n": ["test-power-panel1"]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs
        expected_result = Site.objects.exclude(powerpanel__name="test-power-panel1")

        self.assertQuerysetEqualAndNotEmpty(qs, expected_result)

    def test_filter_single_pk_exclude(self):

        kwargs = {"power_panels__n": [self.power_panel2.pk]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs
        expected_result = Site.objects.exclude(powerpanel__pk=self.power_panel2.pk)

        self.assertQuerysetEqualAndNotEmpty(qs, expected_result)

    def test_filter_multiple_name_exclude(self):

        kwargs = {"power_panels__n": ["test-power-panel1", "test-power-panel2"]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs
        expected_result = Site.objects.exclude(powerpanel__name="test-power-panel1").exclude(
            powerpanel__name="test-power-panel2"
        )

        self.assertQuerysetEqualAndNotEmpty(qs, expected_result)

    def test_filter_duplicate_name_exclude(self):

        kwargs = {"power_panels__n": ["test-power-panel3"]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs
        expected_result = Site.objects.exclude(powerpanel__name="test-power-panel3")

        self.assertQuerysetEqualAndNotEmpty(qs, expected_result)

    def test_filter_null_exclude(self):

        kwargs = {"power_panels__n": [settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqualAndNotEmpty(qs, [self.site1, self.site2])

    def test_filter_combined_name_exclude(self):

        kwargs = {"power_panels__n": ["test-power-panel1", settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqualAndNotEmpty(qs, [self.site2])

    def test_filter_combined_pk_exclude(self):

        kwargs = {"power_panels__n": [self.power_panel2.pk, settings.FILTERS_NULL_CHOICE_VALUE]}
        qs = self.SiteFilterSet(kwargs, self.queryset).qs

        self.assertQuerysetEqualAndNotEmpty(qs, [self.site1])

    def test_get_filter_predicate(self):
        """
        Test that `get_filter_predicate()` has hybrid results depending on whether value is a UUID
        or a slug.
        """

        # Test UUID (pk)
        uuid_obj = self.power_panel1.pk
        kwargs = {"power_panels": [uuid_obj]}
        fs = self.SiteFilterSet(kwargs, self.queryset)
        self.assertQuerysetEqualAndNotEmpty(fs.qs, [self.site1])
        self.assertEqual(
            fs.filters["power_panels"].get_filter_predicate(uuid_obj),
            {"powerpanel": str(uuid_obj)},
        )

        # Test model instance (pk)
        instance = self.power_panel1
        kwargs = {"power_panels": [instance]}
        fs = self.SiteFilterSet(kwargs, self.queryset)
        self.assertQuerysetEqualAndNotEmpty(fs.qs, [self.site1])
        self.assertEqual(
            fs.filters["power_panels"].get_filter_predicate(instance),
            {"powerpanel": str(instance.pk)},
        )

        # Test string (name in this case)
        name = self.power_panel1.name
        kwargs = {"power_panels": [name]}
        fs = self.SiteFilterSet(kwargs, self.queryset)
        self.assertQuerysetEqualAndNotEmpty(fs.qs, [self.site1])
        self.assertEqual(
            fs.filters["power_panels"].get_filter_predicate(name),
            {"powerpanel__name": name},
        )


class TestModel(models.Model):
    """
    Test model used by BaseFilterSetTest for filter validation. Should never appear in a schema migration.
    """

    charfield = models.CharField(max_length=10)
    choicefield = models.IntegerField(choices=(("A", 1), ("B", 2), ("C", 3)))
    datefield = models.DateField()
    datetimefield = models.DateTimeField()
    integerfield = models.IntegerField()
    macaddressfield = MACAddressCharField()
    textfield = models.TextField()
    timefield = models.TimeField()
    treeforeignkeyfield = TreeForeignKey(to="self", on_delete=models.CASCADE)

    tags = TaggableManager(through=TaggedItem)


class BaseFilterSetTest(TestCase):
    """
    Ensure that a BaseFilterSet automatically creates the expected set of filters for each filter type.
    """

    class TestFilterSet(BaseFilterSet):
        charfield = django_filters.CharFilter()
        macaddressfield = MACAddressFilter()
        modelchoicefield = django_filters.ModelChoiceFilter(
            field_name="integerfield",  # We're pretending this is a ForeignKey field
            queryset=Site.objects.all(),
        )
        modelmultiplechoicefield = django_filters.ModelMultipleChoiceFilter(
            field_name="integerfield",  # We're pretending this is a ForeignKey field
            queryset=Site.objects.all(),
        )
        multiplechoicefield = django_filters.MultipleChoiceFilter(field_name="choicefield")
        multivaluecharfield = MultiValueCharFilter(field_name="charfield")
        tagfield = TagFilter()
        treeforeignkeyfield = TreeNodeMultipleChoiceFilter(queryset=TestModel.objects.all())

        class Meta:
            model = TestModel
            fields = (
                "charfield",
                "choicefield",
                "datefield",
                "datetimefield",
                "integerfield",
                "macaddressfield",
                "modelchoicefield",
                "modelmultiplechoicefield",
                "multiplechoicefield",
                "tagfield",
                "textfield",
                "timefield",
                "treeforeignkeyfield",
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
        self.assertIsInstance(self.filters["macaddressfield"], MACAddressFilter)
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
        self.assertIsInstance(self.filters["multivaluecharfield"], MultiValueCharFilter)
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
        self.assertIsInstance(self.filters["textfield"], MultiValueCharFilter)
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
        self.assertIsInstance(self.filters["datefield"], MultiValueDateFilter)
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
        self.assertIsInstance(self.filters["datetimefield"], MultiValueDateTimeFilter)
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
        self.assertIsInstance(self.filters["integerfield"], MultiValueNumberFilter)
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

    def test_multi_value_time_filter(self):
        self.assertIsInstance(self.filters["timefield"], MultiValueTimeFilter)
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
        self.assertIsInstance(self.filters["multiplechoicefield"], django_filters.MultipleChoiceFilter)
        self.assertEqual(self.filters["multiplechoicefield"].lookup_expr, "exact")
        self.assertEqual(self.filters["multiplechoicefield"].exclude, False)
        self.assertEqual(self.filters["multiplechoicefield__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["multiplechoicefield__n"].exclude, True)
        self.assertEqual(self.filters["multiplechoicefield__ie"].lookup_expr, "iexact")
        self.assertEqual(self.filters["multiplechoicefield__ie"].exclude, False)
        self.assertEqual(self.filters["multiplechoicefield__nie"].lookup_expr, "iexact")
        self.assertEqual(self.filters["multiplechoicefield__nie"].exclude, True)
        self.assertEqual(self.filters["multiplechoicefield__ic"].lookup_expr, "icontains")
        self.assertEqual(self.filters["multiplechoicefield__ic"].exclude, False)
        self.assertEqual(self.filters["multiplechoicefield__nic"].lookup_expr, "icontains")
        self.assertEqual(self.filters["multiplechoicefield__nic"].exclude, True)
        self.assertEqual(self.filters["multiplechoicefield__isw"].lookup_expr, "istartswith")
        self.assertEqual(self.filters["multiplechoicefield__isw"].exclude, False)
        self.assertEqual(self.filters["multiplechoicefield__nisw"].lookup_expr, "istartswith")
        self.assertEqual(self.filters["multiplechoicefield__nisw"].exclude, True)
        self.assertEqual(self.filters["multiplechoicefield__iew"].lookup_expr, "iendswith")
        self.assertEqual(self.filters["multiplechoicefield__iew"].exclude, False)
        self.assertEqual(self.filters["multiplechoicefield__niew"].lookup_expr, "iendswith")
        self.assertEqual(self.filters["multiplechoicefield__niew"].exclude, True)
        self.assertEqual(self.filters["multiplechoicefield__re"].lookup_expr, "regex")
        self.assertEqual(self.filters["multiplechoicefield__re"].exclude, False)
        self.assertEqual(self.filters["multiplechoicefield__nre"].lookup_expr, "regex")
        self.assertEqual(self.filters["multiplechoicefield__nre"].exclude, True)
        self.assertEqual(self.filters["multiplechoicefield__ire"].lookup_expr, "iregex")
        self.assertEqual(self.filters["multiplechoicefield__ire"].exclude, False)
        self.assertEqual(self.filters["multiplechoicefield__nire"].lookup_expr, "iregex")
        self.assertEqual(self.filters["multiplechoicefield__nire"].exclude, True)

    def test_tag_filter(self):
        self.assertIsInstance(self.filters["tagfield"], TagFilter)
        self.assertEqual(self.filters["tagfield"].lookup_expr, "exact")
        self.assertEqual(self.filters["tagfield"].exclude, False)
        self.assertEqual(self.filters["tagfield__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["tagfield__n"].exclude, True)

    def test_tree_node_multiple_choice_filter(self):
        self.assertIsInstance(self.filters["treeforeignkeyfield"], TreeNodeMultipleChoiceFilter)
        self.assertEqual(self.filters["treeforeignkeyfield"].lookup_expr, "exact")
        self.assertEqual(self.filters["treeforeignkeyfield"].exclude, False)
        self.assertEqual(self.filters["treeforeignkeyfield__n"].lookup_expr, "exact")
        self.assertEqual(self.filters["treeforeignkeyfield__n"].exclude, True)


class DynamicFilterLookupExpressionTest(TestCase):
    """
    Validate function of automatically generated filters using the Device model as an example.
    """

    device_queryset = Device.objects.all()
    device_filterset = DeviceFilterSet
    site_queryset = Site.objects.all()
    site_filterset = SiteFilterSet

    @classmethod
    def setUpTestData(cls):

        manufacturers = (
            Manufacturer(name="Manufacturer 1", slug="manufacturer-1"),
            Manufacturer(name="Manufacturer 2", slug="manufacturer-2"),
            Manufacturer(name="Manufacturer 3", slug="manufacturer-3"),
        )
        Manufacturer.objects.bulk_create(manufacturers)

        device_types = (
            DeviceType(
                manufacturer=manufacturers[0],
                model="Model 1",
                slug="model-1",
                is_full_depth=True,
            ),
            DeviceType(
                manufacturer=manufacturers[1],
                model="Model 2",
                slug="model-2",
                is_full_depth=True,
            ),
            DeviceType(
                manufacturer=manufacturers[2],
                model="Model 3",
                slug="model-3",
                is_full_depth=False,
            ),
        )
        DeviceType.objects.bulk_create(device_types)

        device_roles = (
            DeviceRole(name="Device Role 1", slug="device-role-1"),
            DeviceRole(name="Device Role 2", slug="device-role-2"),
            DeviceRole(name="Device Role 3", slug="device-role-3"),
        )
        DeviceRole.objects.bulk_create(device_roles)

        device_statuses = Status.objects.get_for_model(Device)
        device_status_map = {ds.slug: ds for ds in device_statuses.all()}

        platforms = (
            Platform(name="Platform 1", slug="platform-1"),
            Platform(name="Platform 2", slug="platform-2"),
            Platform(name="Platform 3", slug="platform-3"),
        )
        Platform.objects.bulk_create(platforms)

        cls.regions = Region.objects.filter(sites__isnull=False)[:3]

        cls.sites = (
            Site.objects.filter(region=cls.regions[0]).first(),
            Site.objects.filter(region=cls.regions[1]).first(),
            Site.objects.filter(region=cls.regions[2]).first(),
        )
        cls.sites[0].asn = 65001
        cls.sites[1].asn = 65101
        cls.sites[2].asn = 65201

        racks = (
            Rack(name="Rack 1", site=cls.sites[0]),
            Rack(name="Rack 2", site=cls.sites[1]),
            Rack(name="Rack 3", site=cls.sites[2]),
        )
        Rack.objects.bulk_create(racks)

        devices = (
            Device(
                name="Device 1",
                device_type=device_types[0],
                device_role=device_roles[0],
                platform=platforms[0],
                serial="ABC",
                asset_tag="1001",
                site=cls.sites[0],
                rack=racks[0],
                position=1,
                face=DeviceFaceChoices.FACE_FRONT,
                status=device_status_map["active"],
                local_context_data={"foo": 123},
                comments="Device 1 comments",
            ),
            Device(
                name="Device 2",
                device_type=device_types[1],
                device_role=device_roles[1],
                platform=platforms[1],
                serial="DEF",
                asset_tag="1002",
                site=cls.sites[1],
                rack=racks[1],
                position=2,
                face=DeviceFaceChoices.FACE_FRONT,
                status=device_status_map["staged"],
                comments="Device 2 comments",
            ),
            Device(
                name="Device 3",
                device_type=device_types[2],
                device_role=device_roles[2],
                platform=platforms[2],
                serial="GHI",
                asset_tag="1003",
                site=cls.sites[2],
                rack=racks[2],
                position=3,
                face=DeviceFaceChoices.FACE_REAR,
                status=device_status_map["failed"],
                comments="Device 3 comments",
            ),
        )
        Device.objects.bulk_create(devices)

        interfaces = (
            Interface(device=devices[0], name="Interface 1", mac_address="00-00-00-00-00-01"),
            Interface(device=devices[0], name="Interface 2", mac_address="aa-00-00-00-00-01"),
            Interface(device=devices[1], name="Interface 3", mac_address="00-00-00-00-00-02"),
            Interface(device=devices[1], name="Interface 4", mac_address="bb-00-00-00-00-02"),
            Interface(device=devices[2], name="Interface 5", mac_address="00-00-00-00-00-03"),
            Interface(device=devices[2], name="Interface 6", mac_address="cc-00-00-00-00-03"),
        )
        Interface.objects.bulk_create(interfaces)

    class DeviceFilterSetWithComments(DeviceFilterSet):
        class Meta:
            model = Device
            fields = [
                "comments",
            ]

    def test_site_name_negation(self):
        params = {"name__n": ["Site 1"]}
        self.assertQuerysetEqual(SiteFilterSet(params, self.site_queryset).qs, Site.objects.exclude(name="Site 1"))

    def test_site_slug_icontains(self):
        params = {"slug__ic": ["-1"]}
        self.assertQuerysetEqual(
            SiteFilterSet(params, self.site_queryset).qs, Site.objects.filter(slug__icontains="-1")
        )

    def test_site_slug_icontains_negation(self):
        params = {"slug__nic": ["-1"]}
        self.assertQuerysetEqual(
            SiteFilterSet(params, self.site_queryset).qs, Site.objects.exclude(slug__icontains="-1")
        )

    def test_site_slug_startswith(self):
        startswith = Site.objects.first().slug[:3]
        params = {"slug__isw": [startswith]}
        self.assertQuerysetEqual(
            SiteFilterSet(params, self.site_queryset).qs, Site.objects.filter(slug__istartswith=startswith)
        )

    def test_site_slug_startswith_negation(self):
        startswith = Site.objects.first().slug[:3]
        params = {"slug__nisw": [startswith]}
        self.assertQuerysetEqual(
            SiteFilterSet(params, self.site_queryset).qs, Site.objects.exclude(slug__icontains=startswith)
        )

    def test_site_slug_endswith(self):
        endswith = Site.objects.first().slug[len(Site.objects.first().slug) - 2 : len(Site.objects.first().slug)]
        params = {"slug__iew": [endswith]}
        self.assertQuerysetEqual(
            SiteFilterSet(params, self.site_queryset).qs, Site.objects.filter(slug__iendswith=endswith)
        )

    def test_site_slug_endswith_negation(self):
        endswith = Site.objects.first().slug[len(Site.objects.first().slug) - 2 : len(Site.objects.first().slug)]
        params = {"slug__niew": [endswith]}
        self.assertQuerysetEqual(
            SiteFilterSet(params, self.site_queryset).qs, Site.objects.exclude(slug__iendswith=endswith)
        )

    def test_site_slug_regex(self):
        params = {"slug__re": ["-1$"]}
        self.assertQuerysetEqual(SiteFilterSet(params, self.site_queryset).qs, Site.objects.filter(slug__regex="-1$"))

    def test_site_slug_regex_negation(self):
        params = {"slug__nre": ["-1$"]}
        self.assertQuerysetEqual(SiteFilterSet(params, self.site_queryset).qs, Site.objects.exclude(slug__regex="-1$"))

    def test_site_slug_iregex(self):
        params = {"slug__ire": ["SITE"]}
        self.assertQuerysetEqual(SiteFilterSet(params, self.site_queryset).qs, Site.objects.filter(slug__iregex="SITE"))

    def test_site_slug_iregex_negation(self):
        params = {"slug__nire": ["SITE"]}
        self.assertQuerysetEqual(
            SiteFilterSet(params, self.site_queryset).qs, Site.objects.exclude(slug__iregex="SITE")
        )

    def test_site_asn_lt(self):
        asn = Site.objects.filter(asn__isnull=False).first().asn
        params = {"asn__lt": [asn]}
        self.assertQuerysetEqual(SiteFilterSet(params, self.site_queryset).qs, Site.objects.filter(asn__lt=asn))

    def test_site_asn_lte(self):
        asn = Site.objects.filter(asn__isnull=False).first().asn
        params = {"asn__lte": [asn]}
        self.assertQuerysetEqual(SiteFilterSet(params, self.site_queryset).qs, Site.objects.filter(asn__lte=asn))

    def test_site_asn_gt(self):
        asn = Site.objects.filter(asn__isnull=False).first().asn
        params = {"asn__gt": [asn]}
        self.assertQuerysetEqual(SiteFilterSet(params, self.site_queryset).qs, Site.objects.filter(asn__gt=asn))

    def test_site_asn_gte(self):
        asn = Site.objects.filter(asn__isnull=False).first().asn
        params = {"asn__gte": [asn]}
        self.assertQuerysetEqual(SiteFilterSet(params, self.site_queryset).qs, Site.objects.filter(asn__gte=asn))

    def test_site_region_negation(self):
        params = {"region__n": ["region-1"]}
        self.assertQuerysetEqual(
            SiteFilterSet(params, self.site_queryset).qs, Site.objects.exclude(region__slug="region-1")
        )

    def test_site_region_id_negation(self):
        params = {"region_id__n": [self.regions[0].pk]}
        self.assertQuerysetEqual(
            SiteFilterSet(params, self.site_queryset).qs,
            Site.objects.exclude(region__in=self.regions[0].get_descendants(include_self=True)),
        )

    def test_device_name_eq(self):
        params = {"name": ["Device 1"]}
        self.assertQuerysetEqual(
            DeviceFilterSet(params, self.device_queryset).qs, Device.objects.filter(name="Device 1")
        )

    def test_device_name_negation(self):
        params = {"name__n": ["Device 1"]}
        self.assertQuerysetEqual(
            DeviceFilterSet(params, self.device_queryset).qs, Device.objects.exclude(name="Device 1")
        )

    def test_device_name_startswith(self):
        params = {"name__isw": ["Device"]}
        self.assertQuerysetEqual(
            DeviceFilterSet(params, self.device_queryset).qs, Device.objects.filter(name__istartswith="Device")
        )

    def test_device_name_startswith_negation(self):
        params = {"name__nisw": ["Device 1"]}
        self.assertQuerysetEqual(
            DeviceFilterSet(params, self.device_queryset).qs, Device.objects.exclude(name__istartswith="Device 1")
        )

    def test_device_name_endswith(self):
        params = {"name__iew": [" 1"]}
        self.assertQuerysetEqual(
            DeviceFilterSet(params, self.device_queryset).qs, Device.objects.filter(name__iendswith=" 1")
        )

    def test_device_name_endswith_negation(self):
        params = {"name__niew": [" 1"]}
        self.assertQuerysetEqual(
            DeviceFilterSet(params, self.device_queryset).qs, Device.objects.exclude(name__iendswith=" 1")
        )

    def test_device_name_icontains(self):
        params = {"name__ic": [" 2"]}
        self.assertQuerysetEqual(
            DeviceFilterSet(params, self.device_queryset).qs, Device.objects.filter(name__icontains=" 2")
        )

    def test_device_name_icontains_negation(self):
        params = {"name__nic": [" "]}
        self.assertQuerysetEqual(
            DeviceFilterSet(params, self.device_queryset).qs, Device.objects.exclude(name__icontains=" ")
        )

    def test_device_mac_address_negation(self):
        params = {"mac_address__n": ["00-00-00-00-00-01", "aa-00-00-00-00-01"]}
        self.assertEqual(DeviceFilterSet(params, self.device_queryset).qs.count(), 2)

    def test_device_mac_address_startswith(self):
        params = {"mac_address__isw": ["aa:"]}
        self.assertEqual(DeviceFilterSet(params, self.device_queryset).qs.count(), 1)

    def test_device_mac_address_startswith_negation(self):
        params = {"mac_address__nisw": ["aa:"]}
        self.assertEqual(DeviceFilterSet(params, self.device_queryset).qs.count(), 2)

    def test_device_mac_address_endswith(self):
        params = {"mac_address__iew": [":02"]}
        self.assertEqual(DeviceFilterSet(params, self.device_queryset).qs.count(), 1)

    def test_device_mac_address_endswith_negation(self):
        params = {"mac_address__niew": [":02"]}
        self.assertEqual(DeviceFilterSet(params, self.device_queryset).qs.count(), 2)

    def test_device_mac_address_icontains(self):
        params = {"mac_address__ic": ["aa:", "bb"]}
        self.assertEqual(DeviceFilterSet(params, self.device_queryset).qs.count(), 2)

    def test_device_mac_address_icontains_negation(self):
        params = {"mac_address__nic": ["aa:", "bb"]}
        self.assertEqual(DeviceFilterSet(params, self.device_queryset).qs.count(), 1)

    def test_device_mac_address_regex(self):
        params = {"mac_address__re": ["^AA:"]}
        self.assertEqual(DeviceFilterSet(params, self.device_queryset).qs.count(), 1)

    def test_device_mac_address_iregex(self):
        params = {"mac_address__ire": ["^aa:"]}
        self.assertEqual(DeviceFilterSet(params, self.device_queryset).qs.count(), 1)

    def test_device_mac_address_regex_negation(self):
        params = {"mac_address__nre": ["^AA:"]}
        self.assertEqual(DeviceFilterSet(params, self.device_queryset).qs.count(), 2)

    def test_device_mac_address_iregex_negation(self):
        params = {"mac_address__nire": ["^aa:"]}
        self.assertEqual(DeviceFilterSet(params, self.device_queryset).qs.count(), 2)

    def test_device_comments_multiple_value_charfield(self):
        params = {"comments": ["Device 1 comments"]}
        self.assertQuerysetEqual(
            self.DeviceFilterSetWithComments(params, self.device_queryset).qs,
            Device.objects.filter(comments="Device 1 comments"),
        )
        params = {"comments": ["Device 1 comments", "Device 2 comments"]}
        self.assertQuerysetEqual(
            self.DeviceFilterSetWithComments(params, self.device_queryset).qs,
            Device.objects.filter(comments__in=["Device 1 comments", "Device 2 comments"]),
        )
        params = {"comments": ["Device 1 comments", "Device 2 comments", "Device 3 comments"]}
        self.assertQuerysetEqual(
            self.DeviceFilterSetWithComments(params, self.device_queryset).qs,
            Device.objects.filter(comments__in=["Device 1 comments", "Device 2 comments", "Device 3 comments"]),
        )

    def test_device_comments_multiple_value_charfield_regex(self):
        params = {"comments__re": ["^Device"]}
        self.assertQuerysetEqual(
            self.DeviceFilterSetWithComments(params, self.device_queryset).qs,
            Device.objects.filter(comments__regex="^Device"),
        )

    def test_device_comments_multiple_value_charfield_regex_negation(self):
        params = {"comments__nre": ["^Device"]}
        self.assertQuerysetEqual(
            self.DeviceFilterSetWithComments(params, self.device_queryset).qs,
            Device.objects.exclude(comments__regex="^Device"),
        )

    def test_device_comments_multiple_value_charfield_iregex(self):
        params = {"comments__ire": ["^device"]}
        self.assertQuerysetEqual(
            self.DeviceFilterSetWithComments(params, self.device_queryset).qs,
            Device.objects.filter(comments__iregex="^device"),
        )

    def test_device_comments_multiple_value_charfield_iregex_negation(self):
        params = {"comments__nire": ["^device"]}
        self.assertQuerysetEqual(
            self.DeviceFilterSetWithComments(params, self.device_queryset).qs,
            Device.objects.exclude(comments__iregex="^device"),
        )


class GetFiltersetTestValuesTest(FilterTestCases.BaseFilterTestCase):
    """Tests for `BaseFilterTestCase.get_filterset_test_values()`."""

    queryset = Site.objects.filter(name__startswith="getfiltersettest")
    exception_message = "Cannot find valid test data for Site field description"

    @classmethod
    def setUpTestData(cls):
        statuses = Status.objects.get_for_model(Site)
        cls.status_active = statuses.get(slug="active")

    def test_empty_queryset(self):
        with self.assertRaisesMessage(ValueError, self.exception_message):
            self.get_filterset_test_values("description")

    def test_object_return_count(self):
        for n in range(1, 11):
            Site.objects.create(
                name=f"getfiltersettestSite{n}", status=self.status_active, description=f"description {n}"
            )
        test_values = self.get_filterset_test_values("description", self.queryset)
        self.assertNotEqual(len(test_values), 0)
        self.assertNotEqual(len(test_values), self.queryset.count())

    def test_insufficient_unique_values(self):
        Site.objects.create(name="getfiltersettestUniqueSite", description="UniqueSite description")
        with self.assertRaisesMessage(ValueError, self.exception_message):
            self.get_filterset_test_values("description")
        Site.objects.create(name="getfiltersettestSite1", status=self.status_active)
        Site.objects.create(name="getfiltersettestSite2", status=self.status_active)
        with self.assertRaisesMessage(ValueError, self.exception_message):
            self.get_filterset_test_values("description")

    def test_no_unique_values(self):
        for n in range(1, 11):
            Site.objects.create(name=f"getfiltersettestSite{n}", status=self.status_active)
        for site in self.queryset:
            site.delete()
            with self.assertRaisesMessage(ValueError, self.exception_message):
                self.get_filterset_test_values("description")


class SearchFilterTest(TestCase, mixins.NautobotTestCaseMixin):
    """Tests for the `SearchFilter` filter class."""

    filterset_class = SiteFilterSet

    def setUp(self):

        super().setUp()

        self.region1 = Region.objects.create(name="Test Region 1", slug="test-region-1")
        self.region2 = Region.objects.create(name="Test Region 2", slug="test-region-2")
        self.site1 = Site.objects.create(region=self.region1, name="Test Site 1", slug="test-site1", asn=1234)
        self.site2 = Site.objects.create(region=self.region2, name="Test Site 2", slug="test-site2", asn=12345)
        self.site3 = Site.objects.create(region=None, name="Test Site 3", slug="test-site3")
        self.site4 = Site.objects.create(region=None, name="Test Site4", slug="test-site4")

        self.queryset = Site.objects.all()

    def get_filterset_count(self, params, klass=None):
        """To save ourselves some boilerplate."""
        if klass is None:
            klass = self.filterset_class
        return klass(params, self.queryset).qs.count()

    def test_default_icontains(self):
        """Test a default search for an "icontains" value."""
        params = {"q": "Test Site"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset_class(params, self.queryset).qs, self.queryset.filter(name__icontains="Test Site")
        )
        params = {"q": "Test Site 3"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset_class(params, self.queryset).qs, self.queryset.filter(name__icontains="Test Site 3")
        )
        # Trailing space should only match the first 3.
        params = {"q": "Test Site "}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset_class(params, self.queryset).qs, self.queryset.filter(name__icontains="Test Site ")
        )

    def test_default_exact(self):
        """Test a default search for an "exact" value."""
        params = {"q": "1234"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset_class(params, self.queryset).qs, self.queryset.filter(asn__exact="1234")
        )
        asn = Site.objects.exclude(asn="1234").values_list("asn", flat=True).first()
        params = {"q": str(asn)}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset_class(params, self.queryset).qs, self.queryset.filter(asn__exact=str(asn))
        )

    def test_default_id(self):
        """Test default search on "id" field."""
        # Search is iexact so UUID search for lower/upper return the same result.
        obj_pk = str(self.site1.pk)
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

        class MySiteFilterSet(SiteFilterSet):
            """Overload the default just to illustrate that it's all we're testing for here."""

            q = SearchFilter(filter_predicates={"asn": {"lookup_expr": "exact", "preprocessor": int}})

        params = {"q": "1234"}
        self.assertQuerysetEqualAndNotEmpty(
            MySiteFilterSet(params, self.queryset).qs, self.queryset.filter(asn__exact="1234")
        )
        params = {"q": "123"}
        # Both querysets are empty so we dont use assertQuerysetEqualAndNotEmpty here.
        self.assertQuerysetEqual(MySiteFilterSet(params, self.queryset).qs, self.queryset.filter(asn__exact="123"))

        # Further an invalid type (e.g. dict) will just result in the predicate for ASN to be skipped
        class MySiteFilterSet2(SiteFilterSet):
            """Overload the default just to illustrate that it's all we're testing for here."""

            q = SearchFilter(filter_predicates={"asn": {"lookup_expr": "exact", "preprocessor": dict}})

        params = {"q": "1234"}
        # Both querysets are empty so we dont use assertQuerysetEqualAndNotEmpty here.
        self.assertEqual(self.get_filterset_count(params, MySiteFilterSet2), 0)

    def test_typed_icontains(self):
        """Test a preprocessor to strip icontains (which wouldn't be by default)."""

        class MySiteFilterSet(SiteFilterSet):
            """Overload the default just to illustrate that it's all we're testing for here."""

            q = SearchFilter(filter_predicates={"name": {"lookup_expr": "icontains", "preprocessor": str.strip}})

        # Both searches should return the same results.
        params = {"q": "Test Site"}
        self.assertQuerysetEqualAndNotEmpty(
            MySiteFilterSet(params, self.queryset).qs, self.queryset.filter(name__icontains="Test Site")
        )
        params = {"q": "Test Site "}
        self.assertQuerysetEqualAndNotEmpty(
            MySiteFilterSet(params, self.queryset).qs, self.queryset.filter(name__icontains="Test Site")
        )

    def test_typed_invalid(self):
        """Test that incorrectly-typed predicate mappings are handled correctly."""
        # Bad preprocessor callable in expanded form
        with self.assertRaises(TypeError):
            barf = None

            class BarfSiteFilterSet(SiteFilterSet):  # pylint: disable=unused-variable
                q = SearchFilter(
                    filter_predicates={
                        "asn": {"preprocessor": barf, "lookup_expr": "exact"},
                    },
                )

        # Missing preprocessor callable in expanded form should also fail
        with self.assertRaises(TypeError):

            class MissingSiteFilterSet(SiteFilterSet):  # pylint: disable=unused-variable
                q = SearchFilter(filter_predicates={"asn": {"lookup_expr": "exact"}})

        # Incorrect lookup_info type (must be str or dict)
        with self.assertRaises(TypeError):

            class InvalidSiteFilterSet(SiteFilterSet):  # pylint: disable=unused-variable
                q = SearchFilter(filter_predicates={"asn": ["icontains"]})
