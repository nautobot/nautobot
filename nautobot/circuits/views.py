from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django_tables2 import RequestConfig
from rest_framework.routers import Route


from nautobot.core.views import generic
from nautobot.utilities.forms import ConfirmationForm
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count

# from nautobot.utilities.utils import count_related

from . import filters, forms, tables
from .api import nested_serializers
from .choices import CircuitTerminationSideChoices
from .models import Circuit, CircuitType, CircuitTermination, Provider, ProviderNetwork
from nautobot.utilities.viewsets import NautobotViewSet, NautobotRouter
from nautobot.utilities.drf_views import NautobotDRFViewSet


class CircuitTypeDRFViewSet(NautobotDRFViewSet):
    model = CircuitType
    serializer_class = nested_serializers.NestedCircuitTypeSerializer
    queryset = CircuitType.objects.all()
    table = tables.CircuitTypeTable
    form = forms.CircuitTypeForm
    filterset = filters.CircuitTypeFilterSet
    import_form = forms.CircuitTypeCSVForm
    lookup_field = "slug"

    def get_extra_context(self, request, view_type, instance):
        # Circuits
        if view_type == "detail":
            circuits = (
                Circuit.objects.restrict(request.user, "view")
                .filter(type=instance)
                .prefetch_related("type", "tenant", "terminations__site")
            )

            circuits_table = tables.CircuitTable(circuits)
            circuits_table.columns.hide("type")

            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(circuits_table)
            return {
                "circuits_table": circuits_table,
            }
        elif view_type == "list":
            return {}
        elif view_type == "bulk_edit":
            return {}
        else:
            return {}


class ProviderDRFViewSet(NautobotDRFViewSet):
    model = Provider
    serializer_class = nested_serializers.NestedProviderSerializer
    queryset = Provider.objects.all()
    table = tables.ProviderTable
    form = forms.ProviderForm
    filterset_form = forms.ProviderFilterForm
    filterset = filters.ProviderFilterSet
    import_form = forms.ProviderCSVForm
    bulk_edit_form = forms.ProviderBulkEditForm
    lookup_field = "slug"

    def get_extra_context(self, request, view_type, instance):
        if view_type == "detail":
            circuits = (
                Circuit.objects.restrict(request.user, "view")
                .filter(provider=instance)
                .prefetch_related("type", "tenant", "terminations__site")
            )

            circuits_table = tables.CircuitTable(circuits)
            circuits_table.columns.hide("provider")

            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(circuits_table)

            return {
                "circuits_table": circuits_table,
            }
        elif view_type == "list":
            return {}
        elif view_type == "bulk_edit":
            return {}
        else:
            return {}


class CircuitDRFViewSet(NautobotDRFViewSet):
    model = Circuit
    prefetch_related = ["provider", "type", "tenant", "termination_a", "termination_z"]
    serializer_class = nested_serializers.NestedCircuitSerializer
    queryset = Circuit.objects.all()
    table = tables.CircuitTable
    form = forms.CircuitForm
    filterset = filters.CircuitFilterSet
    filterset_form = forms.CircuitFilterForm
    import_form = forms.CircuitCSVForm
    bulk_edit_form = forms.CircuitBulkEditForm
    lookup_field = "pk"

    def get_extra_context(self, request, view_type, instance):
        if view_type == "detail":
            # A-side termination
            termination_a = (
                CircuitTermination.objects.restrict(request.user, "view")
                .prefetch_related("site__region")
                .filter(circuit=instance, term_side=CircuitTerminationSideChoices.SIDE_A)
                .first()
            )
            if (
                termination_a
                and termination_a.connected_endpoint
                and hasattr(termination_a.connected_endpoint, "ip_addresses")
            ):
                termination_a.ip_addresses = termination_a.connected_endpoint.ip_addresses.restrict(
                    request.user, "view"
                )

            # Z-side termination
            termination_z = (
                CircuitTermination.objects.restrict(request.user, "view")
                .prefetch_related("site__region")
                .filter(circuit=instance, term_side=CircuitTerminationSideChoices.SIDE_Z)
                .first()
            )
            if (
                termination_z
                and termination_z.connected_endpoint
                and hasattr(termination_z.connected_endpoint, "ip_addresses")
            ):
                termination_z.ip_addresses = termination_z.connected_endpoint.ip_addresses.restrict(
                    request.user, "view"
                )

            return {
                "termination_a": termination_a,
                "termination_z": termination_z,
            }
        elif view_type == "list":
            return {}
        elif view_type == "bulk_edit":
            return {}
        else:
            return {}


class ProviderNetworkDRFViewSet(NautobotDRFViewSet):
    model = ProviderNetwork
    queryset = ProviderNetwork.objects.all()
    serializer_class = nested_serializers.NestedProviderNetworkSerializer
    table = tables.ProviderNetworkTable
    form = forms.ProviderNetworkForm
    filterset_form = forms.ProviderNetworkFilterForm
    filterset = filters.ProviderNetworkFilterSet
    import_form = forms.ProviderNetworkCSVForm
    bulk_edit_form = forms.ProviderNetworkBulkEditForm
    lookup_field = "slug"

    def get_extra_context(self, request, view_type, instance):
        if view_type == "detail":
            circuits = (
                Circuit.objects.restrict(request.user, "view")
                .filter(Q(termination_a__provider_network=instance.pk) | Q(termination_z__provider_network=instance.pk))
                .prefetch_related("type", "tenant", "terminations__site")
            )

            circuits_table = tables.CircuitTable(circuits)
            circuits_table.columns.hide("termination_a")
            circuits_table.columns.hide("termination_z")

            paginate = {"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
            RequestConfig(request, paginate).configure(circuits_table)

            return {
                "circuits_table": circuits_table,
            }
        elif view_type == "list":
            return {}
        elif view_type == "bulk_edit":
            return {}
        else:
            return {}


#
# Providers
#


class ProviderViewSet(NautobotViewSet):
    model = Provider
    table = tables.ProviderTable
    form = forms.ProviderForm
    filterset_form = forms.ProviderFilterForm
    filterset = filters.ProviderFilterSet
    import_form = forms.ProviderCSVForm
    bulk_edit_form = forms.ProviderBulkEditForm
    lookup_field = "slug"

    def get_extra_context(self, request, view_type, instance):
        if view_type == "detail":
            circuits = (
                Circuit.objects.restrict(request.user, "view")
                .filter(provider=instance)
                .prefetch_related("type", "tenant", "terminations__site")
            )

            circuits_table = tables.CircuitTable(circuits)
            circuits_table.columns.hide("provider")

            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(circuits_table)

            return {
                "circuits_table": circuits_table,
            }
        elif view_type == "list":
            return {}
        elif view_type == "bulk_edit":
            return {}
        else:
            return {}


class ProviderViewSetRouter(NautobotRouter):
    viewset = ProviderViewSet

    def __init__(self, prefix, basename):
        super().__init__(prefix, basename)


class ProviderNetworkViewSet(NautobotViewSet):
    model = ProviderNetwork
    table = tables.ProviderNetworkTable
    form = forms.ProviderNetworkForm
    filterset_form = forms.ProviderNetworkFilterForm
    filterset = filters.ProviderNetworkFilterSet
    import_form = forms.ProviderNetworkCSVForm
    bulk_edit_form = forms.ProviderNetworkBulkEditForm
    lookup_field = "slug"

    def get_extra_context(self, request, view_type, instance):
        if view_type == "detail":
            circuits = (
                Circuit.objects.restrict(request.user, "view")
                .filter(Q(termination_a__provider_network=instance.pk) | Q(termination_z__provider_network=instance.pk))
                .prefetch_related("type", "tenant", "terminations__site")
            )

            circuits_table = tables.CircuitTable(circuits)
            circuits_table.columns.hide("termination_a")
            circuits_table.columns.hide("termination_z")

            paginate = {"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
            RequestConfig(request, paginate).configure(circuits_table)

            return {
                "circuits_table": circuits_table,
            }
        elif view_type == "list":
            return {}
        elif view_type == "bulk_edit":
            return {}
        else:
            return {}


class ProviderNetworkViewSetRouter(NautobotRouter):
    viewset = ProviderNetworkViewSet

    def __init__(self, prefix, basename):
        super().__init__(prefix, basename)


#
# Circuit Types
#


class CircuitTypeViewSet(NautobotViewSet):
    model = CircuitType
    queryset = CircuitType.objects.all()
    table = tables.CircuitTypeTable
    form = forms.CircuitTypeForm
    filterset = filters.CircuitTypeFilterSet
    import_form = forms.CircuitTypeCSVForm
    lookup_field = "slug"

    def get_extra_context(self, request, view_type, instance):
        # Circuits
        if view_type == "detail":
            circuits = (
                Circuit.objects.restrict(request.user, "view")
                .filter(type=instance)
                .prefetch_related("type", "tenant", "terminations__site")
            )

            circuits_table = tables.CircuitTable(circuits)
            circuits_table.columns.hide("type")

            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(circuits_table)

            return {
                "circuits_table": circuits_table,
            }
        elif view_type == "list":
            return {}
        elif view_type == "bulk_edit":
            return {}
        else:
            return {}


class CircuitTypeViewSetRouter(NautobotRouter):
    viewset = CircuitTypeViewSet
    exclude_views = ["bulk_edit"]

    def __init__(self, prefix, basename):
        super().__init__(prefix, basename)


#
# Circuits
#


class CircuitViewSet(NautobotViewSet):
    model = Circuit
    prefetch_related = ["provider", "type", "tenant", "termination_a", "termination_z"]
    queryset = Circuit.objects.all()
    table = tables.CircuitTable
    form = forms.CircuitForm
    filterset = filters.CircuitFilterSet
    filterset_form = forms.CircuitFilterForm
    import_form = forms.CircuitCSVForm
    bulk_edit_form = forms.CircuitBulkEditForm
    lookup_field = "pk"

    def get_extra_context(self, request, view_type, instance):
        if view_type == "detail":
            # A-side termination
            termination_a = (
                CircuitTermination.objects.restrict(request.user, "view")
                .prefetch_related("site__region")
                .filter(circuit=instance, term_side=CircuitTerminationSideChoices.SIDE_A)
                .first()
            )
            if (
                termination_a
                and termination_a.connected_endpoint
                and hasattr(termination_a.connected_endpoint, "ip_addresses")
            ):
                termination_a.ip_addresses = termination_a.connected_endpoint.ip_addresses.restrict(
                    request.user, "view"
                )

            # Z-side termination
            termination_z = (
                CircuitTermination.objects.restrict(request.user, "view")
                .prefetch_related("site__region")
                .filter(circuit=instance, term_side=CircuitTerminationSideChoices.SIDE_Z)
                .first()
            )
            if (
                termination_z
                and termination_z.connected_endpoint
                and hasattr(termination_z.connected_endpoint, "ip_addresses")
            ):
                termination_z.ip_addresses = termination_z.connected_endpoint.ip_addresses.restrict(
                    request.user, "view"
                )

            return {
                "termination_a": termination_a,
                "termination_z": termination_z,
            }
        elif view_type == "list":
            return {}
        elif view_type == "bulk_edit":
            return {}
        else:
            return {}


class CircuitViewSetRouter(NautobotRouter):
    viewset = CircuitViewSet

    def __init__(self, prefix, basename):
        super().__init__(prefix, basename)


class CircuitTerminationViewset(NautobotViewSet):
    model = CircuitTermination
    queryset = CircuitTermination.objects.all()
    form = forms.CircuitTerminationForm
    lookup_field = "pk"

    def alter_obj_for_edit(self, obj, request, url_args, url_kwargs):
        if "circuit" in url_kwargs:
            obj.circuit = get_object_or_404(Circuit, pk=url_kwargs["circuit"])
        return obj

    def get_return_url(self, request, obj):
        return obj.circuit.get_absolute_url()


class CircuitTerminationViewSetRouter(NautobotRouter):
    viewset = CircuitTerminationViewset
    # Excluding add and edit views here because the add view needs to be re-declared according to a different pattern.
    exclude_views = ["bulk_edit", "bulk_delete", "list", "add", "edit", "import"]

    def __init__(self, prefix, basename):
        super().__init__(prefix, basename)
        self.routes = self.define_routes()

    def define_routes(self):
        return super().define_routes() + [
            Route(
                url=r"^circuits/(?P<circuit>[0-9a-f-]+)/terminations/add/$",
                mapping={
                    "get": "handle_object_edit_get",
                    "post": "handle_object_edit_post",
                },
                name="{basename}_add",
                detail=False,
                initkwargs={"suffix": "Add"},
            ),
            Route(
                url=r"^{prefix}/{lookup}/edit/$",
                mapping={
                    "get": "handle_object_edit_get",
                    "post": "handle_object_edit_post",
                },
                name="{basename}_edit",
                detail=True,
                initkwargs={"suffix": "Edit"},
            ),
        ]


class CircuitSwapTerminations(generic.ObjectEditView):
    """
    Swap the A and Z terminations of a circuit.
    """

    queryset = Circuit.objects.all()

    def get(self, request, pk):
        circuit = get_object_or_404(self.queryset, pk=pk)
        form = ConfirmationForm()

        # Circuit must have at least one termination to swap
        if not circuit.termination_a and not circuit.termination_z:
            messages.error(
                request,
                f"No terminations have been defined for circuit {circuit}.",
            )
            return redirect("circuits:circuit", pk=circuit.pk)

        return render(
            request,
            "circuits/circuit_terminations_swap.html",
            {
                "circuit": circuit,
                "termination_a": circuit.termination_a,
                "termination_z": circuit.termination_z,
                "form": form,
                "panel_class": "default",
                "button_class": "primary",
                "return_url": circuit.get_absolute_url(),
            },
        )

    def post(self, request, pk):
        circuit = get_object_or_404(self.queryset, pk=pk)
        form = ConfirmationForm(request.POST)

        if form.is_valid():

            termination_a = CircuitTermination.objects.filter(
                circuit=circuit, term_side=CircuitTerminationSideChoices.SIDE_A
            ).first()
            termination_z = CircuitTermination.objects.filter(
                circuit=circuit, term_side=CircuitTerminationSideChoices.SIDE_Z
            ).first()

            if termination_a and termination_z:
                # Use a placeholder to avoid an IntegrityError on the (circuit, term_side) unique constraint
                with transaction.atomic():
                    termination_a.term_side = "_"
                    termination_a.save()
                    termination_z.term_side = "A"
                    termination_z.save()
                    termination_a.term_side = "Z"
                    termination_a.save()
            elif termination_a:
                termination_a.term_side = "Z"
                termination_a.save()
            else:
                termination_z.term_side = "A"
                termination_z.save()

            messages.success(request, f"Swapped terminations for circuit {circuit}.")
            return redirect("circuits:circuit", pk=circuit.pk)

        return render(
            request,
            "circuits/circuit_terminations_swap.html",
            {
                "circuit": circuit,
                "termination_a": circuit.termination_a,
                "termination_z": circuit.termination_z,
                "form": form,
                "panel_class": "default",
                "button_class": "primary",
                "return_url": circuit.get_absolute_url(),
            },
        )
