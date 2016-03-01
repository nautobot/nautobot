from rest_framework import generics

from django.http import Http404
from django.shortcuts import get_object_or_404

from circuits.models import Provider
from dcim.models import Site, Interface
from extras.models import Graph, GRAPH_TYPE_INTERFACE, GRAPH_TYPE_PROVIDER, GRAPH_TYPE_SITE
from .serializers import GraphSerializer


class GraphListView(generics.ListAPIView):
    """
    Returns a list of relevant graphs
    """
    serializer_class = GraphSerializer

    def get_serializer_context(self):
        cls = {
            GRAPH_TYPE_INTERFACE: Interface,
            GRAPH_TYPE_PROVIDER: Provider,
            GRAPH_TYPE_SITE: Site,
        }
        context = super(GraphListView, self).get_serializer_context()
        context.update({'graphed_object': get_object_or_404(cls[self.kwargs.get('type')], pk=self.kwargs['pk'])})
        return context

    def get_queryset(self):
        graph_type = self.kwargs.get('type', None)
        if not graph_type:
            raise Http404()
        queryset = Graph.objects.filter(type=graph_type)
        return queryset
