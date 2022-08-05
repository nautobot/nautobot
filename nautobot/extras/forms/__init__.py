# flake8: noqa
from .base import *
from .forms import *
from .mixins import *

# 2.0 TODO: Names for backward compatibility with Nautobot 1.3 and earlier. Remove in 2.0
AddRemoveTagsForm = TagsBulkEditFormMixin
CustomFieldBulkEditForm = CustomFieldModelBulkEditFormMixin
CustomFieldFilterForm = CustomFieldModelFilterFormMixin
CustomFieldModelForm = CustomFieldModelFormMixin
RelationshipModelForm = RelationshipModelFormMixin
StatusBulkEditFormMixin = StatusModelBulkEditFormMixin
StatusFilterFormMixin = StatusModelFilterFormMixin
