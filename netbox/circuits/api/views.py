from rest_framework import generics

from circuits.models import Provider, CircuitType, Circuit
from circuits.filters import CircuitFilter
from .serializers import ProviderSerializer, CircuitTypeSerializer, CircuitSerializer


class ProviderListView(generics.ListAPIView):
    """
    List all providers
    """
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer


class ProviderDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single provider
    """
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer


class CircuitTypeListView(generics.ListAPIView):
    """
    List all circuit types
    """
    queryset = CircuitType.objects.all()
    serializer_class = CircuitTypeSerializer


class CircuitTypeDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single circuit type
    """
    queryset = CircuitType.objects.all()
    serializer_class = CircuitTypeSerializer


class CircuitListView(generics.ListAPIView):
    """
    List circuits (filterable)
    """
    queryset = Circuit.objects.select_related('type', 'provider', 'site', 'interface__device')
    serializer_class = CircuitSerializer
    filter_class = CircuitFilter


class CircuitDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single circuit
    """
    queryset = Circuit.objects.select_related('type', 'provider', 'site', 'interface__device')
    serializer_class = CircuitSerializer
