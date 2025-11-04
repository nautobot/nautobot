"""Forms for nautobot_load_balancer_models."""

from django import forms

from nautobot.cloud.models import CloudService
from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.forms import (
    add_blank_choice,
    BulkEditNullBooleanSelect,
    DateTimePicker,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    StaticSelect2,
    TagFilterField,
)
from nautobot.dcim.models import Device, DeviceRedundancyGroup, VirtualChassis
from nautobot.extras.forms import (
    NautobotBulkEditForm,
    NautobotFilterForm,
    NautobotModelForm,
    StatusModelBulkEditFormMixin,
    TagsBulkEditFormMixin,
)
from nautobot.ipam.models import IPAddress, Prefix
from nautobot.load_balancers import choices, models
from nautobot.tenancy.forms import TenancyFilterForm, TenancyForm
from nautobot.tenancy.models import Tenant


class VirtualServerForm(NautobotModelForm, TenancyForm):  # pylint: disable=too-many-ancestors
    """VirtualServer creation/edit form."""

    vip = DynamicModelChoiceField(queryset=IPAddress.objects.all(), label="VIP")
    load_balancer_type = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.LoadBalancerTypeChoices),
        widget=StaticSelect2,
        label="Load Balancer Type",
    )
    protocol = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.ProtocolChoices),
        widget=StaticSelect2,
        label="Protocol",
    )
    load_balancer_pool = DynamicModelChoiceField(
        queryset=models.LoadBalancerPool.objects.all(), required=False, label="Load Balancer Pool"
    )
    source_nat_pool = DynamicModelChoiceField(queryset=Prefix.objects.all(), required=False, label="Source NAT Pool")
    source_nat_type = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.SourceNATTypeChoices),
        widget=StaticSelect2,
        label="Source NAT Type",
    )
    health_check_monitor = DynamicModelChoiceField(
        queryset=models.HealthCheckMonitor.objects.all(), required=False, label="Health Check Monitor"
    )
    device = DynamicModelChoiceField(queryset=Device.objects.all(), required=False)
    device_redundancy_group = DynamicModelChoiceField(queryset=DeviceRedundancyGroup.objects.all(), required=False)
    cloud_service = DynamicModelChoiceField(queryset=CloudService.objects.all(), required=False)
    virtual_chassis = DynamicModelChoiceField(queryset=VirtualChassis.objects.all(), required=False)
    certificate_profiles = DynamicModelMultipleChoiceField(
        queryset=models.CertificateProfile.objects.all(),
        required=False,
        label="Certificate Profile(s)",
    )

    field_order = [
        "name",
        "vip",
        "port",
        "protocol",
        "enabled",
        "load_balancer_type",
        "tenant_group",
        "tenant",
        "load_balancer_pool",
        "source_nat_pool",
        "source_nat_type",
        "device",
        "device_redundancy_group",
        "cloud_service",
        "virtual_chassis",
        "health_check_monitor",
        "ssl_offload",
        "certificate_profiles",
    ]

    class Meta:
        """Meta attributes."""

        model = models.VirtualServer
        fields = "__all__"


class VirtualServerBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """VirtualServer bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=models.VirtualServer.objects.all(), widget=forms.MultipleHiddenInput)
    enabled = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    port = forms.IntegerField(required=False)
    protocol = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.ProtocolChoices),
        widget=StaticSelect2,
        label="Protocol",
    )
    load_balancer_pool = DynamicModelChoiceField(
        queryset=models.LoadBalancerPool.objects.all(), required=False, label="Load Balancer Pool"
    )
    load_balancer_type = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.LoadBalancerTypeChoices),
        widget=StaticSelect2,
        label="Load Balancer Type",
    )
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    source_nat_pool = DynamicModelChoiceField(queryset=Prefix.objects.all(), required=False, label="Source NAT Pool")
    source_nat_type = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.SourceNATTypeChoices),
        widget=StaticSelect2,
        label="Source NAT Type",
    )
    device = DynamicModelChoiceField(queryset=Device.objects.all(), required=False)
    device_redundancy_group = DynamicModelChoiceField(queryset=DeviceRedundancyGroup.objects.all(), required=False)
    cloud_service = DynamicModelChoiceField(queryset=CloudService.objects.all(), required=False)
    virtual_chassis = DynamicModelChoiceField(queryset=VirtualChassis.objects.all(), required=False)
    health_check_monitor = DynamicModelChoiceField(queryset=models.HealthCheckMonitor.objects.all(), required=False)
    ssl_offload = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect, label="SSL Offload")
    add_certificate_profiles = DynamicModelMultipleChoiceField(
        queryset=models.CertificateProfile.objects.all(),
        required=False,
    )
    remove_certificate_profiles = DynamicModelMultipleChoiceField(
        queryset=models.CertificateProfile.objects.all(),
        required=False,
    )

    class Meta:
        """Meta attributes."""

        nullable_fields = [
            "cloud_service",
            "device",
            "device_redundancy_group",
            "health_check_monitor",
            "load_balancer_pool",
            "load_balancer_type",
            "port",
            "protocol",
            "source_nat_pool",
            "source_nat_type",
            "tenant",
            "virtual_chassis",
        ]


class VirtualServerFilterForm(NautobotFilterForm, TenancyFilterForm):  # pylint: disable=too-many-ancestors
    """Filter form to filter searches."""

    model = models.VirtualServer
    field_order = ["name"]
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(required=False, label="Name")
    source_nat_pool = DynamicModelMultipleChoiceField(
        queryset=Prefix.objects.all(),
        to_field_name="name",
        required=False,
        label="Prefix",
    )
    load_balancer_pool = DynamicModelMultipleChoiceField(
        queryset=models.LoadBalancerPool.objects.all(),
        to_field_name="name",
        required=False,
        label="Load Balancer Pool",
    )
    device = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        to_field_name="name",
        required=False,
        label="Device",
    )
    device_redundancy_group = DynamicModelMultipleChoiceField(
        queryset=DeviceRedundancyGroup.objects.all(),
        to_field_name="name",
        required=False,
        label="Device Redundancy Group",
    )
    cloud_service = DynamicModelMultipleChoiceField(
        queryset=CloudService.objects.all(),
        to_field_name="name",
        required=False,
        label="Cloud Service",
    )
    virtual_chassis = DynamicModelMultipleChoiceField(
        queryset=VirtualChassis.objects.all(),
        to_field_name="name",
        required=False,
        label="Virtual Chassis",
    )
    health_check_monitor = DynamicModelMultipleChoiceField(
        queryset=models.HealthCheckMonitor.objects.all(),
        to_field_name="name",
        required=False,
        label="Health Check Monitor",
    )
    tags = TagFilterField(model)


class LoadBalancerPoolForm(NautobotModelForm, TenancyForm):  # pylint: disable=too-many-ancestors
    """Form for creating and updating LoadBalancerPool."""

    health_check_monitor = DynamicModelChoiceField(
        queryset=models.HealthCheckMonitor.objects.all(),
        required=False,
        label="Health Check Monitor",
    )
    load_balancing_algorithm = forms.ChoiceField(
        required=True,
        choices=add_blank_choice(choices.LoadBalancingAlgorithmChoices),
        widget=StaticSelect2,
        label="Load Balancing Algorithm",
    )

    field_order = [
        "name",
        "load_balancing_algorithm",
        "tenant_group",
        "tenant",
        "health_check_monitor",
    ]

    class Meta:
        """Meta attributes."""

        model = models.LoadBalancerPool
        fields = "__all__"


class LoadBalancerPoolBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """LoadBalancerPool bulk edit form."""

    pk = forms.ModelMultipleChoiceField(
        queryset=models.LoadBalancerPool.objects.all(), widget=forms.MultipleHiddenInput
    )
    name = forms.CharField(required=False, label="Name")
    load_balancing_algorithm = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.LoadBalancingAlgorithmChoices),
        widget=StaticSelect2,
        label="Load Balancing Algorithm",
    )
    health_check_monitor = DynamicModelChoiceField(
        queryset=models.HealthCheckMonitor.objects.all(),
        required=False,
        label="Health Check Monitor",
    )
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)

    class Meta:
        """Meta attributes."""

        model = models.LoadBalancerPool
        nullable_fields = [
            "tenant",
            "health_check_monitor",
        ]


class LoadBalancerPoolFilterForm(NautobotFilterForm, TenancyFilterForm):  # pylint: disable=too-many-ancestors
    """Filter form for LoadBalancerPool."""

    model = models.LoadBalancerPool
    field_order = ["name"]
    q = forms.CharField(required=False, label="Search")
    health_check_monitor = DynamicModelMultipleChoiceField(
        queryset=models.HealthCheckMonitor.objects.all(),
        to_field_name="name",
        required=False,
        label="Health Check Monitor",
    )
    name = forms.CharField(required=False, label="Name")
    tags = TagFilterField(model)


class LoadBalancerPoolMemberForm(NautobotModelForm, TenancyForm):  # pylint: disable=too-many-ancestors
    """Form for creating and updating LoadBalancerPoolMember."""

    ip_address = DynamicModelChoiceField(
        queryset=IPAddress.objects.all(),
        required=True,
        label="IP Address",
    )
    load_balancer_pool = DynamicModelChoiceField(
        queryset=models.LoadBalancerPool.objects.all(),
        required=True,
        label="Load Balancer Pool",
    )
    health_check_monitor = DynamicModelChoiceField(
        queryset=models.HealthCheckMonitor.objects.all(),
        required=False,
        label="Health Check Monitor",
    )
    certificate_profiles = DynamicModelMultipleChoiceField(
        queryset=models.CertificateProfile.objects.all(),
        required=False,
        label="Certificate Profile",
    )

    field_order = [
        "load_balancer_pool",
        "ip_address",
        "port",
        "status",
        "label",
        "tenant_group",
        "tenant",
        "health_check_monitor",
        "ssl_offload",
        "certificate_profiles",
    ]

    class Meta:
        """Meta attributes."""

        model = models.LoadBalancerPoolMember
        fields = "__all__"


class LoadBalancerPoolMemberBulkEditForm(StatusModelBulkEditFormMixin, TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """LoadBalancerPoolMember bulk edit form."""

    pk = forms.ModelMultipleChoiceField(
        queryset=models.LoadBalancerPoolMember.objects.all(), widget=forms.MultipleHiddenInput
    )
    label = forms.CharField(required=False)
    ip_address = DynamicModelChoiceField(
        queryset=IPAddress.objects.all(),
        required=False,
        label="IP Address",
    )
    load_balancer_pool = DynamicModelChoiceField(
        queryset=models.LoadBalancerPool.objects.all(),
        required=False,
        label="Load Balancer Pool",
    )
    port = forms.IntegerField(required=False, label="Port")
    ssl_offload = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect, label="SSL Offload")
    health_check_monitor = DynamicModelChoiceField(
        queryset=models.HealthCheckMonitor.objects.all(),
        required=False,
        label="Health Check Monitor",
    )
    add_certificate_profiles = DynamicModelMultipleChoiceField(
        queryset=models.CertificateProfile.objects.all(),
        required=False,
    )
    remove_certificate_profiles = DynamicModelMultipleChoiceField(
        queryset=models.CertificateProfile.objects.all(),
        required=False,
    )
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)

    class Meta:
        """Meta attributes."""

        model = models.LoadBalancerPoolMember
        nullable_fields = [
            "health_check_monitor",
            "label",
            "tenant",
        ]


class LoadBalancerPoolMemberFilterForm(NautobotFilterForm, TenancyFilterForm):  # pylint: disable=too-many-ancestors
    """Filter form for LoadBalancerPoolMember."""

    model = models.LoadBalancerPoolMember
    q = forms.CharField(required=False, label="Search")
    load_balancer_pool = DynamicModelMultipleChoiceField(
        queryset=models.LoadBalancerPool.objects.all(),
        to_field_name="name",
        required=False,
        label="Load Balancer Pool",
    )
    health_check_monitor = DynamicModelMultipleChoiceField(
        queryset=models.HealthCheckMonitor.objects.all(),
        to_field_name="name",
        required=False,
        label="Health Check Monitor",
    )
    certificate_profiles = DynamicModelMultipleChoiceField(
        queryset=models.CertificateProfile.objects.all(),
        to_field_name="name",
        required=False,
        label="Certificate Profile(s)",
    )
    tags = TagFilterField(model)


class HealthCheckMonitorForm(NautobotModelForm, TenancyForm):  # pylint: disable=too-many-ancestors
    """Form for creating and updating HealthCheckMonitor."""

    field_order = [
        "name",
        "health_check_type",
        "port",
        "interval",
        "timeout",
        "retry",
        "tenant_group",
        "tenant",
    ]

    class Meta:
        """Meta attributes."""

        model = models.HealthCheckMonitor
        fields = "__all__"


class HealthCheckMonitorBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """HealthCheckMonitor bulk edit form."""

    pk = forms.ModelMultipleChoiceField(
        queryset=models.HealthCheckMonitor.objects.all(), widget=forms.MultipleHiddenInput
    )
    name = forms.CharField(required=False, label="Name")
    interval = forms.IntegerField(required=False, label="Interval")
    retry = forms.IntegerField(required=False, label="Retry")
    timeout = forms.IntegerField(required=False, label="Timeout")
    port = forms.IntegerField(required=False, label="Port")
    health_check_type = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.HealthCheckTypeChoices),
        widget=StaticSelect2,
        label="Health Check Type",
    )
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)

    class Meta:
        """Meta attributes."""

        model = models.HealthCheckMonitor
        nullable_fields = [
            "interval",
            "retry",
            "timeout",
            "port",
            "health_check_type",
            "tenant",
        ]


class HealthCheckMonitorFilterForm(NautobotFilterForm, TenancyFilterForm):  # pylint: disable=too-many-ancestors
    """Filter form for HealthCheckMonitor."""

    model = models.HealthCheckMonitor
    q = forms.CharField(required=False, label="Search")
    tags = TagFilterField(models.HealthCheckMonitor)


class CertificateProfileForm(NautobotModelForm, TenancyForm):  # pylint: disable=too-many-ancestors
    """Form for creating and updating CertificateProfile."""

    field_order = [
        "name",
        "certificate_type",
        "certificate_file_path",
        "chain_file_path",
        "key_file_path",
        "expiration_date",
        "cipher",
        "tenant_group",
        "tenant",
    ]

    class Meta:
        """Meta attributes."""

        model = models.CertificateProfile
        fields = "__all__"
        widgets = {
            "expiration_date": DateTimePicker(),
        }


class CertificateProfileBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """CertificateProfile bulk edit form."""

    pk = forms.ModelMultipleChoiceField(
        queryset=models.CertificateProfile.objects.all(), widget=forms.MultipleHiddenInput
    )
    name = forms.CharField(required=False, label="Name")
    certificate_type = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(choices.CertificateTypeChoices),
        widget=StaticSelect2,
        label="Certificate Type",
    )
    certificate_file_path = forms.CharField(
        required=False, max_length=CHARFIELD_MAX_LENGTH, label="Certificate File Path"
    )
    chain_file_path = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH, label="Chain File Path")
    key_file_path = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH, label="Key File Path")
    expiration_date = forms.DateTimeField(required=False, label="Expiration Date", widget=DateTimePicker)
    cipher = forms.CharField(required=False, label="Cipher")
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)

    class Meta:
        """Meta attributes."""

        model = models.CertificateProfile
        nullable_fields = [
            "certificate_type",
            "certificate_file_path",
            "chain_file_path",
            "key_file_path",
            "expiration_date",
            "cipher",
            "tenant",
        ]


class CertificateProfileFilterForm(NautobotFilterForm, TenancyFilterForm):  # pylint: disable=too-many-ancestors
    """Filter form for CertificateProfile."""

    model = models.CertificateProfile
    q = forms.CharField(required=False, label="Search")
    tags = TagFilterField(model)
