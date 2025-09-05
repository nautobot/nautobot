import logging

from nautobot.core.models import BaseModel
from nautobot.core.models.fields import TagsField
from nautobot.extras.models.change_logging import ChangeLoggedModel
from nautobot.extras.models.customfields import CustomFieldModel
from nautobot.extras.models.mixins import ContactMixin, DynamicGroupsModelMixin, NotesMixin, SavedViewMixin
from nautobot.extras.models.relationships import RelationshipModel

logger = logging.getLogger(__name__)


class OrganizationalModel(
    ChangeLoggedModel,
    ContactMixin,
    CustomFieldModel,
    DynamicGroupsModelMixin,
    NotesMixin,
    RelationshipModel,
    SavedViewMixin,
    BaseModel,
):
    """
    Base abstract model for all organizational models.

    Organizational models aid the primary models by building structured relationships
    and logical groups, or categorizations. Organizational models do not typically
    represent concrete networking resources or assets, but rather they enable user
    specific use cases and metadata about network resources. Examples include
    Device Role, Rack Group, Status, Manufacturer, and Platform.
    """

    class Meta:
        abstract = True


class PrimaryModel(
    ChangeLoggedModel,
    ContactMixin,
    CustomFieldModel,
    DynamicGroupsModelMixin,
    NotesMixin,
    RelationshipModel,
    SavedViewMixin,
    BaseModel,
):
    """
    Base abstract model for all primary models.

    A primary model is one which is materialistically relevant to the network datamodel.
    Such models form the basis of major elements of the data model, like Device,
    IP Address, Location, VLAN, Virtual Machine, etc. Primary models usually represent
    tangible or logical resources on the network, or within the organization.
    """

    tags = TagsField()

    class Meta:
        abstract = True
