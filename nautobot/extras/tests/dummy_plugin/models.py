from django.db import models
from nautobot.extras.utils import extras_features


@extras_features("graphql")
class DummyModel(models.Model):
    name = models.CharField(max_length=20)
    number = models.IntegerField(default=100)

    class Meta:
        ordering = ["name"]


class AnotherDummyModel(models.Model):
    name = models.CharField(max_length=20)
    number = models.IntegerField(default=100)

    class Meta:
        ordering = ["name"]
