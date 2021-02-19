from taggit.managers import TaggableManager

from extras.models.change_logging import ChangeLoggedModel
from extras.models.customfields import CustomFieldModel
from extras.models.relationships import RelationshipModel
from extras.models.tags import TaggedItem
from netbox.models import BaseModel


class OrganizationalModel(
    BaseModel,
    ChangeLoggedModel,
    CustomFieldModel,
    RelationshipModel,
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
    BaseModel,
    ChangeLoggedModel,
    CustomFieldModel,
    RelationshipModel,
):
    """
    Base abstract model for all primary models.

    A primary model is one which is materialistically relevant to the network datamodel.
    Such models form the basis of major elements of the data model, like Device,
    IP Address, Site, VLAN, Virtual Machine, etc. Primary models usually represent
    tangible or logical resources on the network, or within the organization.
    """
    tags = TaggableManager(through=TaggedItem)

    class Meta:
        abstract = True
