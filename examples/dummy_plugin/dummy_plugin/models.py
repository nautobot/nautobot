from django.db import models

from nautobot.core.models import BaseModel
from nautobot.extras.utils import extras_features


@extras_features("graphql")
class DummyModel(BaseModel):
    name = models.CharField(max_length=20)
    number = models.IntegerField(default=100)

    class Meta:
        ordering = ["name"]


class AnotherDummyModel(BaseModel):
    name = models.CharField(max_length=20)
    number = models.IntegerField(default=100)

    class Meta:
        ordering = ["name"]
