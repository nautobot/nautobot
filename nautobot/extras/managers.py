from django.db.models import Q
from taggit.managers import TaggableManager as TaggitTaggableManager

from nautobot.extras.models.tags import Tag
from nautobot.utilities.forms.fields import DynamicModelMultipleChoiceField


class TaggableManager(TaggitTaggableManager):
    """
    Helper class for overriding TaggableManager formfield method
    """

    def formfield(self, form_class=DynamicModelMultipleChoiceField, **kwargs):
        queryset = Tag.objects.filter(
            Q(
                content_types__model=self.model._meta.model_name,
                content_types__app_label=self.model._meta.app_label,
            )
            | Q(content_types__isnull=True)
        )
        kwargs.setdefault("queryset", queryset)
        kwargs.setdefault("required", False)
        kwargs.setdefault("query_params", {"content_types": self.model._meta.label_lower})

        return super().formfield(form_class, **kwargs)
