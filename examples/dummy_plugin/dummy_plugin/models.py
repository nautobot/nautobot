from django.db import models
from django.urls import reverse

from nautobot.core.fields import AutoSlugField
from nautobot.core.models import BaseModel
from nautobot.extras.utils import extras_features
from nautobot.extras.models import ObjectChange
from nautobot.utilities.utils import serialize_object


@extras_features("custom_links", "graphql")
class DummyModel(BaseModel):
    name = models.CharField(max_length=20, help_text="The name of this Dummy.")
    number = models.IntegerField(default=100, help_text="The number of this Dummy.")

    csv_headers = ["name", "number"]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - {self.number}"

    def get_absolute_url(self):
        return reverse("plugins:dummy_plugin:dummymodel", kwargs={"pk": self.pk})

    def to_objectchange(self, action):
        return ObjectChange(
            changed_object=self,
            object_repr=str(self),
            action=action,
            # related_object=self.virtual_machine,
            object_data=serialize_object(self),
        )

    def to_csv(self):
        return (
            self.name,
            self.number,
        )


class AnotherDummyModel(BaseModel):
    name = models.CharField(max_length=20)
    number = models.IntegerField(default=100)

    class Meta:
        ordering = ["name"]


class AutoSlugModel(models.Model):
    title = models.CharField(max_length=20)
    slug = AutoSlugField(populate_from="title", max_length=10)


class UniqueAutoSlugModel(models.Model):
    title = models.CharField(max_length=255)
    slug = AutoSlugField(populate_from="title", unique=True)


class UniqueForAutoSlugModel(models.Model):
    title = models.CharField(max_length=255)
    slug = AutoSlugField(
        populate_from="title",
        unique_for_date="unique_date",
        unique_for_month="unique_month",
        unique_for_year="unique_year",
    )
    unique_date = models.DateField()
    unique_month = models.DateField()
    unique_year = models.DateField()


class UniqueForDateTimeAutoSlugModel(models.Model):
    title = models.CharField(max_length=255)
    slug = AutoSlugField(populate_from="title", unique_for_date="pub_datetime")
    pub_datetime = models.DateTimeField()


class UniqueTogetherAutoSlugModel(models.Model):
    title = models.CharField(max_length=255)
    slug = AutoSlugField(populate_from="title")
    field_1 = models.CharField(max_length=10)
    field_2 = models.CharField(max_length=10)
    field_3 = models.CharField(max_length=10)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            ("created", "field_1"),
            (
                "slug",
                "field_1",
            ),
            ("slug", "field_2", "field_3"),
        )


class ChildUniqueTogetherAutoSlugModel(UniqueTogetherAutoSlugModel):
    pass


class MixedUniqueAutoSlugModel(models.Model):
    title = models.CharField(max_length=255)
    slug = AutoSlugField(populate_from="title", unique_for_date="unique_date")
    unique_date = models.DateField()
    field_1 = models.CharField(max_length=10)

    class Meta:
        unique_together = ("slug", "field_1")


def custom_slugify(value):
    return "custom-%s" % value


class CustomAutoSlugModel(models.Model):
    title = models.CharField(max_length=255)
    slug = AutoSlugField(populate_from="title", slugify=custom_slugify)


class Child1Model(UniqueAutoSlugModel):
    pass


class Child2Model(UniqueAutoSlugModel):
    pass
