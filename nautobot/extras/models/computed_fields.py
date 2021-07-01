from collections import OrderedDict

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.urls import reverse
from jinja2 import TemplateError

from nautobot.core.models import BaseModel
from nautobot.extras.models import ChangeLoggedModel
from nautobot.extras.utils import extras_features, FeatureQuery
from nautobot.utilities.querysets import RestrictedQuerySet
from nautobot.utilities.utils import render_jinja2


class ComputedFieldManager(models.Manager.from_queryset(RestrictedQuerySet)):
    use_in_migrations = True

    def get_for_model(self, model):
        """
        Return all ComputedFiedlds assigned to the given model.
        """
        content_type = ContentType.objects.get_for_model(model._meta.concrete_model)
        return self.get_queryset().filter(content_type=content_type)


@extras_features("graphql")
class ComputedField(BaseModel, ChangeLoggedModel):
    """
    Read-only rendered fields driven by a Jinja2 template that are applied to objects within a ContentType.
    """

    content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=FeatureQuery("custom_fields"),
    )
    slug = models.SlugField(max_length=100, unique=True, help_text="Internal field name")
    label = models.CharField(max_length=100, help_text="Name of the field as displayed to users")
    description = models.CharField(max_length=200, blank=True)
    template = models.TextField(max_length=500, help_text="Jinja2 template code for field value")
    fallback_value = models.CharField(
        max_length=500, help_text="Fallback value to be used for the field in the case of a template rendering error."
    )
    weight = models.PositiveSmallIntegerField(default=100)

    objects = ComputedFieldManager()

    class Meta:
        ordering = ["weight", "slug"]
        unique_together = ("content_type", "label")

    def __str__(self):
        return self.slug

    def get_absolute_url(self):
        return reverse("extras:computedfield", kwargs={"pk": self.pk})

    def to_form_field(self):
        return forms.CharField(max_length=255, disabled=True)

    def render(self, context):
        try:
            return render_jinja2(self.template, context)
        except TemplateError:
            return self.fallback_value


class ComputedFieldModelMixin(models.Model):
    """
    Abstract class for any model which may have computed fields associated with it.
    """

    class Meta:
        abstract = True

    def has_computed_fields(self):
        """
        Return a boolean indicating whether or not this content type has computed fields associated with it.
        """
        return bool(ComputedField.objects.get_for_model(self))

    def get_computed_field(self, slug, render=True):
        computed_field = ComputedField.objects.get_for_model(self).get(slug=slug)
        if render:
            return computed_field.render(context={"obj": self})
        return computed_field.template

    def get_computed_fields(self, label_as_key=False):
        computed_fields_dict = {}
        computed_fields = ComputedField.objects.get_for_model(self)
        if not computed_fields:
            return {}
        for cf in computed_fields:
            computed_fields_dict[cf.label if label_as_key else cf.slug] = cf.render(context={"obj": self})
        return computed_fields_dict
