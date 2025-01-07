from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel  # isort: off

from nautobot.extras.utils import extras_features

from .roles import RoleField
from .statuses import StatusField


class ContactTeamSharedBase(PrimaryModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, db_index=True)
    phone = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, db_index=True)
    email = models.EmailField(blank=True, db_index=True, verbose_name="E-mail")
    address = models.TextField(blank=True)

    comments = models.TextField(blank=True)
    is_contact_associable_model = False

    class Meta:
        abstract = True
        ordering = ("name",)
        unique_together = (("name", "phone", "email"),)

    def __str__(self):
        result = self.name
        if self.phone:
            result += f" ({self.phone})"
        if self.email:
            result += f" ({self.email})"
        return result


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class Contact(ContactTeamSharedBase):
    """Contact information for an individual person or other point of contact."""

    class Meta(ContactTeamSharedBase.Meta):
        abstract = False


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class Team(ContactTeamSharedBase):
    """A group of Contacts, usable interchangeably with a single Contact in most cases."""

    contacts = models.ManyToManyField(to=Contact, related_name="teams", blank=True)

    class Meta(ContactTeamSharedBase.Meta):
        abstract = False


@extras_features(
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "statuses",
    "webhooks",
)
class ContactAssociation(OrganizationalModel):
    """Intermediary model for associating a Contact or Team to any other object."""

    contact = models.ForeignKey(
        to=Contact, blank=True, null=True, on_delete=models.CASCADE, related_name="contact_associations"
    )
    team = models.ForeignKey(
        to=Team, blank=True, null=True, on_delete=models.CASCADE, related_name="contact_associations"
    )
    associated_object_type = models.ForeignKey(to=ContentType, on_delete=models.SET_NULL, null=True, related_name="+")
    associated_object_id = models.UUIDField(db_index=True)
    associated_object = GenericForeignKey(ct_field="associated_object_type", fk_field="associated_object_id")

    role = RoleField(blank=False, null=False)
    status = StatusField(blank=False, null=False)

    is_contact_associable_model = False
    is_dynamic_group_associable_model = False
    is_saved_view_model = False

    class Meta:
        unique_together = (
            ("contact", "associated_object_type", "associated_object_id", "role"),
            ("team", "associated_object_type", "associated_object_id", "role"),
        )

    def __str__(self):
        if self.contact is not None:
            return f"Contact {self.contact} for {self.associated_object}"
        else:
            return f"Team contact {self.team} for {self.associated_object}"

    def clean(self):
        if self.contact is None and self.team is None:
            raise ValidationError("Either a contact or a team must be specified")
        if self.contact is not None and self.team is not None:
            raise ValidationError("A contact and a team cannot be both specified at once")
        if self.associated_object is None:
            raise ValidationError("The associated object must be valid")

    @property
    def contact_or_team(self):
        if self.contact is not None:
            return self.contact
        else:
            return self.team
