"""
django-slugger
~~~~~

:copyright: (c) 2017-2018 Dmitry Pechnikov
:license: MIT, see NOTICE for more details.
"""

from datetime import date

from django.core import checks

from nautobot.utilities.testing import TestCase
from nautobot.core.fields import AutoSlugField

from dummy_plugin import models


class TestAutoSlugField(TestCase):
    def test_generated_slug(self):
        obj = models.AutoSlugModel.objects.create(slug="", title="Test 1")

        assert obj.slug == "test-1"

    def test_specified_slug(self):
        obj = models.UniqueAutoSlugModel.objects.create(slug="manual-slug", title="Test 1")

        assert obj.slug == "manual-slug", "manual slug should override auto-generated one"

    def test_exceeds_max_length(self):
        obj = models.AutoSlugModel.objects.create(title="x" * 20)

        assert obj.slug == "x" * 10

    def test_fully_match_slug_field(self):
        models.UniqueAutoSlugModel.objects.bulk_create(
            [
                models.UniqueAutoSlugModel(slug="some-test"),
                models.UniqueAutoSlugModel(slug="test"),
                models.UniqueAutoSlugModel(slug="test-1"),
            ]
        )
        obj = models.UniqueAutoSlugModel.objects.create(slug="", title="Test")

        assert obj.slug == "test-2", "taken slugs should be from instances which slug fully " "matches the slug field"

    def test_add_suffix(self):
        models.UniqueAutoSlugModel.objects.create(slug="test")
        obj = models.UniqueAutoSlugModel.objects.create(slug="", title="Test")

        assert obj.slug == "test-1"

    def test_generated_slug_match_slug_with_suffix(self):
        models.UniqueAutoSlugModel.objects.create(slug="test-1")
        obj = models.UniqueAutoSlugModel.objects.create(slug="", title="Test 1")

        assert obj.slug == "test-1-1", "add suffix instead of incrementing existing suffix"

    def test_suffix_increment(self):
        models.UniqueAutoSlugModel.objects.bulk_create(
            [
                models.UniqueAutoSlugModel(slug="test"),
                models.UniqueAutoSlugModel(slug="test-1"),
                models.UniqueAutoSlugModel(slug="test-3"),
            ]
        )
        obj = models.UniqueAutoSlugModel.objects.create(slug="", title="Test")

        assert obj.slug == "test-2", "suffix increment should be the smallest available value"

    def test_regenerate_slug(self):
        obj = models.UniqueAutoSlugModel.objects.create(slug="", title="Test")
        obj.slug = ""
        obj.save()

        assert obj.slug == "test", "object slug should not be used for suffix generation"

    def test_only_suffixed_slug_exists(self):
        models.UniqueAutoSlugModel.objects.create(slug="test-1")
        obj = models.UniqueAutoSlugModel.objects.create(slug="", title="Test")

        assert obj.slug == "test", "do not use suffix if original slug is not taken"

    def test_unique_for_date(self):
        models.UniqueForAutoSlugModel.objects.create(
            slug="test", unique_date=date(2000, 1, 1), unique_month=date(2000, 1, 1), unique_year=date(2000, 1, 1)
        )

        unique_for_date = models.UniqueForAutoSlugModel.objects.create(
            slug="",
            title="test",
            unique_date=date(2000, 1, 1),
            unique_month=date(2000, 2, 1),
            unique_year=date(2001, 1, 1),
        )

        assert unique_for_date.slug == "test-1"

    def test_unique_for_month(self):
        models.UniqueForAutoSlugModel.objects.create(
            slug="test", unique_date=date(2000, 1, 1), unique_month=date(2000, 1, 1), unique_year=date(2000, 1, 1)
        )

        unique_for_month = models.UniqueForAutoSlugModel.objects.create(
            slug="",
            title="test",
            unique_date=date(2000, 1, 2),
            unique_month=date(2000, 1, 1),
            unique_year=date(2001, 1, 1),
        )

        assert unique_for_month.slug == "test-1"

    def test_unique_for_year(self):
        models.UniqueForAutoSlugModel.objects.create(
            slug="test", unique_date=date(2000, 1, 1), unique_month=date(2000, 1, 1), unique_year=date(2000, 1, 1)
        )

        unique_for_year = models.UniqueForAutoSlugModel.objects.create(
            slug="",
            title="test",
            unique_date=date(2000, 1, 2),
            unique_month=date(2000, 2, 1),
            unique_year=date(2000, 1, 1),
        )

        assert unique_for_year.slug == "test-1"

    def test_multiple_unique_together_constraints(self):
        # unique_together = (
        #     ('created', 'field_1'),
        #     ('slug', 'field_1',),
        #     ('slug', 'field_2', 'field_3'),
        # )
        models.UniqueTogetherAutoSlugModel.objects.create(
            slug="test",
            field_1="1-1",
            field_2="2-1",
            field_3="3-1",
        )

        # violate only field_1 constraint
        field_1 = models.UniqueTogetherAutoSlugModel.objects.create(
            slug="",
            title="test",
            field_1="1-1",
            field_2="2-2",
            field_3="3-2",
        )
        # violate only field_2/field_3 constraint
        field_2_3 = models.UniqueTogetherAutoSlugModel.objects.create(
            slug="",
            title="test",
            field_1="1-2",
            field_2="2-1",
            field_3="3-1",
        )
        # violate both constraints
        both = models.UniqueTogetherAutoSlugModel.objects.create(
            slug="",
            title="test",
            field_1="1-1",
            field_2="2-2",
            field_3="3-2",
        )

        assert field_1.slug == "test-1"
        assert field_2_3.slug == "test-1"
        assert both.slug == "test-2"

    def test_unique_together_multi_table_inheritance(self):
        models.ChildUniqueTogetherAutoSlugModel.objects.create(
            slug="test",
            field_1="1-1",
            field_2="2-1",
            field_3="3-1",
        )

        obj = models.ChildUniqueTogetherAutoSlugModel.objects.create(
            title="test",
            slug="",
            field_1="1-2",
            field_2="2-1",
            field_3="3-1",
        )

        assert obj.slug == "test-1"

    def test_both_unique_for_and_unique_together(self):
        # unique_together = ('slug', 'field_1')
        models.MixedUniqueAutoSlugModel.objects.create(
            slug="test",
            unique_date=date(2000, 1, 1),
            field_1="1-1",
        )

        unique_for = models.MixedUniqueAutoSlugModel.objects.create(
            slug="",
            title="test",
            unique_date=date(2000, 1, 1),
            field_1="1-2",
        )
        unique_together = models.MixedUniqueAutoSlugModel.objects.create(
            slug="",
            title="test",
            unique_date=date(2000, 1, 2),
            field_1="1-1",
        )

        assert unique_for.slug == "test-1"
        assert unique_together.slug == "test-1"

    def test_custom_slugify_function(self):
        obj = models.CustomAutoSlugModel.objects.create(slug="", title="Test")

        assert obj.slug == "custom-Test"

    def test_form_field_is_not_required(self):
        field = AutoSlugField(populate_from="title")

        assert not field.formfield().required

    def test_field_deconstruction(self):
        field = AutoSlugField(populate_from="title", slugify=models.custom_slugify)

        name, path, args, kwargs = field.deconstruct()

        assert kwargs["populate_from"] == "title"
        assert kwargs["slugify"] == models.custom_slugify

    def test_model_inheritance(self):
        models.Child1Model.objects.create(title="test", slug="")

        obj = models.Child2Model.objects.create(title="test", slug="")

        assert obj.slug == "test-1"
