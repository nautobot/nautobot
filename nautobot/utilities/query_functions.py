from django.db.models import Aggregate, JSONField, Value

from django.contrib.postgres.aggregates.mixins import OrderableAggMixin
from django.db import NotSupportedError
from django.db.models import Func


class CollateAsChar(Func):
    """
    Disregard localization by collating a field as a plain character string. Helpful for ensuring predictable ordering.
    """

    function = None
    template = "(%(expressions)s) COLLATE %(function)s"

    def as_sql(self, compiler, connection, function=None, template=None, arg_joiner=None, **extra_context):
        vendor = connection.vendor
        # Mapping of vendor => function
        func_map = {
            "postgresql": '"C"',
            "mysql": "utf8mb4_bin",
        }

        if vendor not in func_map:
            raise NotSupportedError(f"CollateAsChar is not supported for database {vendor}")

        function = func_map[connection.vendor]

        return super().as_sql(compiler, connection, function, template, arg_joiner, **extra_context)


class JSONBAgg(Aggregate):
    function = None
    output_field = JSONField()

    # Borrowed from `django.contrib.postrgres.aggregates.JSONBagg`.
    def convert_value(self, value, expression, connection):
        if not value:
            return "[]"
        return value

    def as_sql(self, compiler, connection, **extra_context):
        vendor = connection.vendor
        # Mapping of vendor => func
        func_map = {
            "postgresql": "JSONB_AGG",
            "mysql": "JSON_ARRAYAGG",
        }

        if JSONBAgg.function is None and vendor not in func_map:
            raise ConnectionError(f"JSON aggregation is not supported for database {vendor}")

        JSONBAgg.function = func_map[vendor]

        return super().as_sql(compiler, connection, **extra_context)


class EmptyGroupByJSONBAgg(JSONBAgg):
    """
    JSONBAgg is a builtin aggregation function which means it includes the use of a GROUP BY clause.
    When used as an annotation for collecting config context data objects, the GROUP BY is
    incorrect. This subclass overrides the Django ORM aggregation control to remove the GROUP BY.

    TODO in Django 3.2 ordering is supported natively on JSONBAgg so we only need to inherit from JSONBAgg.
    """

    contains_aggregate = False


class OrderableJSONBAgg(OrderableAggMixin, JSONBAgg):
    """
    TODO in Django 3.2 ordering is supported natively on JSONBAgg so this is no longer needed.
    """

    template = "%(function)s(%(distinct)s%(expressions)s %(ordering)s)"
