"""Helpers for an app to implement a REST API."""

from nautobot.core.api import (
    BaseModelSerializer,
    CustomFieldModelSerializerMixin,
    NautobotModelSerializer,
    NotesSerializerMixin,
    RelationshipModelSerializerMixin,
    ValidatedModelSerializer,
    WritableNestedSerializer,
)
from nautobot.core.api.fields import (
    ChoiceField,
    ContentTypeField,
    NautobotHyperlinkedRelatedField,
    ObjectTypeField,
    SerializedPKRelatedField,
    TimeZoneSerializerField,
)
from nautobot.core.api.mixins import WritableSerializerMixin
from nautobot.core.api.pagination import OptionalLimitOffsetPagination
from nautobot.core.api.parsers import NautobotCSVParser
from nautobot.core.api.renderers import FormlessBrowsableAPIRenderer, NautobotCSVRenderer, NautobotJSONRenderer
from nautobot.core.api.routers import OrderedDefaultRouter
from nautobot.core.api.schema import NautobotAutoSchema
from nautobot.core.api.serializers import (
    OptInFieldsMixin,
    TreeModelSerializerMixin,
)
from nautobot.core.api.utils import (
    dict_to_filter_params,
    dynamic_import,
    get_api_version_serializer,
    get_nested_serializer_depth,
    get_relation_info_for_nested_serializers,
    get_serializer_for_model,
    get_view_name,
    is_api_request,
    nested_serializer_factory,
    nested_serializers_for_models,
    rest_api_server_error,
    return_nested_serializer_data_based_on_depth,
    versioned_serializer_selector,
)
from nautobot.core.api.views import (
    APIRootView,
    BulkDestroyModelMixin,
    BulkUpdateModelMixin,
    GetObjectCountsView,
    ModelViewSet,
    ModelViewSetMixin,
    ReadOnlyModelViewSet,
)
from nautobot.extras.api.fields import MultipleChoiceJSONField
from nautobot.extras.api.mixins import TaggedModelSerializerMixin
from nautobot.extras.api.views import CustomFieldModelViewSet, NautobotModelViewSet, NotesViewSetMixin


__all__ = (
    "APIRootView",
    "BaseModelSerializer",
    "BulkDestroyModelMixin",
    "BulkUpdateModelMixin",
    "ChoiceField",
    "ContentTypeField",
    "CustomFieldModelSerializerMixin",
    "CustomFieldModelViewSet",
    "dict_to_filter_params",
    "dynamic_import",
    "FormlessBrowsableAPIRenderer",
    "get_api_version_serializer",
    "get_nested_serializer_depth",
    "get_relation_info_for_nested_serializers",
    "get_serializer_for_model",
    "get_view_name",
    "GetObjectCountsView",
    "is_api_request",
    "ModelViewSet",
    "ModelViewSetMixin",
    "MultipleChoiceJSONField",
    "NautobotAutoSchema",
    "NautobotCSVParser",
    "NautobotCSVRenderer",
    "NautobotHyperlinkedRelatedField",
    "NautobotJSONRenderer",
    "NautobotModelSerializer",
    "NautobotModelViewSet",
    "nested_serializer_factory",
    "nested_serializers_for_models",
    "NotesSerializerMixin",
    "NotesViewSetMixin",
    "ObjectTypeField",
    "OptInFieldsMixin",
    "OptionalLimitOffsetPagination",
    "OrderedDefaultRouter",
    "ReadOnlyModelViewSet",
    "RelationshipModelSerializerMixin",
    "rest_api_server_error",
    "return_nested_serializer_data_based_on_depth",
    "SerializedPKRelatedField",
    "TaggedModelSerializerMixin",
    "TimeZoneSerializerField",
    "TreeModelSerializerMixin",
    "ValidatedModelSerializer",
    "versioned_serializer_selector",
    "WritableNestedSerializer",
    "WritableSerializerMixin",
)
