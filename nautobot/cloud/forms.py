import inspect

from django import forms

from nautobot.cloud.models import CloudAccount, CloudNetwork, CloudResourceType, CloudService
from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.forms import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    MultiValueCharField,
    TagFilterField,
)
from nautobot.core.forms.fields import MultipleContentTypeField
from nautobot.dcim.models import Manufacturer
from nautobot.extras.forms import NautobotBulkEditForm, NautobotFilterForm, NautobotModelForm, TagsBulkEditFormMixin
from nautobot.extras.models import SecretsGroup
from nautobot.ipam.models import Namespace, Prefix

#
# Cloud Account
#


class CloudAccountForm(NautobotModelForm):
    provider = DynamicModelChoiceField(
        queryset=Manufacturer.objects.all(),
        help_text="The Manufacturer instance which represents the Cloud Provider",
    )
    secrets_group = DynamicModelChoiceField(queryset=SecretsGroup.objects.all(), required=False)

    class Meta:
        model = CloudAccount
        fields = [
            "account_number",
            "name",
            "description",
            "provider",
            "secrets_group",
            "tags",
        ]


class CloudAccountBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=CloudAccount.objects.all(), widget=forms.MultipleHiddenInput)
    secrets_group = DynamicModelChoiceField(queryset=SecretsGroup.objects.all(), required=False)
    provider = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False)
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        nullable_fields = [
            "secrets_group",
            "description",
        ]


class CloudAccountFilterForm(NautobotFilterForm):
    model = CloudAccount
    field_order = [
        "q",
        "account_number",
        "name",
        "provider",
        "secrets_group",
        "tags",
    ]
    q = forms.CharField(required=False, label="Search")
    name = MultiValueCharField(required=False)
    account_number = MultiValueCharField(required=False)
    secrets_group = DynamicModelMultipleChoiceField(
        queryset=SecretsGroup.objects.all(), to_field_name="name", required=False
    )
    provider = DynamicModelMultipleChoiceField(
        queryset=Manufacturer.objects.all(), to_field_name="name", required=False
    )
    tags = TagFilterField(model)


#
# Cloud Network
#


class CloudNetworkForm(NautobotModelForm):
    cloud_resource_type = DynamicModelChoiceField(
        queryset=CloudResourceType.objects.all(),
        query_params={"content_types": [CloudNetwork._meta.label_lower]},
    )
    cloud_account = DynamicModelChoiceField(
        queryset=CloudAccount.objects.all(),
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
            "cloud_resource_type",
            "cloud_account",
            "parent",
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


class CloudNetworkBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=CloudNetwork.objects.all(), widget=forms.MultipleHiddenInput)
    cloud_resource_type = DynamicModelChoiceField(
        queryset=CloudResourceType.objects.all(),
        query_params={"content_types": [CloudNetwork._meta.label_lower]},
        required=False,
    )
    cloud_account = DynamicModelChoiceField(queryset=CloudAccount.objects.all(), required=False)
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
        nullable_fields = [
            "description",
        ]


class CloudNetworkFilterForm(NautobotFilterForm):
    model = CloudNetwork
    field_order = [
        "q",
        "name",
        "cloud_resource_type",
        "cloud_account",
        "parent",
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


class CloudServiceForm(NautobotModelForm):
    cloud_account = DynamicModelChoiceField(
        queryset=CloudAccount.objects.all(),
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

    class Meta:
        model = CloudService
        fields = [
            "name",
            "description",
            "cloud_resource_type",
            "cloud_account",
            "cloud_networks",
            "extra_config",
            "tags",
        ]


class CloudServiceBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=CloudService.objects.all(), widget=forms.MultipleHiddenInput)
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    cloud_resource_type = DynamicModelChoiceField(
        queryset=CloudResourceType.objects.all(),
        query_params={"content_types": [CloudService._meta.label_lower]},
        required=False,
    )
    cloud_account = DynamicModelChoiceField(queryset=CloudAccount.objects.all(), required=False)
    add_cloud_networks = DynamicModelMultipleChoiceField(queryset=CloudNetwork.objects.all(), required=False)
    remove_cloud_networks = DynamicModelMultipleChoiceField(queryset=CloudNetwork.objects.all(), required=False)
    extra_config = forms.JSONField(required=False)

    class Meta:
        nullable_fields = ["cloud_account", "description", "extra_config"]


class CloudServiceFilterForm(NautobotFilterForm):
    model = CloudService
    field_order = [
        "q",
        "name",
        "cloud_account",
        "cloud_networks",
        "cloud_resource_type",
        "tags",
    ]
    q = forms.CharField(required=False, label="Search")
    name = MultiValueCharField(required=False)
    cloud_account = DynamicModelMultipleChoiceField(
        queryset=CloudAccount.objects.all(), to_field_name="name", required=False
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
