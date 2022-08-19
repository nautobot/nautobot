import logging
import sys

from taggit.managers import TaggableManager, _TaggableManager

from nautobot.extras.models.change_logging import ChangeLoggedModel
from nautobot.extras.models.customfields import CustomFieldModel
from nautobot.extras.models.mixins import DynamicGroupMixin, NotesMixin
from nautobot.extras.models.relationships import RelationshipModel
from nautobot.extras.models.tags import TaggedItem
from nautobot.core.models import BaseModel


logger = logging.getLogger(__name__)


class OrganizationalModel(
    BaseModel, ChangeLoggedModel, CustomFieldModel, RelationshipModel, DynamicGroupMixin, NotesMixin
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


class _NautobotTaggableManager(_TaggableManager):
    def set(self, *tags, through_defaults=None, **kwargs):
        """
        Patch model.tags.set() to be backwards-compatible with django-taggit 1.x and forward-compatible with later.

        Both of these approaches are supported:

        - tags.set("tag 1", "tag 2")  # django-taggit 1.x
        - tags.set(["tag 1", "tag 2"])  # django-taggit 2.x and later
        """
        if len(tags) == 1 and not isinstance(tags[0], (self.through.tag_model(), str)):
            # taggit 2.x+ style, i.e. `set([tag, tag, tag])`
            tags = tags[0]
        else:
            # taggit 1.x style, i.e. `set(tag, tag, tag)`
            # Note: logger.warning() only supports a `stacklevel` parameter in Python 3.8 and later
            tags_unpacked = ", ".join([repr(tag) for tag in tags])
            tags_list = list(tags)
            message = "Deprecated `tags.set(%s)` was called, please change to `tags.set(%s)` instead"
            if sys.version_info >= (3, 8):
                logger.warning(message, tags_unpacked, tags_list, stacklevel=2)
            else:  # Python 3.7
                logger.warning(message, tags_unpacked, tags_list)
        return super().set(tags, through_defaults=through_defaults, **kwargs)


class PrimaryModel(BaseModel, ChangeLoggedModel, CustomFieldModel, RelationshipModel, DynamicGroupMixin, NotesMixin):
    """
    Base abstract model for all primary models.

    A primary model is one which is materialistically relevant to the network datamodel.
    Such models form the basis of major elements of the data model, like Device,
    IP Address, Site, VLAN, Virtual Machine, etc. Primary models usually represent
    tangible or logical resources on the network, or within the organization.
    """

    tags = TaggableManager(through=TaggedItem, manager=_NautobotTaggableManager, ordering=["name"])

    class Meta:
        abstract = True
