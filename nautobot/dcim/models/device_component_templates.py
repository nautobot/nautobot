from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseModel
from nautobot.core.models.fields import ForeignKeyWithAutoRelatedName, NaturalOrderingField
from nautobot.core.models.ordering import naturalize_interface
from nautobot.dcim.choices import (
    ConsolePortTypeChoices,
    InterfaceTypeChoices,
    PortTypeChoices,
    PowerOutletFeedLegChoices,
    PowerOutletTypeChoices,
    PowerPortTypeChoices,
    SubdeviceRoleChoices,
)
from nautobot.dcim.constants import REARPORT_POSITIONS_MAX, REARPORT_POSITIONS_MIN
from nautobot.extras.models import (
    ChangeLoggedModel,
    ContactMixin,
    CustomField,
    CustomFieldModel,
    DynamicGroupsModelMixin,
    RelationshipModel,
    Status,
)
from nautobot.extras.utils import extras_features

from .device_components import (
    ConsolePort,
    ConsoleServerPort,
    DeviceBay,
    FrontPort,
    Interface,
    ModuleBay,
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
    "ModuleBayTemplate",
    "PowerOutletTemplate",
    "PowerPortTemplate",
    "RearPortTemplate",
)


# TODO: Changing ComponentTemplateModel to an OrganizationalModel would just involve adding Notes support...
class ComponentTemplateModel(
    ContactMixin,
    DynamicGroupsModelMixin,
    ChangeLoggedModel,
    CustomFieldModel,
    RelationshipModel,
    BaseModel,
):
    device_type = ForeignKeyWithAutoRelatedName(to="dcim.DeviceType", on_delete=models.CASCADE)
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    _name = NaturalOrderingField(target_field="name", max_length=CHARFIELD_MAX_LENGTH, blank=True)
    label = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Physical label")
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)

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

    instantiate.alters_data = True

    def to_objectchange(self, action, **kwargs):
        """
        Return a new ObjectChange with the `related_object` pinned to the `device_type` by default.
        """
        if "related_object" in kwargs:
            return super().to_objectchange(action, **kwargs)

        try:
            device_type = self.device_type
        except ObjectDoesNotExist:
            # The parent DeviceType has already been deleted
            device_type = None

        return super().to_objectchange(action, related_object=device_type, **kwargs)

    def get_absolute_url(self, api=False):
        # TODO: in the new UI, this should be able to link directly to the object, instead of the device-type.
        if not api:
            return self.device_type.get_absolute_url(api=api)  # pylint: disable=no-member
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

    instantiate_model.alters_data = True


class ModularComponentTemplateModel(ComponentTemplateModel):
    """Component Template that supports assignment to a DeviceType or a ModuleType."""

    device_type = ForeignKeyWithAutoRelatedName(
        to="dcim.DeviceType",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    module_type = ForeignKeyWithAutoRelatedName(
        to="dcim.ModuleType",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    natural_key_field_names = ["device_type", "module_type", "name"]

    class Meta:
        abstract = True
        ordering = ("device_type", "module_type", "_name")
        constraints = [
            models.UniqueConstraint(
                fields=("device_type", "name"),
                name="%(app_label)s_%(class)s_device_type_name_unique",
            ),
            models.UniqueConstraint(
                fields=("module_type", "name"),
                name="%(app_label)s_%(class)s_module_type_name_unique",
            ),
        ]

    @property
    def parent(self):
        return self.device_type if self.device_type else self.module_type

    def to_objectchange(self, action, **kwargs):
        """
        Return a new ObjectChange with the `related_object` pinned to the `device_type` or `module_type`.
        """
        if "related_object" in kwargs:
            return super().to_objectchange(action, **kwargs)

        try:
            parent = self.parent
        except ObjectDoesNotExist:
            # The parent may have already been deleted
            parent = None

        return super().to_objectchange(action, related_object=parent, **kwargs)

    def get_absolute_url(self, api=False):
        if not api:
            return self.parent.get_absolute_url(api=api)
        return super().get_absolute_url(api=api)

    def instantiate_model(self, model, device, module=None, **kwargs):
        """
        Helper method to self.instantiate().
        """
        return super().instantiate_model(model, device, module=module, **kwargs)

    def clean(self):
        super().clean()

        # Validate that a DeviceType or ModuleType is set, but not both
        if self.device_type and self.module_type:
            raise ValidationError("Only one of device_type or module_type must be set")

        if not (self.device_type or self.module_type):
            raise ValidationError("Either device_type or module_type must be set")


@extras_features(
    "custom_validators",
)
class ConsolePortTemplate(ModularComponentTemplateModel):
    """
    A template for a ConsolePort to be created for a new Device.
    """

    type = models.CharField(max_length=50, choices=ConsolePortTypeChoices, blank=True)

    def instantiate(self, device, module=None):
        return self.instantiate_model(model=ConsolePort, device=device, module=module, type=self.type)


@extras_features(
    "custom_validators",
)
class ConsoleServerPortTemplate(ModularComponentTemplateModel):
    """
    A template for a ConsoleServerPort to be created for a new Device.
    """

    type = models.CharField(max_length=50, choices=ConsolePortTypeChoices, blank=True)

    def instantiate(self, device, module=None):
        return self.instantiate_model(model=ConsoleServerPort, device=device, module=module, type=self.type)


@extras_features(
    "custom_validators",
)
class PowerPortTemplate(ModularComponentTemplateModel):
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
    power_factor = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.95"),
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(Decimal("1.00"))],
        help_text="Power factor (0.01-1.00) for converting between watts (W) and volt-amps (VA). Defaults to 0.95.",
    )

    def instantiate(self, device, module=None):
        return self.instantiate_model(
            model=PowerPort,
            device=device,
            module=module,
            type=self.type,
            maximum_draw=self.maximum_draw,
            allocated_draw=self.allocated_draw,
            power_factor=self.power_factor,
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
class PowerOutletTemplate(ModularComponentTemplateModel):
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

    def clean(self):
        super().clean()

        # Validate power port assignment
        if self.power_port_template:
            if self.device_type and self.power_port_template.device_type != self.device_type:
                raise ValidationError(
                    f"Parent power port ({self.power_port_template}) must belong to the same device type"
                )
            if self.module_type and self.power_port_template.module_type != self.module_type:
                raise ValidationError(
                    f"Parent power port ({self.power_port_template}) must belong to the same module type"
                )

    def instantiate(self, device, module=None):
        if self.power_port_template:
            power_port = PowerPort.objects.get(device=device, module=module, name=self.power_port_template.name)
        else:
            power_port = None
        return self.instantiate_model(
            model=PowerOutlet,
            device=device,
            module=module,
            type=self.type,
            power_port=power_port,
            feed_leg=self.feed_leg,
        )


@extras_features(
    "custom_validators",
)
class InterfaceTemplate(ModularComponentTemplateModel):
    """
    A template for a physical data interface on a new Device.
    """

    # Override ComponentTemplateModel._name to specify naturalize_interface function
    _name = NaturalOrderingField(
        target_field="name",
        naturalize_function=naturalize_interface,
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
    )
    type = models.CharField(max_length=50, choices=InterfaceTypeChoices)
    mgmt_only = models.BooleanField(default=False, verbose_name="Management only")

    def instantiate(self, device, module=None):
        try:
            status = Status.objects.get_for_model(Interface).get(name="Active")
        except Status.DoesNotExist:
            status = Status.objects.get_for_model(Interface).first()
        return self.instantiate_model(
            model=Interface,
            device=device,
            module=module,
            type=self.type,
            mgmt_only=self.mgmt_only,
            status=status,
        )


@extras_features(
    "custom_validators",
)
class FrontPortTemplate(ModularComponentTemplateModel):
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

    natural_key_field_names = ["device_type", "module_type", "name", "rear_port_template", "rear_port_position"]

    class Meta(ModularComponentTemplateModel.Meta):
        constraints = [
            *ModularComponentTemplateModel.Meta.constraints,
            models.UniqueConstraint(
                fields=("rear_port_template", "rear_port_position"),
                name="dcim_frontporttemplate_rear_port_template_position_unique",
            ),
        ]

    def clean(self):
        super().clean()

        # Validate rear port assignment
        if self.device_type and self.rear_port_template.device_type != self.device_type:
            raise ValidationError(f"Rear port ({self.rear_port_template}) must belong to the same device type")
        if self.module_type and self.rear_port_template.module_type != self.module_type:
            raise ValidationError(f"Rear port ({self.rear_port_template}) must belong to the same module type")

        # Validate rear port position assignment
        if self.rear_port_position > self.rear_port_template.positions:
            raise ValidationError(
                (
                    f"Invalid rear port position ({self.rear_port_position}); "
                    f"rear port {self.rear_port_template.name} has only {self.rear_port_template.positions} positions"
                )
            )

    def instantiate(self, device, module=None):
        if self.rear_port_template:
            rear_port = RearPort.objects.get(device=device, module=module, name=self.rear_port_template.name)
        else:
            rear_port = None
        return self.instantiate_model(
            model=FrontPort,
            device=device,
            module=module,
            type=self.type,
            rear_port=rear_port,
            rear_port_position=self.rear_port_position,
        )


@extras_features(
    "custom_validators",
)
class RearPortTemplate(ModularComponentTemplateModel):
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

    def instantiate(self, device, module=None):
        return self.instantiate_model(
            model=RearPort,
            device=device,
            module=module,
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
        if self.device_type and self.device_type.subdevice_role != SubdeviceRoleChoices.ROLE_PARENT:  # pylint: disable=no-member
            raise ValidationError(
                f'Subdevice role of device type ({self.device_type}) must be set to "parent" to allow device bays.'
            )


@extras_features("custom_validators")
class ModuleBayTemplate(ModularComponentTemplateModel):
    """Template for a slot in a Device or Module which can contain Modules."""

    position = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        help_text="The position of the module bay within the device or module",
    )
    label = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Physical label")
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    module_family = models.ForeignKey(
        to="dcim.ModuleFamily",
        on_delete=models.PROTECT,
        related_name="module_bay_templates",
        blank=True,
        null=True,
        help_text="Module family that can be installed in this bay. Leave blank for no restriction.",
    )
    requires_first_party_modules = models.BooleanField(
        default=False,
        help_text="This bay will only accept modules from the same manufacturer as the parent device or module",
    )

    natural_key_field_names = ["device_type", "module_type", "name"]

    @property
    def parent(self):
        return self.device_type if self.device_type else self.module_type

    def __str__(self):
        return f"{self.parent} ({self.name})"

    def instantiate(self, device, module=None):
        custom_field_data = {}
        content_type = ContentType.objects.get_for_model(ModuleBay)
        fields = CustomField.objects.filter(content_types=content_type)
        for field in fields:
            custom_field_data[field.key] = field.default

        return ModuleBay(
            parent_device=device,
            parent_module=module,
            name=self.name,
            position=self.position,
            label=self.label,
            description=self.description,
            module_family=self.module_family,
            requires_first_party_modules=self.requires_first_party_modules,
            _custom_field_data=custom_field_data,
        )

    def to_objectchange(self, action, **kwargs):
        """
        Return a new ObjectChange with the `related_object` pinned to the parent `device_type` or `module_type`.
        """
        try:
            parent = self.parent
        except ObjectDoesNotExist:
            # The parent may have already been deleted
            parent = None

        return super().to_objectchange(action, related_object=parent, **kwargs)

    def get_absolute_url(self, api=False):
        if not api:
            return self.parent.get_absolute_url(api=api)
        return super().get_absolute_url(api=api)

    def clean(self):
        super().clean()

        # Validate that a DeviceType or ModuleType is set, but not both
        if self.device_type and self.module_type:
            raise ValidationError("Only one of device_type or module_type must be set")

        if not (self.device_type or self.module_type):
            raise ValidationError("Either device_type or module_type must be set")
