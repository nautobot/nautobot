from django.db import models  # noqa: I001
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError
from jsonschema.validators import Draft7Validator

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseManager, BaseModel, ContentTypeRelatedQuerySet
from nautobot.core.models.fields import ForeignKeyLimitedByContentTypes
from nautobot.core.models.generics import PrimaryModel
from nautobot.extras.utils import FeatureQuery, extras_features


class AccessPointGroup(PrimaryModel):
    """
    An AccessPointGroup is a collection of AccessPoints. It is used to apply common configuration to multiple
    AccessPoints at once.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=200, blank=True)
    controller = models.ForeignKey(
        to="dcim.Controller",
        on_delete=models.PROTECT,
        related_name="access_point_groups",
        blank=True,
        null=True,
    )
    access_points = models.ManyToManyField(
        to="dcim.Device",
        related_name="access_point_groups",
        blank=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
    

class RadioProfile(PrimaryModel):
    """
    A RadioProfile is a collection of settings that can be applied to a Radio.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=200, blank=True)
    access_point_groups = models.ManyToManyField(
        to="wireless.AccessPointGroup",
        related_name="radio_profiles",
        blank=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
    

class WirelessNetwork(PrimaryModel):
    """
    A WirelessNetwork represents a wireless network that can be broadcast by an AccessPoint.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=200, blank=True)
    ssid = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    access_point_groups = models.ManyToManyField(
        to="wireless.AccessPointGroup",
        related_name="wireless_networks",
        blank=True,
    )


    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name