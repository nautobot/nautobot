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
    LaxURLField,
    NautobotHyperlinkedRelatedField,
    ObjectTypeField,
    SerializedPKRelatedField,
    TimeZoneSerializerField,
)
from nautobot.core.api.mixins import WritableSerializerMixin
from nautobot.core.api.parsers import NautobotCSVParser
from nautobot.core.api.routers import AuthenticatedAPIRootView as APIRootView, OrderedDefaultRouter
from nautobot.core.api.schema import NautobotAutoSchema
from nautobot.core.api.serializers import (
    OptInFieldsMixin,
    TreeModelSerializerMixin,
)
from nautobot.core.api.utils import (
    dict_to_filter_params,
    dynamic_import,
    get_api_version_serializer,
    get_serializer_for_model,
    get_view_name,
    is_api_request,
    rest_api_server_error,
    versioned_serializer_selector,
)
from nautobot.core.api.views import (
    BulkDestroyModelMixin,
    BulkUpdateModelMixin,
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
    "LaxURLField",
    "ModelViewSet",
    "ModelViewSetMixin",
    "MultipleChoiceJSONField",
    "NautobotAutoSchema",
    "NautobotCSVParser",
    "NautobotHyperlinkedRelatedField",
    "NautobotModelSerializer",
    "NautobotModelViewSet",
    "NotesSerializerMixin",
    "NotesViewSetMixin",
    "ObjectTypeField",
    "OptInFieldsMixin",
    "OrderedDefaultRouter",
    "ReadOnlyModelViewSet",
    "RelationshipModelSerializerMixin",
    "SerializedPKRelatedField",
    "TaggedModelSerializerMixin",
    "TimeZoneSerializerField",
    "TreeModelSerializerMixin",
    "ValidatedModelSerializer",
    "WritableNestedSerializer",
    "WritableSerializerMixin",
    "dict_to_filter_params",
    "dynamic_import",
    "get_api_version_serializer",
    "get_serializer_for_model",
    "get_view_name",
    "is_api_request",
    "rest_api_server_error",
    "versioned_serializer_selector",
)
