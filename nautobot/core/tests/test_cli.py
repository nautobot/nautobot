from nautobot.core.cli import migrate_deprecated_templates
from nautobot.core.testing import TestCase


class TestMigrateTemplates(TestCase):
    def test_template_replacements(self):
        """Verify that all old templates are replaced by a single new template."""
        audit_dict = {}
        for new_template, old_templates in migrate_deprecated_templates.TEMPLATE_REPLACEMENTS.items():
            for old_template in old_templates:
                self.assertNotIn(old_template, audit_dict)
                audit_dict[old_template] = new_template

    def test_replace_template_references_no_change(self):
        content = """
        {% extends "base.html" %}
        {% block content %}
        <h1>Hello, World!</h1>
        {% endblock %}
        """
        replaced_content, was_updated = migrate_deprecated_templates.replace_template_references(content)
        self.assertFalse(was_updated)
        self.assertEqual(replaced_content, content)

    def test_replace_template_references(self):
        original_content = """
        {% extends "generic/object_bulk_import.html" %}
        {% block content %}
        <h1>Hello, World!</h1>
        {% endblock %}
        """
        new_content = """
        {% extends "generic/object_bulk_create.html" %}
        {% block content %}
        <h1>Hello, World!</h1>
        {% endblock %}
        """
        replaced_content, was_updated = migrate_deprecated_templates.replace_template_references(original_content)
        self.assertTrue(was_updated)
        self.assertEqual(replaced_content, new_content)
