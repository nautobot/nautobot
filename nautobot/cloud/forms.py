import inspect

from django import forms

from nautobot.cloud.models import CloudAccount, CloudNetwork, CloudService, CloudType
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
        help_text="Manufacturers are the recommended model to represent cloud providers.",
    )
    secrets_group = DynamicModelChoiceField(queryset=SecretsGroup.objects.all())

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
    cloud_type = DynamicModelChoiceField(
        queryset=CloudType.objects.all(),
    )
    cloud_account = DynamicModelChoiceField(
        queryset=CloudAccount.objects.all(),
    )
    parent = DynamicModelChoiceField(
        queryset=CloudNetwork.objects.all(),
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
            "cloud_type",
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


class CloudNetworkBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=CloudNetwork.objects.all(), widget=forms.MultipleHiddenInput)
    cloud_type = DynamicModelChoiceField(queryset=CloudType.objects.all(), required=False)
    cloud_account = DynamicModelChoiceField(queryset=CloudAccount.objects.all(), required=False)
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    namespace = DynamicModelChoiceField(queryset=Namespace.objects.all(), required=False)
    add_prefixes = DynamicModelMultipleChoiceField(
        queryset=Prefix.objects.all(), required=False, query_params={"namespace": "$namespace"}
    )
    remove_prefixes = DynamicModelMultipleChoiceField(
        queryset=Prefix.objects.all(), required=False, query_params={"namespace": "$namespace"}
    )

    class Meta:
        nullable_fields = [
            "description",
        ]


class CloudNetworkFilterForm(NautobotFilterForm):
    model = CloudNetwork
    field_order = [
        "q",
        "name",
        "cloud_type",
        "cloud_account",
        "parent",
        "tags",
    ]
    q = forms.CharField(required=False, label="Search")
    name = MultiValueCharField(required=False)
    cloud_type = DynamicModelMultipleChoiceField(queryset=CloudType.objects.all(), to_field_name="name", required=False)
    cloud_account = DynamicModelMultipleChoiceField(
        queryset=CloudAccount.objects.all(), to_field_name="name", required=False
    )
    parent = DynamicModelMultipleChoiceField(queryset=CloudNetwork.objects.all(), to_field_name="name", required=False)
    tags = TagFilterField(model)


#
# Cloud Type
#


class CloudTypeForm(NautobotModelForm):
    provider = DynamicModelChoiceField(
        queryset=Manufacturer.objects.all(),
        help_text="Manufacturers are the recommended model to represent cloud providers.",
    )
    content_types = MultipleContentTypeField(
        feature="cloud_types",
        label="Content Type(s)",
    )

    class Meta:
        model = CloudType
        fields = [
            "name",
            "description",
            "provider",
            "config_schema",
            "content_types",
            "tags",
        ]


class CloudTypeBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=CloudType.objects.all(), widget=forms.MultipleHiddenInput)
    provider = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False)
    content_types = MultipleContentTypeField(
        feature="cloud_types",
        required=False,
        label="Content Type(s)",
    )
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        nullable_fields = [
            "description",
        ]


class CloudTypeFilterForm(NautobotFilterForm):
    model = CloudType
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
        feature="cloud_types",
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
    cloud_network = DynamicModelChoiceField(
        queryset=CloudNetwork.objects.all(),
    )
    cloud_type = DynamicModelChoiceField(
        queryset=CloudType.objects.all(),
    )

    class Meta:
        model = CloudService
        fields = [
            "name",
            "cloud_account",
            "cloud_network",
            "cloud_type",
            "extra_config",
            "tags",
        ]


class CloudServiceBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=CloudService.objects.all(), widget=forms.MultipleHiddenInput)
    cloud_account = DynamicModelChoiceField(queryset=CloudAccount.objects.all(), required=False)
    cloud_network = DynamicModelChoiceField(queryset=CloudNetwork.objects.all(), required=False)
    cloud_type = DynamicModelChoiceField(queryset=CloudType.objects.all(), required=False)
    extra_config = forms.JSONField(required=False)

    class Meta:
        nullable_fields = ["cloud_account", "extra_config"]


class CloudServiceFilterForm(NautobotFilterForm):
    model = CloudService
    field_order = [
        "q",
        "name",
        "cloud_account",
        "cloud_network",
        "cloud_type",
        "tags",
    ]
    q = forms.CharField(required=False, label="Search")
    name = MultiValueCharField(required=False)
    cloud_account = DynamicModelMultipleChoiceField(
        queryset=CloudAccount.objects.all(), to_field_name="name", required=False
    )
    cloud_network = DynamicModelMultipleChoiceField(
        queryset=CloudNetwork.objects.all(), to_field_name="name", required=False
    )
    cloud_type = DynamicModelMultipleChoiceField(queryset=CloudType.objects.all(), to_field_name="name", required=False)
    tags = TagFilterField(model)
