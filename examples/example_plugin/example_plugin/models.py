from django.db import models
from django.urls import reverse

from nautobot.core.models import BaseModel
from nautobot.extras.utils import extras_features
from nautobot.extras.models import CustomFieldModel, ObjectChange
from nautobot.utilities.utils import serialize_object


@extras_features(
    "custom_links",
    "graphql",
    "webhooks",
)
class ExampleModel(BaseModel):
    name = models.CharField(max_length=20, help_text="The name of this Example.")
    number = models.IntegerField(default=100, help_text="The number of this Example.")

    csv_headers = ["name", "number"]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - {self.number}"

    def get_absolute_url(self):
        return reverse("plugins:example_plugin:examplemodel", kwargs={"pk": self.pk})

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


@extras_features(
    "custom_fields",
)
class AnotherExampleModel(BaseModel, CustomFieldModel):
    name = models.CharField(max_length=20)
    number = models.IntegerField(default=100)

    class Meta:
        ordering = ["name"]
