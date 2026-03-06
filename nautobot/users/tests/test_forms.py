from django.contrib.admin.models import ADDITION, CHANGE, DELETION
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from nautobot.apps.testing import FormTestCases
from nautobot.users.forms import LogEntryFilterForm
from nautobot.users.models import LogEntry

User = get_user_model()


class LogEntryFilterFormTest(FormTestCases.BaseFormTestCase):
    form_class = LogEntryFilterForm

    def test_field_order(self):
        form = LogEntryFilterForm()
        self.assertEqual(form.field_order, ["q", "user", "content_type", "action_flag"])

    def test_model_and_optional_fields(self):
        form = LogEntryFilterForm()
        self.assertEqual(form.model, LogEntry)
        self.assertFalse(form.fields["user"].required)
        self.assertFalse(form.fields["content_type"].required)
        self.assertFalse(form.fields["action_flag"].required)

    def test_action_flag_choices(self):
        form = LogEntryFilterForm()
        action_values = {str(value) for value, _label in form.fields["action_flag"].choices if value != ""}
        self.assertTrue({str(ADDITION), str(CHANGE), str(DELETION)}.issubset(action_values))

    def test_dynamic_querysets(self):
        form = LogEntryFilterForm()
        self.assertEqual(form.fields["user"].queryset.model, User)
        self.assertEqual(form.fields["content_type"].queryset.model, ContentType)
