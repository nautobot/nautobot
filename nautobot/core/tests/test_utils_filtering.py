
from django.core.exceptions import ValidationError

from nautobot.core.testing import TestCase
from nautobot.core.utils import filtering
from nautobot.dcim.filters import LocationFilterSet
from nautobot.dcim.models import Location
from nautobot.extras.models import Tag


class TableTestCase(TestCase):
    def test_build_filter_dict_invalid_form_raises_validation_error(self):
        with self.assertRaises(ValidationError) as cm:
            filtering.build_filter_dict_from_filterset(
                LocationFilterSet,
                {"asn": "invalid"},
            )

        self.assertEqual(cm.exception.message_dict, {"asn": ["Enter a whole number."]})

    def test_build_filter_dict_simple_field(self):
        result = filtering.build_filter_dict_from_filterset(
            LocationFilterSet,
            {"name": ["Location A"]},
        )

        self.assertEqual(result, {"name": ["Location A"]})

    def test_build_filter_dict_integer_field(self):
        result = filtering.build_filter_dict_from_filterset(
            LocationFilterSet,
            {"asn": [123]},
        )

        self.assertEqual(result, {"asn": [123]})

    def test_build_filter_dict_model_choice_stores_pk(self):
        parent = Location.objects.first()

        result = filtering.build_filter_dict_from_filterset(
            LocationFilterSet,
            {"parent": [str(parent)]},
        )

        self.assertEqual(result, {"parent": [str(parent)]})

    def test_build_filter_dict_model_multiple_choice_stores_pk_list(self):
        Tag.objects.create(name="tag1")
        Tag.objects.create(name="tag2")

        result = filtering.build_filter_dict_from_filterset(
            LocationFilterSet,
            {"tags": ["tag1", "tag2"]},
        )

        self.assertEqual(
            result,
            {"tags": ["tag1", "tag2"]},
        )

    def test_build_filter_dict_drops_empty_values(self):
        result = filtering.build_filter_dict_from_filterset(
            LocationFilterSet,
            {"name": ""},
        )

        self.assertEqual(result, {})
