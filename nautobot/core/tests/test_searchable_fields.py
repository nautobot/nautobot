from django.test import SimpleTestCase

from nautobot.core.management.commands.generate_searchable_fields import (
    collect_searchable_fields,
    render_yaml,
    SEARCHABLE_FIELDS_YAML,
)


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
