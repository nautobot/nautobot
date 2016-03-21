import django_filters

from dcim.models import Device
from .models import Secret, SecretRole


class SecretFilter(django_filters.FilterSet):
    device_id = django_filters.ModelMultipleChoiceFilter(
        name='device',
        queryset=Device.objects.all(),
        label='Device (ID)',
    )
    device = django_filters.ModelMultipleChoiceFilter(
        name='device',
        queryset=Device.objects.all(),
        to_field_name='name',
        label='Device (name)',
    )
    role_id = django_filters.ModelMultipleChoiceFilter(
        name='role',
        queryset=SecretRole.objects.all(),
        label='Role (ID)',
    )
    role = django_filters.ModelMultipleChoiceFilter(
        name='role',
        queryset=SecretRole.objects.all(),
        to_field_name='slug',
        label='Role (slug)',
    )

    class Meta:
        model = Secret
        fields = ['name', 'device_id', 'device', 'role_id', 'role']
