import inspect

from django import forms

from nautobot.cloud.models import (
    CloudAccount,
    CloudAccountGroup,
    CloudNetwork,
    CloudResourceGroup,
    CloudResourceType,
    CloudService,
)
from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.forms import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    MultiValueCharField,
    StaticSelect2,
    TagFilterField,
)
from nautobot.core.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot.core.forms.fields import MultipleContentTypeField
from nautobot.dcim.form_mixins import (
    LocatableModelBulkEditFormMixin,
    LocatableModelFilterFormMixin,
    LocatableModelFormMixin,
)
from nautobot.dcim.models import Manufacturer
from nautobot.extras.forms import (
    NautobotBulkEditForm,
    NautobotFilterForm,
    NautobotModelForm,
    RoleModelBulkEditFormMixin,
    RoleModelFilterFormMixin,
    StatusModelBulkEditFormMixin,
    StatusModelFilterFormMixin,
    TagsBulkEditFormMixin,
)
from nautobot.extras.models import SecretsGroup
from nautobot.ipam.models import IPAddress, Namespace, Prefix
from nautobot.tenancy.forms import TenancyFilterForm, TenancyForm
from nautobot.tenancy.models import Tenant

#
# Cloud Account
#


class CloudAccountForm(NautobotModelForm, TenancyForm):
    provider = DynamicModelChoiceField(
        queryset=Manufacturer.objects.all(),
        help_text="The Manufacturer instance which represents the Cloud Provider",
    )
    cloud_account_group = DynamicModelChoiceField(queryset=CloudAccountGroup.objects.all(), required=False)
    secrets_group = DynamicModelChoiceField(queryset=SecretsGroup.objects.all(), required=False)

    class Meta:
        model = CloudAccount
        fields = [
            "account_number",
            "name",
            "description",
            "provider",
            "cloud_account_group",
            "status",
            "tenant_group",
            "tenant",
            "secrets_group",
            "tags",
        ]


class CloudAccountBulkEditForm(TagsBulkEditFormMixin, StatusModelBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=CloudAccount.objects.all(), widget=forms.MultipleHiddenInput)
    secrets_group = DynamicModelChoiceField(queryset=SecretsGroup.objects.all(), required=False)
    provider = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False)
    cloud_account_group = DynamicModelChoiceField(queryset=CloudAccountGroup.objects.all(), required=False)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        model = CloudAccount
        nullable_fields = [
            "cloud_account_group",
            "tenant",
            "secrets_group",
            "description",
        ]


class CloudAccountFilterForm(NautobotFilterForm, StatusModelFilterFormMixin, TenancyFilterForm):
    model = CloudAccount
    field_order = [
        "q",
        "account_number",
        "name",
        "provider",
        "cloud_account_group",
        "status",
        "tenant_group",
        "tenant",
        "secrets_group",
        "tags",
    ]
    q = forms.CharField(required=False, label="Search")
    name = MultiValueCharField(required=False)
    account_number = MultiValueCharField(required=False)
    cloud_account_group = DynamicModelMultipleChoiceField(
        queryset=CloudAccountGroup.objects.all(), to_field_name="name", required=False
    )
    secrets_group = DynamicModelMultipleChoiceField(
        queryset=SecretsGroup.objects.all(), to_field_name="name", required=False
    )
    provider = DynamicModelMultipleChoiceField(
        queryset=Manufacturer.objects.all(), to_field_name="name", required=False
    )
    tags = TagFilterField(model)


#
# Cloud Account Group
#


class CloudAccountGroupForm(NautobotModelForm):
    parent = DynamicModelChoiceField(queryset=CloudAccountGroup.objects.all(), required=False)
    cloud_resource_type = DynamicModelChoiceField(
        queryset=CloudResourceType.objects.all(),
        query_params={"content_types": [CloudAccountGroup._meta.label_lower]},
    )

    class Meta:
        model = CloudAccountGroup
        fields = [
            "parent",
            "name",
            "description",
            "cloud_resource_type",
            "extra_config",
            "tags",
        ]


class CloudAccountGroupBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=CloudAccountGroup.objects.all(), widget=forms.MultipleHiddenInput)
    parent = DynamicModelChoiceField(queryset=CloudAccountGroup.objects.all(), required=False)
    cloud_resource_type = DynamicModelChoiceField(
        queryset=CloudResourceType.objects.all(),
        query_params={"content_types": [CloudAccountGroup._meta.label_lower]},
        required=False,
    )
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        nullable_fields = ["parent", "description"]


class CloudAccountGroupFilterForm(NautobotFilterForm):
    model = CloudAccountGroup
    field_order = ["q", "name", "parent", "cloud_resource_type", "has_cloud_accounts", "tags"]
    q = forms.CharField(required=False, label="Search")
    name = MultiValueCharField(required=False)
    parent = DynamicModelMultipleChoiceField(
        queryset=CloudAccountGroup.objects.all(), to_field_name="name", required=False
    )
    cloud_resource_type = DynamicModelMultipleChoiceField(
        queryset=CloudResourceType.objects.all(),
        query_params={"content_types": [CloudAccountGroup._meta.label_lower]},
        to_field_name="name",
        required=False,
    )
    has_cloud_accounts = forms.NullBooleanField(
        required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES)
    )
    tags = TagFilterField(model)


#
# Cloud Resource Group
#


class CloudResourceGroupForm(LocatableModelFormMixin, NautobotModelForm):
    cloud_account = DynamicModelChoiceField(queryset=CloudAccount.objects.all())
    cloud_resource_type = DynamicModelChoiceField(
        queryset=CloudResourceType.objects.all(),
        query_params={"content_types": [CloudResourceGroup._meta.label_lower]},
    )

    class Meta:
        model = CloudResourceGroup
        fields = [
            "name",
            "description",
            "provider_resource_id",
            "cloud_account",
            "cloud_resource_type",
            "location",
            "extra_config",
            "tags",
        ]


class CloudResourceGroupBulkEditForm(TagsBulkEditFormMixin, LocatableModelBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=CloudResourceGroup.objects.all(), widget=forms.MultipleHiddenInput)
    cloud_account = DynamicModelChoiceField(queryset=CloudAccount.objects.all(), required=False)
    cloud_resource_type = DynamicModelChoiceField(
        queryset=CloudResourceType.objects.all(),
        query_params={"content_types": [CloudResourceGroup._meta.label_lower]},
        required=False,
    )
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        model = CloudResourceGroup
        nullable_fields = ["location", "description"]


class CloudResourceGroupFilterForm(NautobotFilterForm, LocatableModelFilterFormMixin):
    model = CloudResourceGroup
    field_order = ["q", "name", "cloud_account", "cloud_resource_type", "location", "tags"]
    q = forms.CharField(required=False, label="Search")
    name = MultiValueCharField(required=False)
    cloud_account = DynamicModelMultipleChoiceField(
        queryset=CloudAccount.objects.all(), to_field_name="name", required=False
    )
    cloud_resource_type = DynamicModelMultipleChoiceField(
        queryset=CloudResourceType.objects.all(),
        query_params={"content_types": [CloudResourceGroup._meta.label_lower]},
        to_field_name="name",
        required=False,
    )
    tags = TagFilterField(model)


#
# Cloud Network
#


class CloudNetworkForm(LocatableModelFormMixin, NautobotModelForm, TenancyForm):
    cloud_resource_type = DynamicModelChoiceField(
        queryset=CloudResourceType.objects.all(),
        query_params={"content_types": [CloudNetwork._meta.label_lower]},
    )
    cloud_account = DynamicModelChoiceField(
        queryset=CloudAccount.objects.all(),
    )
    cloud_resource_group = DynamicModelChoiceField(
        queryset=CloudResourceGroup.objects.all(),
        query_params={"cloud_account": "$cloud_account"},
        required=False,
    )
    cloud_services = DynamicModelMultipleChoiceField(
        queryset=CloudService.objects.all(),
        required=False,
    )
    parent = DynamicModelChoiceField(
        queryset=CloudNetwork.objects.all(),
        query_params={"parent__isnull": True},
        required=False,
    )
    namespace = DynamicModelChoiceField(queryset=Namespace.objects.all(), required=False)
    prefixes = DynamicModelMultipleChoiceField(
        queryset=Prefix.objects.all(),
        required=False,
        query_params={"namespace": "$namespace"},
    )

    class Meta:
        model = CloudNetwork
        fields = [
            "name",
            "description",
            "provider_resource_id",
            "cloud_resource_type",
            "cloud_account",
            "cloud_resource_group",
            "parent",
            "location",
            "status",
            "role",
            "tenant_group",
            "tenant",
            "prefixes",
            "extra_config",
            "tags",
        ]
        EXTRA_CONFIG_HELP_TEXT = """
            Optional user-defined <a href="https://json.org/">JSON</a> data for this integration. Example:
            <pre><code class="language-json">{
                "key": "value",
                "key2": [
                    "value1",
                    "value2"
                ]
            }</code></pre>
        """
        help_texts = {
            "extra_config": inspect.cleandoc(EXTRA_CONFIG_HELP_TEXT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.present_in_database:
            self.initial["cloud_services"] = self.instance.cloud_services.values_list("id", flat=True)

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        instance.cloud_services.set(self.cleaned_data["cloud_services"])
        return instance


class CloudNetworkBulkEditForm(
    TagsBulkEditFormMixin,
    LocatableModelBulkEditFormMixin,
    StatusModelBulkEditFormMixin,
    RoleModelBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=CloudNetwork.objects.all(), widget=forms.MultipleHiddenInput)
    cloud_resource_type = DynamicModelChoiceField(
        queryset=CloudResourceType.objects.all(),
        query_params={"content_types": [CloudNetwork._meta.label_lower]},
        required=False,
    )
    cloud_account = DynamicModelChoiceField(queryset=CloudAccount.objects.all(), required=False)
    cloud_resource_group = DynamicModelChoiceField(queryset=CloudResourceGroup.objects.all(), required=False)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    namespace = DynamicModelChoiceField(queryset=Namespace.objects.all(), required=False)
    add_prefixes = DynamicModelMultipleChoiceField(
        queryset=Prefix.objects.all(), required=False, query_params={"namespace": "$namespace"}
    )
    remove_prefixes = DynamicModelMultipleChoiceField(
        queryset=Prefix.objects.all(), required=False, query_params={"namespace": "$namespace"}
    )
    add_cloud_services = DynamicModelMultipleChoiceField(queryset=CloudService.objects.all(), required=False)
    remove_cloud_services = DynamicModelMultipleChoiceField(queryset=CloudService.objects.all(), required=False)

    class Meta:
        model = CloudNetwork
        nullable_fields = [
            "cloud_resource_group",
            "location",
            "role",
            "tenant",
            "description",
        ]


class CloudNetworkFilterForm(
    NautobotFilterForm,
    LocatableModelFilterFormMixin,
    StatusModelFilterFormMixin,
    RoleModelFilterFormMixin,
    TenancyFilterForm,
):
    model = CloudNetwork
    field_order = [
        "q",
        "name",
        "cloud_resource_type",
        "cloud_account",
        "cloud_resource_group",
        "parent",
        "location",
        "status",
        "role",
        "tenant_group",
        "tenant",
        "tags",
    ]
    q = forms.CharField(required=False, label="Search")
    name = MultiValueCharField(required=False)
    cloud_resource_type = DynamicModelMultipleChoiceField(
        queryset=CloudResourceType.objects.all(),
        query_params={"content_types": [CloudNetwork._meta.label_lower]},
        to_field_name="name",
        required=False,
    )
    cloud_account = DynamicModelMultipleChoiceField(
        queryset=CloudAccount.objects.all(), to_field_name="name", required=False
    )
    cloud_resource_group = DynamicModelMultipleChoiceField(
        queryset=CloudResourceGroup.objects.all(), to_field_name="name", required=False
    )
    parent = DynamicModelMultipleChoiceField(
        queryset=CloudNetwork.objects.all(),
        query_params={"parent__isnull": True},
        to_field_name="name",
        required=False,
    )
    tags = TagFilterField(model)


#
# Cloud Resource Type
#


class CloudResourceTypeForm(NautobotModelForm):
    provider = DynamicModelChoiceField(
        queryset=Manufacturer.objects.all(),
        help_text="The Manufacturer instance which represents the Cloud Provider",
    )
    content_types = MultipleContentTypeField(
        feature="cloud_resource_types",
        label="Content Type(s)",
    )

    class Meta:
        model = CloudResourceType
        fields = [
            "name",
            "description",
            "provider",
            "config_schema",
            "content_types",
            "tags",
        ]


class CloudResourceTypeBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=CloudResourceType.objects.all(), widget=forms.MultipleHiddenInput)
    provider = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False)
    content_types = MultipleContentTypeField(
        feature="cloud_resource_types",
        required=False,
        label="Content Type(s)",
    )
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        nullable_fields = [
            "description",
        ]


class CloudResourceTypeFilterForm(NautobotFilterForm):
    model = CloudResourceType
    field_order = [
        "q",
        "name",
        "provider",
        "content_types",
        "tags",
    ]
    q = forms.CharField(required=False, label="Search")
    name = MultiValueCharField(required=False)
    provider = DynamicModelMultipleChoiceField(
        queryset=Manufacturer.objects.all(), to_field_name="name", required=False
    )
    content_types = MultipleContentTypeField(
        feature="cloud_resource_types",
        required=False,
        choices_as_strings=True,
        label="Content Type(s)",
    )
    tags = TagFilterField(model)


#
# Cloud Service
#


class CloudServiceForm(LocatableModelFormMixin, NautobotModelForm, TenancyForm):
    cloud_account = DynamicModelChoiceField(
        queryset=CloudAccount.objects.all(),
        required=False,
    )
    cloud_resource_group = DynamicModelChoiceField(
        queryset=CloudResourceGroup.objects.all(),
        query_params={"cloud_account": "$cloud_account"},
        required=False,
    )
    cloud_networks = DynamicModelMultipleChoiceField(
        queryset=CloudNetwork.objects.all(),
        required=False,
    )
    cloud_resource_type = DynamicModelChoiceField(
        queryset=CloudResourceType.objects.all(),
        query_params={"content_types": [CloudService._meta.label_lower]},
    )
    ip_addresses = DynamicModelMultipleChoiceField(
        queryset=IPAddress.objects.all(),
        required=False,
        label="IP addresses",
    )

    class Meta:
        model = CloudService
        fields = [
            "name",
            "description",
            "provider_resource_id",
            "cloud_resource_type",
            "cloud_account",
            "cloud_resource_group",
            "cloud_networks",
            "ip_addresses",
            "location",
            "status",
            "role",
            "tenant_group",
            "tenant",
            "extra_config",
            "tags",
        ]


class CloudServiceBulkEditForm(
    TagsBulkEditFormMixin,
    LocatableModelBulkEditFormMixin,
    StatusModelBulkEditFormMixin,
    RoleModelBulkEditFormMixin,
    NautobotBulkEditForm,
):
    pk = forms.ModelMultipleChoiceField(queryset=CloudService.objects.all(), widget=forms.MultipleHiddenInput)
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    cloud_resource_type = DynamicModelChoiceField(
        queryset=CloudResourceType.objects.all(),
        query_params={"content_types": [CloudService._meta.label_lower]},
        required=False,
    )
    cloud_account = DynamicModelChoiceField(queryset=CloudAccount.objects.all(), required=False)
    cloud_resource_group = DynamicModelChoiceField(queryset=CloudResourceGroup.objects.all(), required=False)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    add_cloud_networks = DynamicModelMultipleChoiceField(queryset=CloudNetwork.objects.all(), required=False)
    remove_cloud_networks = DynamicModelMultipleChoiceField(queryset=CloudNetwork.objects.all(), required=False)
    extra_config = forms.JSONField(required=False)

    class Meta:
        model = CloudService
        nullable_fields = [
            "cloud_account",
            "cloud_resource_group",
            "location",
            "role",
            "tenant",
            "description",
            "extra_config",
        ]


class CloudServiceFilterForm(
    NautobotFilterForm,
    LocatableModelFilterFormMixin,
    StatusModelFilterFormMixin,
    RoleModelFilterFormMixin,
    TenancyFilterForm,
):
    model = CloudService
    field_order = [
        "q",
        "name",
        "cloud_account",
        "cloud_resource_group",
        "cloud_networks",
        "cloud_resource_type",
        "location",
        "status",
        "role",
        "tenant_group",
        "tenant",
        "tags",
    ]
    q = forms.CharField(required=False, label="Search")
    name = MultiValueCharField(required=False)
    cloud_account = DynamicModelMultipleChoiceField(
        queryset=CloudAccount.objects.all(), to_field_name="name", required=False
    )
    cloud_resource_group = DynamicModelMultipleChoiceField(
        queryset=CloudResourceGroup.objects.all(), to_field_name="name", required=False
    )
    cloud_networks = DynamicModelMultipleChoiceField(
        queryset=CloudNetwork.objects.all(), to_field_name="name", required=False
    )
    cloud_resource_type = DynamicModelMultipleChoiceField(
        queryset=CloudResourceType.objects.all(),
        query_params={"content_types": [CloudService._meta.label_lower]},
        to_field_name="name",
        required=False,
    )
    tags = TagFilterField(model)
