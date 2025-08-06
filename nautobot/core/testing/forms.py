from django.test import tag, TestCase

from nautobot.core.api.constants import NON_FILTER_QUERY_PARAMS
from nautobot.core.forms.fields import DynamicModelChoiceMixin
from nautobot.core.utils.lookup import get_filterset_for_model


# TODO(timizuo): All Form Test cases should inherit from FormTestCases
@tag("unit")
class FormTestCases:
    class BaseFormTestCase(TestCase):
        """Base class for generic form tests."""

        form_class = None

        def test_form_dynamic_model_choice_fields_query_params(self):
            for field_name, field_class in self.form_class.declared_fields.items():
                if not isinstance(field_class, DynamicModelChoiceMixin):
                    continue
                with self.subTest(f"Assert {self.form_class.__name__}.{field_name} query_params are valid."):
                    query_params_fields = set(field_class.query_params.keys())
                    query_params_fields = query_params_fields - set(NON_FILTER_QUERY_PARAMS)
                    if not query_params_fields:
                        self.skipTest(f"{self.form_class.__name__}.{field_name} has no query_params")
                    field_model = field_class.queryset.model
                    filterset_class = get_filterset_for_model(field_model)
                    filterset_fields = set(filterset_class().filters.keys())
                    invalid_query_params = query_params_fields - filterset_fields
                    self.assertFalse(
                        invalid_query_params,
                        f"{invalid_query_params} are invalid query_params fields for {self.form_class.__name__}.{field_name}",
                    )
