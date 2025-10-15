from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.test import tag

from nautobot.core.testing import views
from nautobot.extras.choices import CustomFieldFilterLogicChoices, CustomFieldTypeChoices, DynamicGroupOperatorChoices
from nautobot.extras.models import CustomField, DynamicGroup, DynamicGroupMembership


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
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": False,
                                    "not_matched_value": False,
                                },
                            },
                            {
                                "search": "Lorem ipsum",
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": True,
                                    "not_matched_value": False,
                                },
                            },
                            {
                                "search": "lorem ipsum",
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": False,
                                    "not_matched_value": False,
                                },
                            },
                            {
                                "search": "null",
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": True,
                                    "value": False,
                                    "not_matched_value": False,
                                },
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
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": False,
                                    "not_matched_value": False,
                                },
                            },
                            {
                                "search": "Lorem",
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": True,
                                    "not_matched_value": False,
                                },
                            },
                            {
                                "search": "lorem",
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": True,
                                    "not_matched_value": False,
                                },
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
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": False,
                                    "not_matched_value": False,
                                },
                            },
                            {
                                "search": "Lorem",
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": True,
                                    "not_matched_value": False,
                                },
                            },
                            {
                                "search": "lorem",
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": True,
                                    "not_matched_value": False,
                                },
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
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": False,
                                    "not_matched_value": False,
                                },
                            },
                            {
                                "search": "ipsum",
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": True,
                                    "not_matched_value": False,
                                },
                            },
                            {
                                "search": "IPSUM",
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": True,
                                    "not_matched_value": False,
                                },
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
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": False,
                                    "not_matched_value": False,
                                },
                            },
                            {
                                "search": "Lorem ipsum",
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": True,
                                    "not_matched_value": False,
                                },
                            },
                            {
                                "search": "lorem ipsum",
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": True,
                                    "not_matched_value": False,
                                },
                            },
                            {
                                "search": "null",
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": True,
                                    "value": False,
                                    "not_matched_value": False,
                                },
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
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": False,
                                    "not_matched_value": False,
                                },
                            },
                            {
                                "search": ".?ipsum",
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": True,
                                    "not_matched_value": False,
                                },
                            },
                            {
                                "search": ".?IPSUM",
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": False,
                                    "not_matched_value": False,
                                },
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
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": False,
                                    "not_matched_value": False,
                                },
                            },
                            {
                                "search": ".?ipsum",
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": True,
                                    "not_matched_value": False,
                                },
                            },
                            {
                                "search": ".?IPSUM",
                                "expected": {
                                    "no_key": False,
                                    "empty": False,
                                    "null": False,
                                    "value": True,
                                    "not_matched_value": False,
                                },
                            },
                            # {"search": "null",
                            #  "expected": {"no_key": True, "empty": False, "null": True, "value": False}}, # TODO: 500 atm
                        ],
                    },
                ],
            }
        }

        def test_generate_query_with_str_field_for_dynamic_groups_usage(self):
            cf_label = "test_dgs_label_str"
            test_data = self.filter_matrix[CustomFieldTypeChoices.TYPE_TEXT]
            self.create_custom_field(self.filterset.Meta.model, cf_label)

            instances = self.queryset.all()[:5]
            self.prepare_custom_fields_values(cf_label, instances, test_data["value"], "not-matched")
            qs = self.queryset.filter(pk__in=[instance.pk for instance in instances])

            for lookup_data in test_data["lookups"]:
                test_cases = [(lookup_data["lookup"], test_case) for test_case in lookup_data["test_cases"]]

                for lookup, test_case in test_cases:
                    assert_in_msg = f'object expected to be found for searching `{lookup}` ({lookup_data["name"]}) = "{test_case["search"]}"'
                    assert_not_in_msg = f'object expected to be filtered out for searching `{lookup}` ({lookup_data["name"]}) = "{test_case["search"]}"'

                    lookup_expr = f"cf_{cf_label}__{lookup}"
                    if lookup == "":
                        lookup_expr = f"cf_{cf_label}"

                    with self.subTest(
                        f'Test filtering {cf_label} by `{lookup}` ({lookup_data["name"]}) = "{test_case["search"]}"'
                    ):
                        params = {lookup_expr: test_case["search"]}
                        fs = self.filterset(params, qs)
                        self.assertTrue(fs.is_valid())

                        filter_field = fs.filters.get(lookup_expr)

                        query = filter_field.generate_query(test_case["search"])
                        filtered = qs.filter(query)

                        self.assertProperInstancesReturned(
                            instances, filtered, test_case["expected"], assert_in_msg, assert_not_in_msg
                        )

                # Dynamic Groups filtering logic do negation at higher level than standard filtersets classes
                # Below I'm generating the "negated" expected test cases, but lookup stays "positional"
                # It will be negated during passing to qs.filter method
                negated_test_cases = self.get_negated_test_cases(lookup_data["lookup"], lookup_data["test_cases"])

                for lookup, test_case in negated_test_cases:
                    assert_in_msg = f'object expected to be found for searching `{lookup}` ({lookup_data["name"]}) = "{test_case["search"]}"'
                    assert_not_in_msg = f'object expected to be filtered out for searching `{lookup}` ({lookup_data["name"]}) = "{test_case["search"]}"'

                    with self.subTest(
                        f'Test negated filtering {cf_label} by `{lookup}` ({lookup_data["name"]}) = "{test_case["search"]}"'
                    ):
                        params = {lookup_expr: test_case["search"]}
                        fs = self.filterset(params, qs)
                        self.assertTrue(fs.is_valid())

                        filter_field = fs.filters.get(lookup_expr)

                        query = filter_field.generate_query(test_case["search"])
                        filtered = qs.filter(~query)

                        self.assertProperInstancesReturned(
                            instances, filtered, test_case["expected"], assert_in_msg, assert_not_in_msg
                        )

        def test_str_custom_field_with_dynamic_groups(self):
            cf_label = "test_dgs_label_str"
            cf_label_ic = "test_dgs_label_str_ic"
            test_data = self.filter_matrix[CustomFieldTypeChoices.TYPE_TEXT]
            model = self.filterset.Meta.model
            self.create_custom_field(model, cf_label)
            self.create_custom_field(model, cf_label_ic, filter_logic=CustomFieldFilterLogicChoices.FILTER_LOOSE)

            instances = self.queryset.all()[:5]
            self.prepare_custom_fields_values(cf_label, instances, test_data["value"], "not-matched")
            self.prepare_custom_fields_values(cf_label_ic, instances, test_data["value"], "not-matched")

            ct = ContentType.objects.get_for_model(model)

            filter_group = DynamicGroup.objects.create(
                name="CustomField DynamicGroup",
                content_type=ct,
                filter={},
            )
            parent_group = DynamicGroup.objects.create(
                name="Parent CustomField DynamicGroup",
                content_type=ct,
                filter={},
            )
            group_membership = DynamicGroupMembership.objects.create(
                parent_group=parent_group,
                group=filter_group,
                operator=DynamicGroupOperatorChoices.OPERATOR_INTERSECTION,
                weight=10,
            )

            # Prepare test cases
            # For dynamic group we're supporting only exact or icontains for now
            # Depending on the custom field filter logic
            for lookup_data in test_data["lookups"]:
                if lookup_data["lookup"] not in ["", "ic"]:
                    continue

                test_cases = [(lookup_data["lookup"], test_case) for test_case in lookup_data["test_cases"]]
                group_membership.operator = DynamicGroupOperatorChoices.OPERATOR_INTERSECTION
                group_membership.save()

                for lookup, test_case in test_cases:
                    assert_in_msg = f'object expected to be found for searching `{lookup}` ({lookup_data["name"]}) = "{test_case["search"]}"'
                    assert_not_in_msg = f'object expected to be filtered out for searching `{lookup}` ({lookup_data["name"]}) = "{test_case["search"]}"'
                    group_filter = {f"cf_{cf_label}": test_case["search"]}
                    if lookup == "ic":
                        group_filter = {f"cf_{cf_label_ic}": test_case["search"]}

                    with self.subTest(f"Test filtering {group_filter}"):
                        filter_group.set_filter(group_filter)
                        filter_group.save()
                        members = parent_group.update_cached_members()
                        self.assertProperInstancesReturned(
                            instances, members, test_case["expected"], assert_in_msg, assert_not_in_msg
                        )

                negated_test_cases = self.get_negated_test_cases(lookup_data["lookup"], lookup_data["test_cases"])
                group_membership.operator = DynamicGroupOperatorChoices.OPERATOR_DIFFERENCE
                group_membership.save()

                for lookup, test_case in negated_test_cases:
                    assert_in_msg = f'object expected to be found for searching `{lookup}` ({lookup_data["name"]}) = "{test_case["search"]}"'
                    assert_not_in_msg = f'object expected to be filtered out for searching `{lookup}` ({lookup_data["name"]}) = "{test_case["search"]}"'
                    group_filter = {f"cf_{cf_label}": test_case["search"]}
                    if lookup == "ic":
                        group_filter = {f"cf_{cf_label_ic}": test_case["search"]}

                    with self.subTest(f"Test negated filtering {group_filter}"):
                        filter_group.set_filter(group_filter)
                        filter_group.save()
                        members = parent_group.update_cached_members()
                        self.assertProperInstancesReturned(
                            instances, members, test_case["expected"], assert_in_msg, assert_not_in_msg
                        )

        def test_str_custom_field_filters(self):
            cf_label = "test_fs_label_str"
            test_data = self.filter_matrix[CustomFieldTypeChoices.TYPE_TEXT]
            self.create_custom_field(self.filterset.Meta.model, cf_label)

            instances = self.queryset.all()[:5]
            self.prepare_custom_fields_values(cf_label, instances, test_data["value"], "not-matched")
            qs = self.queryset.filter(pk__in=[instance.pk for instance in instances])

            for lookup_data in test_data["lookups"]:
                test_cases = [(lookup_data["lookup"], test_case) for test_case in lookup_data["test_cases"]]
                if negated_lookup := lookup_data.get("negated_lookup"):
                    test_cases += self.get_negated_test_cases(negated_lookup, lookup_data["test_cases"])

                for lookup, test_case in test_cases:
                    assert_in_msg = f'object expected to be found for searching `{lookup}` ({lookup_data["name"]}) = "{test_case["search"]}"'
                    assert_not_in_msg = f'object expected to be filtered out for searching `{lookup}` ({lookup_data["name"]}) = "{test_case["search"]}"'

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
                        self.assertProperInstancesReturned(
                            instances, filtered, test_case["expected"], assert_in_msg, assert_not_in_msg
                        )

        @staticmethod
        def create_custom_field(
            model: Model,
            label: str,
            filter_logic: CustomFieldFilterLogicChoices = CustomFieldFilterLogicChoices.FILTER_EXACT,
        ) -> CustomField:
            cf = CustomField.objects.create(
                type=CustomFieldTypeChoices.TYPE_TEXT,
                label=label,
                filter_logic=filter_logic,
            )
            cf.content_types.set([ContentType.objects.get_for_model(model)])
            return cf

        def prepare_custom_fields_values(self, label, instances, match_value, not_match_value):
            i1, i2, i3, i4, i5 = instances

            # No-key object
            self.assertIsNone(i1._custom_field_data.get(label))

            # Empty-str as value object
            i2._custom_field_data[label] = ""
            i2.save()

            # Null-value object
            i3._custom_field_data[label] = None
            i3.save()

            # Object with matcheed value
            i4._custom_field_data[label] = match_value
            i4.save()

            # Object with not-matched value
            i5._custom_field_data[label] = not_match_value
            i5.save()

        @staticmethod
        def get_negated_test_cases(lookup: str, test_cases: list):
            negated_test_cases = []
            for test_case in test_cases:
                expected = {key: not value for key, value in test_case["expected"].items()}
                negated_test_cases.append((lookup, {"search": test_case["search"], "expected": expected}))
            return negated_test_cases

        def assertProperInstancesReturned(self, instances, filtered, expected, assert_in_msg, assert_not_in_msg):
            no_key_object, empty_str_object, null_value_object, matched_value, not_matched_value = instances

            if expected["no_key"]:
                self.assertIn(no_key_object, filtered, msg=f"No-key {assert_in_msg}")
            else:
                self.assertNotIn(no_key_object, filtered, msg=f"No-key {assert_not_in_msg}")

            if expected["empty"]:
                self.assertIn(empty_str_object, filtered, msg=f"Empty-value {assert_in_msg}")
            else:
                self.assertNotIn(empty_str_object, filtered, msg=f"Empty-value {assert_not_in_msg}")

            if expected["null"]:
                self.assertIn(null_value_object, filtered, msg=f"Null-value {assert_in_msg}")
            else:
                self.assertNotIn(null_value_object, filtered, msg=f"Null-value {assert_not_in_msg}")

            if expected["value"]:
                self.assertIn(matched_value, filtered, msg=f"Matched-value {assert_in_msg}")
            else:
                self.assertNotIn(matched_value, filtered, msg=f"Matched-value {assert_not_in_msg}")

            if expected["not_matched_value"]:
                self.assertIn(not_matched_value, filtered, msg=f"Not-matched-value {assert_in_msg}")
            else:
                self.assertNotIn(not_matched_value, filtered, msg=f"Not-matched-valuee {assert_not_in_msg}")
