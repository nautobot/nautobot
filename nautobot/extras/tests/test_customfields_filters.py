from django.contrib.contenttypes.models import ContentType
from django.test import tag

from nautobot.core.testing import views
from nautobot.extras.choices import CustomFieldFilterLogicChoices, CustomFieldTypeChoices
from nautobot.extras.models import CustomField


@tag("unit")
class CustomFieldsFilters:
    class CustomFieldsFilterSetTestCaseMixin(views.TestCase):
        filter_matrix = {
            CustomFieldTypeChoices.TYPE_TEXT: {
                "value": "Lorem ipsum",
                "lookups": [
                    {
                        "name": "exact match",
                        "lookup": "",
                        "negated_lookup": "n",
                        "test_cases": [
                            {
                                "search": "foo",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": False},
                            },
                            {
                                "search": "Lorem ipsum",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": True},
                            },
                            {
                                "search": "lorem ipsum",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": False},
                            },
                            {
                                "search": "null",
                                "expected": {"no_key": False, "empty": False, "null": True, "value": False},
                            },
                        ],
                    },
                    {
                        "name": "icontains",
                        "lookup": "ic",
                        "negated_lookup": "nic",
                        "test_cases": [
                            {
                                "search": "foo",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": False},
                            },
                            {
                                "search": "Lorem",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": True},
                            },
                            {
                                "search": "lorem",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": True},
                            },
                            # {"search": "null",
                            #  "expected": {"no_key": True, "empty": False, "null": True, "value": False}}, # TODO: 500 atm
                        ],
                    },
                    {
                        "name": "istartswith",
                        "lookup": "isw",
                        "negated_lookup": "nisw",
                        "test_cases": [
                            {
                                "search": "foo",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": False},
                            },
                            {
                                "search": "Lorem",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": True},
                            },
                            {
                                "search": "lorem",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": True},
                            },
                            # {"search": "null",
                            #  "expected": {"no_key": True, "empty": False, "null": True, "value": False}}, # TODO: 500 atm
                        ],
                    },
                    {
                        "name": "iendswith",
                        "lookup": "iew",
                        "negated_lookup": "niew",
                        "test_cases": [
                            {
                                "search": "foo",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": False},
                            },
                            {
                                "search": "ipsum",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": True},
                            },
                            {
                                "search": "IPSUM",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": True},
                            },
                            # {"search": "null",
                            #  "expected": {"no_key": True, "empty": False, "null": True, "value": False}}, # TODO: 500 atm
                        ],
                    },
                    {
                        "name": "iexact, case-insensitive match",
                        "lookup": "ie",
                        "negated_lookup": "nie",
                        "test_cases": [
                            {
                                "search": "foo",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": False},
                            },
                            {
                                "search": "Lorem ipsum",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": True},
                            },
                            {
                                "search": "lorem ipsum",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": True},
                            },
                            {
                                "search": "null",
                                "expected": {"no_key": False, "empty": False, "null": True, "value": False},
                            },
                        ],
                    },
                    {
                        "name": "regex match (case-sensitive)",
                        "lookup": "re",
                        "negated_lookup": "nre",
                        "test_cases": [
                            {
                                "search": ".?foo",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": False},
                            },
                            {
                                "search": ".?ipsum",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": True},
                            },
                            {
                                "search": ".?IPSUM",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": False},
                            },
                            # {"search": "null",
                            #  "expected": {"no_key": True, "empty": False, "null": True, "value": False}}, # TODO: 500 atm
                        ],
                    },
                    {
                        "name": "regex match (case-insensitive)",
                        "lookup": "ire",
                        "negated_lookup": "nire",
                        "test_cases": [
                            {
                                "search": ".?foo",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": False},
                            },
                            {
                                "search": ".?ipsum",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": True},
                            },
                            {
                                "search": ".?IPSUM",
                                "expected": {"no_key": False, "empty": False, "null": False, "value": True},
                            },
                            # {"search": "null",
                            #  "expected": {"no_key": True, "empty": False, "null": True, "value": False}}, # TODO: 500 atm
                        ],
                    },
                ],
            }
        }

        @staticmethod
        def get_negated_test_cases(lookup, test_cases):
            negated_test_cases = []
            for test_case in test_cases:
                expected = {key: not value for key, value in test_case["expected"].items()}
                negated_test_cases.append((lookup, {"search": test_case["search"], "expected": expected}))
            return negated_test_cases

        def test_str_custom_field_filters(self):
            model = self.filterset.Meta.model
            test_data = self.filter_matrix[CustomFieldTypeChoices.TYPE_TEXT]

            cf_label = "test_label_str"
            cf = CustomField.objects.create(
                type=CustomFieldTypeChoices.TYPE_TEXT,
                label=cf_label,
                filter_logic=CustomFieldFilterLogicChoices.FILTER_EXACT,
            )
            cf.content_types.set([ContentType.objects.get_for_model(model)])

            i1, i2, i3, i4 = tested_instances = self.queryset.all()[:4]
            qs = self.queryset.filter(pk__in=tested_instances)

            # No-key object
            self.assertIsNone(i1._custom_field_data.get(cf_label))

            # Empty-str as value object
            i2._custom_field_data[cf_label] = ""
            i2.save()

            # Null-value object
            i3._custom_field_data[cf_label] = None
            i3.save()

            # Object with actual value
            i4._custom_field_data[cf_label] = test_data["value"]
            i4.save()

            for lookup_data in test_data["lookups"]:
                test_cases = [(lookup_data["lookup"], test_case) for test_case in lookup_data["test_cases"]]
                if negated_lookup := lookup_data.get("negated_lookup"):
                    test_cases += self.get_negated_test_cases(negated_lookup, lookup_data["test_cases"])

                for lookup, test_case in test_cases:
                    lookup_expr = f"cf_{cf_label}__{lookup}"
                    if lookup == "":
                        lookup_expr = f"cf_{cf_label}"

                    with self.subTest(
                        f'Test filtering {cf_label} by `{lookup}` ({lookup_data["name"]}) = "{test_case["search"]}"'
                    ):
                        # Little hack to mimic actual UI behavior: for exact filtering value is  being passed as "str" not list.
                        # But for `ie` it will be list.
                        # Also for filtering by "exact" with custom field "loose" filtering logic it will use `icontains`.
                        if lookup == "":
                            params = {lookup_expr: test_case["search"]}
                        else:
                            params = {lookup_expr: [test_case["search"]]}
                        fs = self.filterset(params, qs)

                        self.assertTrue(fs.is_valid())
                        filtered = fs.qs
                        assert_in_msg = f'object expected to be found for searching `{lookup}` ({lookup_data["name"]}) = "{test_case["search"]}"'
                        assert_not_in_msg = f'object expected to be filtered out for searching `{lookup}` ({lookup_data["name"]}) = "{test_case["search"]}"'

                        if test_case["expected"]["no_key"]:
                            self.assertIn(i1, filtered, msg=f"No-key {assert_in_msg}")
                        else:
                            self.assertNotIn(i1, filtered, msg=f"No-key {assert_not_in_msg}")

                        if test_case["expected"]["empty"]:
                            self.assertIn(i2, filtered, msg=f"Empty-value {assert_in_msg}")
                        else:
                            self.assertNotIn(i2, filtered, msg=f"Empty-value {assert_not_in_msg}")

                        if test_case["expected"]["null"]:
                            self.assertIn(i3, filtered, msg=f"Null-value {assert_in_msg}")
                        else:
                            self.assertNotIn(i3, filtered, msg=f"Null-value {assert_not_in_msg}")

                        if test_case["expected"]["value"]:
                            self.assertIn(i4, filtered, msg=f"Value-set {assert_in_msg}")
                        else:
                            self.assertNotIn(i4, filtered, msg=f"Value-set {assert_not_in_msg}")
