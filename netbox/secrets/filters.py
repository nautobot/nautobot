import django_filters

from .models import Secret, SecretRole


class SecretFilter(django_filters.FilterSet):
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
        fields = ['name', 'role_id', 'role']
