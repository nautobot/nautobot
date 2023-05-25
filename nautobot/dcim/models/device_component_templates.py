from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.contrib.contenttypes.models import ContentType

from nautobot.core.models import BaseModel
from nautobot.core.models.fields import ForeignKeyWithAutoRelatedName, NaturalOrderingField
from nautobot.core.models.ordering import naturalize_interface
from nautobot.dcim.choices import (
    SubdeviceRoleChoices,
    ConsolePortTypeChoices,
    PowerPortTypeChoices,
    PowerOutletTypeChoices,
    PowerOutletFeedLegChoices,
    InterfaceTypeChoices,
    PortTypeChoices,
)

from nautobot.dcim.constants import REARPORT_POSITIONS_MAX, REARPORT_POSITIONS_MIN
from nautobot.extras.models import ChangeLoggedModel, CustomField, CustomFieldModel, RelationshipModel, Status
from nautobot.extras.utils import extras_features
from .device_components import (
    ConsolePort,
    ConsoleServerPort,
    DeviceBay,
    FrontPort,
    Interface,
    PowerOutlet,
    PowerPort,
    RearPort,
)

__all__ = (
    "ConsolePortTemplate",
    "ConsoleServerPortTemplate",
    "DeviceBayTemplate",
    "FrontPortTemplate",
    "InterfaceTemplate",
    "PowerOutletTemplate",
    "PowerPortTemplate",
    "RearPortTemplate",
)


class ComponentTemplateModel(BaseModel, ChangeLoggedModel, CustomFieldModel, RelationshipModel):
    device_type = ForeignKeyWithAutoRelatedName(to="dcim.DeviceType", on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    _name = NaturalOrderingField(target_field="name", max_length=100, blank=True)
    label = models.CharField(max_length=64, blank=True, help_text="Physical label")
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        if self.label:
            return f"{self.name} ({self.label})"
        return self.name

    def instantiate(self, device):
        """
        Instantiate a new component on the specified Device.
        """
        raise NotImplementedError()

    def to_objectchange(self, action, **kwargs):
        """
        Return a new ObjectChange with the `related_object` pinned to the `device_type` by default.
        """
        try:
            device_type = self.device_type
        except ObjectDoesNotExist:
            # The parent DeviceType has already been deleted
            device_type = None

        return super().to_objectchange(action, related_object=device_type, **kwargs)

    def get_absolute_url(self, api=False):
        # TODO: in the new UI, this should be able to link directly to the object, instead of the device-type.
        if not api:
            return self.device_type.get_absolute_url(api=api)
        return super().get_absolute_url(api=api)

    def instantiate_model(self, model, device, **kwargs):
        """
        Helper method to self.instantiate().
        """
        custom_field_data = {}
        content_type = ContentType.objects.get_for_model(model)
        fields = CustomField.objects.filter(content_types=content_type)
        for field in fields:
            custom_field_data[field.key] = field.default

        return model(
            device=device,
            name=self.name,
            label=self.label,
            description=self.description,
            _custom_field_data=custom_field_data,
            **kwargs,
        )


@extras_features(
    "custom_validators",
)
class ConsolePortTemplate(ComponentTemplateModel):
    """
    A template for a ConsolePort to be created for a new Device.
    """

    type = models.CharField(max_length=50, choices=ConsolePortTypeChoices, blank=True)

    class Meta:
        ordering = ("device_type", "_name")
        unique_together = ("device_type", "name")

    def instantiate(self, device):
        return self.instantiate_model(model=ConsolePort, device=device, type=self.type)


@extras_features(
    "custom_validators",
)
class ConsoleServerPortTemplate(ComponentTemplateModel):
    """
    A template for a ConsoleServerPort to be created for a new Device.
    """

    type = models.CharField(max_length=50, choices=ConsolePortTypeChoices, blank=True)

    class Meta:
        ordering = ("device_type", "_name")
        unique_together = ("device_type", "name")

    def instantiate(self, device):
        return self.instantiate_model(model=ConsoleServerPort, device=device, type=self.type)


@extras_features(
    "custom_validators",
)
class PowerPortTemplate(ComponentTemplateModel):
    """
    A template for a PowerPort to be created for a new Device.
    """

    type = models.CharField(max_length=50, choices=PowerPortTypeChoices, blank=True)
    maximum_draw = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)],
        help_text="Maximum power draw (watts)",
    )
    allocated_draw = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)],
        help_text="Allocated power draw (watts)",
    )

    class Meta:
        ordering = ("device_type", "_name")
        unique_together = ("device_type", "name")

    def instantiate(self, device):
        return self.instantiate_model(
            model=PowerPort,
            device=device,
            type=self.type,
            maximum_draw=self.maximum_draw,
            allocated_draw=self.allocated_draw,
        )

    def clean(self):
        super().clean()

        if self.maximum_draw is not None and self.allocated_draw is not None:
            if self.allocated_draw > self.maximum_draw:
                raise ValidationError(
                    {"allocated_draw": f"Allocated draw cannot exceed the maximum draw ({self.maximum_draw}W)."}
                )


@extras_features(
    "custom_validators",
)
class PowerOutletTemplate(ComponentTemplateModel):
    """
    A template for a PowerOutlet to be created for a new Device.
    """

    type = models.CharField(max_length=50, choices=PowerOutletTypeChoices, blank=True)
    power_port_template = models.ForeignKey(
        to="dcim.PowerPortTemplate",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="power_outlet_templates",
    )
    feed_leg = models.CharField(
        max_length=50,
        choices=PowerOutletFeedLegChoices,
        blank=True,
        help_text="Phase (for three-phase feeds)",
    )

    class Meta:
        ordering = ("device_type", "_name")
        unique_together = ("device_type", "name")

    def clean(self):
        super().clean()

        # Validate power port assignment
        if self.power_port_template and self.power_port_template.device_type != self.device_type:
            raise ValidationError(f"Parent power port ({self.power_port_template}) must belong to the same device type")

    def instantiate(self, device):
        if self.power_port_template:
            power_port = PowerPort.objects.get(device=device, name=self.power_port_template.name)
        else:
            power_port = None
        return self.instantiate_model(
            model=PowerOutlet,
            device=device,
            type=self.type,
            power_port=power_port,
            feed_leg=self.feed_leg,
        )


@extras_features(
    "custom_validators",
)
class InterfaceTemplate(ComponentTemplateModel):
    """
    A template for a physical data interface on a new Device.
    """

    # Override ComponentTemplateModel._name to specify naturalize_interface function
    _name = NaturalOrderingField(
        target_field="name",
        naturalize_function=naturalize_interface,
        max_length=100,
        blank=True,
    )
    type = models.CharField(max_length=50, choices=InterfaceTypeChoices)
    mgmt_only = models.BooleanField(default=False, verbose_name="Management only")

    class Meta:
        ordering = ("device_type", "_name")
        unique_together = ("device_type", "name")

    def instantiate(self, device):
        try:
            status = Status.objects.get_for_model(Interface).get(name="Active")
        except Status.DoesNotExist:
            status = Status.objects.get_for_model(Interface).first()
        return self.instantiate_model(
            model=Interface,
            device=device,
            type=self.type,
            mgmt_only=self.mgmt_only,
            status=status,
        )


@extras_features(
    "custom_validators",
)
class FrontPortTemplate(ComponentTemplateModel):
    """
    Template for a pass-through port on the front of a new Device.
    """

    type = models.CharField(max_length=50, choices=PortTypeChoices)
    rear_port_template = models.ForeignKey(
        to="dcim.RearPortTemplate",
        on_delete=models.CASCADE,
        related_name="front_port_templates",
    )
    rear_port_position = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(REARPORT_POSITIONS_MIN),
            MaxValueValidator(REARPORT_POSITIONS_MAX),
        ],
    )

    class Meta:
        ordering = ("device_type", "_name")
        unique_together = (
            ("device_type", "name"),
            ("rear_port_template", "rear_port_position"),
        )

    def clean(self):
        super().clean()

        # Validate rear port assignment
        if self.rear_port_template.device_type != self.device_type:
            raise ValidationError(f"Rear port ({self.rear_port_template}) must belong to the same device type")

        # Validate rear port position assignment
        if self.rear_port_position > self.rear_port_template.positions:
            raise ValidationError(
                (
                    f"Invalid rear port position ({self.rear_port_position}); "
                    f"rear port {self.rear_port_template.name} has only {self.rear_port_template.positions} positions"
                )
            )

    def instantiate(self, device):
        if self.rear_port_template:
            rear_port = RearPort.objects.get(device=device, name=self.rear_port_template.name)
        else:
            rear_port = None
        return self.instantiate_model(
            model=FrontPort,
            device=device,
            type=self.type,
            rear_port=rear_port,
            rear_port_position=self.rear_port_position,
        )


@extras_features(
    "custom_validators",
)
class RearPortTemplate(ComponentTemplateModel):
    """
    Template for a pass-through port on the rear of a new Device.
    """

    type = models.CharField(max_length=50, choices=PortTypeChoices)
    positions = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(REARPORT_POSITIONS_MIN),
            MaxValueValidator(REARPORT_POSITIONS_MAX),
        ],
    )

    class Meta:
        ordering = ("device_type", "_name")
        unique_together = ("device_type", "name")

    def instantiate(self, device):
        return self.instantiate_model(
            model=RearPort,
            device=device,
            type=self.type,
            positions=self.positions,
        )


@extras_features(
    "custom_validators",
)
class DeviceBayTemplate(ComponentTemplateModel):
    """
    A template for a DeviceBay to be created for a new parent Device.
    """

    class Meta:
        ordering = ("device_type", "_name")
        unique_together = ("device_type", "name")

    def instantiate(self, device):
        return self.instantiate_model(model=DeviceBay, device=device)

    def clean(self):
        if self.device_type and self.device_type.subdevice_role != SubdeviceRoleChoices.ROLE_PARENT:
            raise ValidationError(
                f'Subdevice role of device type ({self.device_type}) must be set to "parent" to allow device bays.'
            )
