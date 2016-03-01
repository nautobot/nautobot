import django_filters

from dcim.models import Site
from circuits.models import Provider, Circuit, CircuitType


class CircuitFilter(django_filters.FilterSet):
    q = django_filters.MethodFilter(
        action='search',
        label='Search',
    )
    provider_id = django_filters.ModelMultipleChoiceFilter(
        name='provider',
        queryset=Provider.objects.all(),
        label='Provider (ID)',
    )
    provider = django_filters.ModelMultipleChoiceFilter(
        name='provider',
        queryset=Provider.objects.all(),
        to_field_name='slug',
        label='Provider (slug)',
    )
    type_id = django_filters.ModelMultipleChoiceFilter(
        name='type',
        queryset=CircuitType.objects.all(),
        label='Circuit type (ID)',
    )
    type = django_filters.ModelMultipleChoiceFilter(
        name='type',
        queryset=CircuitType.objects.all(),
        to_field_name='slug',
        label='Circuit type (slug)',
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        name='site',
        queryset=Site.objects.all(),
        label='Site (ID)',
    )
    site = django_filters.ModelMultipleChoiceFilter(
        name='site',
        queryset=Site.objects.all(),
        to_field_name='slug',
        label='Site (slug)',
    )

    class Meta:
        model = Circuit
        fields = ['q', 'provider_id', 'provider', 'type_id', 'type', 'site_id', 'site', 'interface', 'install_date']

    def search(self, queryset, value):
        value = value.strip()
        return queryset.filter(cid__icontains=value)
