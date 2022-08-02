from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django_tables2 import RequestConfig


from nautobot.core.views import generic
from nautobot.utilities.drf_views import NautobotDRFViewSet
from nautobot.utilities.forms import ConfirmationForm
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.utilities.utils import count_related

from . import filters, forms, tables
from .api import nested_serializers
from .choices import CircuitTerminationSideChoices
from .models import Circuit, CircuitType, CircuitTermination, Provider, ProviderNetwork


class CircuitTypeDRFViewSet(NautobotDRFViewSet):
    model = CircuitType
    serializer_class = nested_serializers.NestedCircuitTypeSerializer
    queryset = CircuitType.objects.annotate(circuit_count=count_related(Circuit, "type"))
    table_class = tables.CircuitTypeTable
    form_class = forms.CircuitTypeForm
    filterset_class = filters.CircuitTypeFilterSet
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


class CircuitTerminationDRFViewset(NautobotDRFViewSet):
    model = CircuitTermination
    queryset = CircuitTermination.objects.all()
    serializer_class = nested_serializers.NestedCircuitTerminationSerializer
    form_class = forms.CircuitTerminationForm
    lookup_field = "pk"

    def alter_obj_for_edit(self, obj, request, url_args, url_kwargs):
        if "circuit" in url_kwargs:
            obj.circuit = get_object_or_404(Circuit, pk=url_kwargs["circuit"])
        return obj

    def get_return_url(self, request, obj):
        return obj.circuit.get_absolute_url()


class ProviderDRFViewSet(NautobotDRFViewSet):
    model = Provider
    serializer_class = nested_serializers.NestedProviderSerializer
    queryset = Provider.objects.annotate(count_circuits=count_related(Circuit, "provider"))
    table_class = tables.ProviderTable
    form_class = forms.ProviderForm
    filterset_form_class = forms.ProviderFilterForm
    filterset_class = filters.ProviderFilterSet
    import_form = forms.ProviderCSVForm
    bulk_edit_form_class = forms.ProviderBulkEditForm
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
    table_class = tables.CircuitTable
    form_class = forms.CircuitForm
    filterset_class = filters.CircuitFilterSet
    filterset_form_class = forms.CircuitFilterForm
    import_form = forms.CircuitCSVForm
    bulk_edit_form_class = forms.CircuitBulkEditForm
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
    table_class = tables.ProviderNetworkTable
    form_class = forms.ProviderNetworkForm
    filterset_form_class = forms.ProviderNetworkFilterForm
    filterset_class = filters.ProviderNetworkFilterSet
    import_form = forms.ProviderNetworkCSVForm
    bulk_edit_form_class = forms.ProviderNetworkBulkEditForm
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
