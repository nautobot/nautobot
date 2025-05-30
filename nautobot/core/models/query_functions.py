from django.db import NotSupportedError
from django.db.models import Aggregate, Func, JSONField, Value
from django.db.models.fields.json import compile_json_path
from django.db.models.functions import Cast


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


class JSONSet(Func):
    """
    Set or create the value of a single key in a JSONField.

    Example:
        model.objects.all().update(_custom_field_data=JSONSet("_custom_field_data", "cf_key", "new_value"))

    Limitations:
        - Postgres and MySQL only.
        - Does *not* support nested lookups (`key1__key2`), only a single top-level key.
        - Unlike the referenced Django PR, supports only a single key/value rather than an arbitrary number of them.

    References:
        - https://code.djangoproject.com/ticket/32519
        - https://github.com/django/django/pull/18489/files
    """

    function = None

    def __init__(self, expression, path, value, output_field=None):
        self.path = path
        self.value = value
        super().__init__(expression, output_field=output_field)

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        """
        Based on https://github.com/django/django/pull/18489/files.

        Transforms and inserts self.path and self.value appropriately into the expression fields.
        """
        c = super().resolve_expression(query, allow_joins, reuse, summarize, for_save)
        # Resolve expressions in the JSON update values.
        c.fields = {
            self.path: (
                self.value.resolve_expression(query, allow_joins, reuse, summarize, for_save)
                if hasattr(self.value, "resolve_expression")
                else self.value
            )
        }
        return c

    def as_sql(self, compiler, connection, function=None, **extra_context):  # pylint:disable=arguments-differ
        """
        MySQL implementation based on https://github.com/django/django/pull/18489/files.

        Creates a copy of this object with the appropriately transformed self.path and self.value for MySQL JSON_SET().
        """
        if connection.vendor != "mysql":
            raise NotSupportedError(f"JSONSet is not implemented for database {connection.vendor}")

        copy = self.copy()
        new_source_expressions = copy.get_source_expressions()

        path = compile_json_path([self.path])
        value = self.value
        if not hasattr(value, "resolve_expression"):
            # Use Value to serialize the value to a string, then Cast to ensure it's treated as JSON.
            value = Cast(Value(value, output_field=self.output_field), output_field=self.output_field)

        new_source_expressions.extend((Value(path), value))
        copy.set_source_expressions(new_source_expressions)
        return super(JSONSet, copy).as_sql(compiler, connection, function="JSON_SET", **extra_context)

    def as_postgresql(self, compiler, connection, function=None, **extra_context):
        """
        PostgreSQL implementation based on https://github.com/django/django/pull/18489/files.

        Creates a copy of this object with appropriately transformed self.path and self.value for Postgres JSONB_SET().
        """
        copy = self.copy()
        new_source_expressions = copy.get_source_expressions()

        path = self.path
        value = self.value
        if not hasattr(value, "resolve_expression"):
            # We don't need Cast() here because Value with a JSONFIeld is correctly handled as JSONB by Postgres
            value = Value(value, output_field=self.output_field)
        else:

            class ToJSONB(Func):
                function = "TO_JSONB"

            value = ToJSONB(value, output_field=self.output_field)

        new_source_expressions.extend((Value(f"{{{path}}}"), value))
        copy.set_source_expressions(new_source_expressions)
        return super(JSONSet, copy).as_sql(compiler, connection, function="JSONB_SET", **extra_context)


class JSONRemove(Func):
    """
    Unset and remove a single key in a JSONField.

    Example:
        model.objects.all().update(_custom_field_data=JSONRemove("_custom_field_data", "cf_key"))

    Limitations:
        - Postgres and MySQL only.
        - Does *not* support nested lookups (`key1__key2`), only a single top-level key.
        - Unlike the referenced Django PR, supports only a single key, not N keys.

    References:
        - https://code.djangoproject.com/ticket/32519
        - https://github.com/django/django/pull/18489/files
    """

    def __init__(self, expression, path):
        self.path = path
        super().__init__(expression)

    def as_sql(self, compiler, connection, function=None, **extra_context):  # pylint:disable=arguments-differ
        """
        MySQL implementation based on https://github.com/django/django/pull/18489/files.

        Creates a copy of this object with appropriately transformed self.path for MySQL JSON_REMOVE().
        """
        if connection.vendor != "mysql":
            raise NotSupportedError(f"JSONSet is not implemented for database {connection.vendor}")

        copy = self.copy()
        new_source_expressions = copy.get_source_expressions()

        new_source_expressions.append(Value(compile_json_path([self.path])))

        copy.set_source_expressions(new_source_expressions)
        return super(JSONRemove, copy).as_sql(compiler, connection, function="JSON_REMOVE", **extra_context)

    def as_postgresql(self, compiler, connection, function=None, **extra_context):
        """
        PostgreSQL implementation based on https://github.com/django/django/pull/18489/files.

        Creates a copy of this object with appropriately transformed self.path for Postgres `#-` operator.
        """
        copy = self.copy()
        new_source_expressions = copy.get_source_expressions()

        new_source_expressions.append(Value(f"{{{self.path}}}"))

        copy.set_source_expressions(new_source_expressions)
        return super(JSONRemove, copy).as_sql(
            compiler, connection, template="%(expressions)s", arg_joiner="#- ", **extra_context
        )


class JSONBAgg(Aggregate):
    """
    Like django.contrib.postgres.aggregates.JSONBAgg, but different.

    1. Supports both Postgres (JSONB_AGG) and MySQL (JSON_ARRAYAGG)
    2. Does not support `ordering` as JSON_ARRAYAGG does not guarantee ordering.
    """

    function = None
    output_field = JSONField()
    # TODO(Glenn): Django's JSONBAgg has `allow_distinct=True`, we might want to think about adding that at some point?

    # Borrowed from `django.contrib.postgres.aggregates.JSONBagg`.
    def convert_value(self, value, expression, connection):  # pylint: disable=arguments-differ
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
    """

    contains_aggregate = False
