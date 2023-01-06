from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from nautobot.core.api import BaseModelSerializer


class TreeModelSerializerMixin(BaseModelSerializer):
    """Add a `tree_depth` field to model serializers based on django-tree-queries."""

    tree_depth = serializers.SerializerMethodField(read_only=True)

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_tree_depth(self, obj):
        """The `tree_depth` is not a database field, but an annotation automatically added by django-tree-queries."""
        return getattr(obj, "tree_depth", None)
