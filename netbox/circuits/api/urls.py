from django.conf.urls import url

from extras.models import GRAPH_TYPE_PROVIDER
from extras.api.views import GraphListView

from .views import *


urlpatterns = [

    # Providers
    url(r'^providers/$', ProviderListView.as_view(), name='provider_list'),
    url(r'^providers/(?P<pk>\d+)/$', ProviderDetailView.as_view(), name='provider_detail'),
    url(r'^providers/(?P<pk>\d+)/graphs/$', GraphListView.as_view(), {'type': GRAPH_TYPE_PROVIDER},
        name='provider_graphs'),

    # Circuit types
    url(r'^circuit-types/$', CircuitTypeListView.as_view(), name='circuittype_list'),
    url(r'^circuit-types/(?P<pk>\d+)/$', CircuitTypeDetailView.as_view(), name='circuittype_detail'),

    # Circuits
    url(r'^circuits/$', CircuitListView.as_view(), name='circuit_list'),
    url(r'^circuits/(?P<pk>\d+)/$', CircuitDetailView.as_view(), name='circuit_detail'),

]
