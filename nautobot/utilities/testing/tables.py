from django.test import TestCase

import inspect

from nautobot.core.models import BaseModel
from types import ModuleType
from typing import List, Tuple, Type

from nautobot.utilities.tables import BaseTable, ButtonsColumn


class TableTestCase(TestCase):
    @staticmethod
    def get_tables_from_module(
        module: ModuleType,
        parent_class: Type[BaseTable] = BaseTable,
        excluded_classes: List[Type[BaseTable]] = [BaseTable],
    ) -> List[Type[BaseTable]]:
        """
        Gets all `Table` classes defined in `module`

        Optionally can filter to only tables inherited from `parent_class` (defaults to `BaseTable`)
        or can exclude specific classes (i.e. `excluded_classes)

        Args:
            module: Module to search for `Table` class definitions
            parent_class:
                Results are filtered to only classes **inherited** from `parent_class`
                Classes of `parent_class` are **not** included in results
            excluded_classes: Specific classes to exclude from results

        Returns:
            List of `Table` classes defined in module meeting specific parameters
        """
        return [
            c
            for _, c in inspect.getmembers(module)
            if (
                (inspect.isclass(c) and issubclass(c, parent_class))
                and (c not in [parent_class] + excluded_classes)
                # Concatenating `parent_class` to `excluded_classes` is required because `issubclass(BaseTable, BaseTable)` returns `True`
            )
        ]

    def assertModelHasField(
        self,
        field: str,
        model: Type[BaseModel],
        include_parents: bool = True,
        include_hidden: bool = True,
    ):
        """
        Assert that `field` exists on `model`

        Args:
            field: Field to confirm existence of
            model: Model to check for existence of `field`
            include_parents: Include inherited fields on model
            include_hidden: Include hidden fields on model
        """
        model_fields = [
            field.name
            for field in model._meta.get_fields(
                include_parents=include_parents,
                include_hidden=include_hidden,
            )
        ]
        self.assertIn(field, model_fields)

    def assertModelHasProperty(
        self,
        property_name: str,
        model: Type[BaseModel],
    ):
        """
        Assert that `property_name` exists on `model`
        """
        self.assertTrue(
            hasattr(model, property_name) and isinstance(getattr(model, property_name), property),
            f'{model} does not contain expected property "{property_name}"',
        )

    def assertTableFieldsExist(
        self,
        table,
        excluded_fields: List[str] = ["pk", "id"],
        excluded_column_classes: Tuple[type] = (ButtonsColumn),
    ):
        """
        Assert that fields defined in `Table` exist on linked `Model` as a field or property

        Args:
            table: Table class to analyze
            excluded_fields: List of fields to exclude from validation
            allow_hidden_fields: Permit usage of hidden fields from model

        Raises:
            AssertionError: when a field is defined on the `Table` that is not defined on linked `Model`
        """

        self.assertTrue(hasattr(table, "_meta"))
        self.assertTrue(hasattr(table._meta, "model"))
        self.assertTrue(hasattr(table, "base_columns"))

        model = table._meta.model

        fields = list(
            filter(
                lambda f: f[0] not in excluded_fields
                and ((excluded_column_classes is None) or (not isinstance(f[1], excluded_column_classes))),
                table.base_columns.items(),
            )
        )
        for field_name, field_cls in fields:
            if hasattr(field_cls, "order_by") and field_cls.order_by is not None:
                for order_by_field in field_cls.order_by:
                    fields.append((order_by_field, None))
            else:
                try:
                    self.assertModelHasField(field_name, model)
                except AssertionError:
                    try:
                        self.assertModelHasProperty(field_name, model)
                    except AssertionError as e:
                        raise e
