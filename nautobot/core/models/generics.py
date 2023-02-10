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


# 2.0 TODO: remove this, force migration to the newer django-taggit API.
class _NautobotTaggableManager(_TaggableManager):
    """Extend _TaggableManager to work around a breaking API change between django-taggit 1.x and 2.x.

    This is a bit confusing, as there's also a related `TaggableManager` class as well.
    `TaggableManager` is the *model field* (subclass of `models.fields.related.RelatedField`),
    while `_TaggableManager` is the *associated manager* (subclass of `models.Manager`).

    For `TaggableManager`, we chose to monkey-patch rather than subclass to override its `formfield` method;
    replacing it with a subclass would create database migrations for every PrimaryModel with a `tags` field.
    In 2.0 we'll want to bite the bullet and make the cutover (#1633).

    For `_TaggableManager`, we can subclass rather than monkey-patching because replacing it *doesn't* require
    a database migration, and this is cleaner than a monkey-patch.
    """

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
