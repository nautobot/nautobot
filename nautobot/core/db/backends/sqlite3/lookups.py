"""JSONField lookups that Django does not implement for SQLite."""

from django.db.models.fields.json import (
    compile_json_path,
    ContainedBy as DjangoContainedBy,
    DataContains as DjangoDataContains,
    JSONField,
    KeyTransform,
)


class _JSONTextLHSMixin:
    """
    Compile the left-hand side of a JSON lookup to JSON text.

    Django compiles a key transform on SQLite to a `JSON_EXTRACT()` expression, which yields the plain SQL value of a
    scalar (a JSON string becomes bare text, `true` becomes 1). The `->` operator yields the JSON text of any value
    instead, which is what the registered `JSON_CONTAINS` function expects.
    """

    def process_json_lhs(self, compiler, connection):
        if isinstance(self.lhs, KeyTransform):
            lhs, params, key_transforms = self.lhs.preprocess_lhs(compiler, connection)
            return f"({lhs} -> %s)", (*params, compile_json_path(key_transforms))
        lhs, params = self.process_lhs(compiler, connection)
        return lhs, tuple(params)


class DataContains(_JSONTextLHSMixin, DjangoDataContains):
    def as_sqlite(self, compiler, connection):
        lhs, lhs_params = self.process_json_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        return f"JSON_CONTAINS({lhs}, {rhs})", (*lhs_params, *rhs_params)


class ContainedBy(_JSONTextLHSMixin, DjangoContainedBy):
    def as_sqlite(self, compiler, connection):
        lhs, lhs_params = self.process_json_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        return f"JSON_CONTAINS({rhs}, {lhs})", (*rhs_params, *lhs_params)


def register_lookups():
    """Replace Django's `contains` and `contained_by` JSONField lookups with SQLite-capable equivalents."""
    JSONField.register_lookup(DataContains)
    JSONField.register_lookup(ContainedBy)
