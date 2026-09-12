"""Validate filter patterns with the database regex engine."""

from contextlib import nullcontext

from django.core.exceptions import ValidationError
from django.db import connections, DatabaseError, models, transaction
from django.db.models.sql.query import Query

# MySQL ICU pattern errors. Generic errors, internal failures, stack overflow, and timeouts must propagate.
MYSQL_REGEX_PATTERN_ERRORS = {
    3685,  # ER_REGEXP_ILLEGAL_ARGUMENT (includes invalid Unicode properties)
    3688,  # ER_REGEXP_RULE_SYNTAX
    3689,  # ER_REGEXP_BAD_ESCAPE_SEQUENCE
    3690,  # ER_REGEXP_UNIMPLEMENTED
    3691,  # ER_REGEXP_MISMATCHED_PAREN
    3692,  # ER_REGEXP_BAD_INTERVAL
    3693,  # ER_REGEXP_MAX_LT_MIN
    3694,  # ER_REGEXP_INVALID_BACK_REF
    3695,  # ER_REGEXP_LOOK_BEHIND_LIMIT
    3696,  # ER_REGEXP_MISSING_CLOSE_BRACKET
    3697,  # ER_REGEXP_INVALID_RANGE
    3700,  # ER_REGEXP_PATTERN_TOO_BIG
    3887,  # ER_REGEXP_INVALID_CAPTURE_GROUP_NAME
    3900,  # ER_REGEXP_INVALID_FLAG
    4007,  # ER_REGEX_NUMBER_TOO_BIG
}


def validate_regex(values, *, using, lookup_expr):
    """Compile supplied patterns on the query's database without reading model rows.

    Python regex syntax differs from PostgreSQL and MySQL syntax. Use Django's
    backend-specific lookup SQL, with parameterized patterns and an empty subject.
    One SELECT validates all values in a field. Protect an existing transaction
    with a savepoint so a rejected pattern does not prevent error reporting.
    """
    if isinstance(values, str):
        values = [values]
    if not values:
        return

    connection = connections[using]
    compiler = Query(None).get_compiler(connection=connection)
    lookup = models.CharField().get_lookup(lookup_expr)
    expressions = []
    params = []
    for value in dict.fromkeys(values):
        if "\x00" in value:
            raise ValidationError("Null characters are not allowed.", code="null_characters_not_allowed")
        sql, sql_params = compiler.compile(lookup(models.Value(""), models.Value(value)))
        expressions.append(sql)
        params.extend(sql_params)

    try:
        with transaction.atomic(using=using) if not connection.get_autocommit() else nullcontext():
            with connection.cursor() as cursor:
                cursor.execute("SELECT " + ", ".join(expressions), params)
    except DatabaseError as error:
        cause = error.__cause__
        sqlstate = getattr(cause, "sqlstate", None) or getattr(cause, "pgcode", None)
        if (connection.vendor == "postgresql" and sqlstate == "2201B") or (
            connection.vendor == "mysql" and error.args and error.args[0] in MYSQL_REGEX_PATTERN_ERRORS
        ):
            raise ValidationError("Enter a valid regular expression for this database.", code="invalid") from error
        raise
