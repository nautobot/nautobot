from django.contrib.contenttypes.models import ContentType
from django.test import SimpleTestCase

from nautobot.core.management.commands.generate_searchable_fields import (
    collect_searchable_fields,
    render_yaml,
    SEARCHABLE_FIELDS_YAML,
)
from nautobot.core.templatetags.helpers import searchable_fields_for_content_type
from nautobot.core.utils.lookup import get_searchable_fields_for_model
from nautobot.dcim.models import Location


class SearchableFieldsDocsTestCase(SimpleTestCase):
    """Ensure the committed searchable_fields.yaml documentation artifact stays in sync with the code."""

    def test_committed_artifact_is_up_to_date(self):
        expected = render_yaml(collect_searchable_fields())
        actual = SEARCHABLE_FIELDS_YAML.read_text() if SEARCHABLE_FIELDS_YAML.exists() else ""
        self.assertEqual(
            actual,
            expected,
            msg=(
                f"{SEARCHABLE_FIELDS_YAML.name} is out of date. "
                "Run `nautobot-server generate_searchable_fields` and commit the result."
            ),
        )


class GetSearchableFieldsForModelTestCase(SimpleTestCase):
    """Test the introspection helper shared by the docs generator and the search bar tooltip."""

    def test_returns_sorted_fields_for_model_with_search_filter(self):
        fields = get_searchable_fields_for_model(Location)
        self.assertIsInstance(fields, list)
        self.assertEqual(fields, sorted(fields))
        # `name` is declared and `id` is always layered in by SearchFilter's default predicates.
        self.assertIn("name", fields)
        self.assertIn("id", fields)

    def test_returns_none_for_model_without_filterset(self):
        # Django's ContentType has no Nautobot FilterSet / `q` SearchFilter.
        self.assertIsNone(get_searchable_fields_for_model(ContentType))


class SearchableFieldsForContentTypeTagTestCase(SimpleTestCase):
    """Test the template tag that drives the search bar help tooltip."""

    class _FakeContentType:
        """Stand-in for a ContentType that avoids a database lookup."""

        def __init__(self, model):
            self._model = model

        def model_class(self):
            return self._model

    def test_returns_fields_for_content_type(self):
        self.assertEqual(
            searchable_fields_for_content_type(self._FakeContentType(Location)),
            get_searchable_fields_for_model(Location),
        )

    def test_returns_none_without_content_type(self):
        self.assertIsNone(searchable_fields_for_content_type(None))

    def test_returns_none_for_unresolvable_model(self):
        self.assertIsNone(searchable_fields_for_content_type(self._FakeContentType(None)))
