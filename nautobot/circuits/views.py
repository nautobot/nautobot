from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django_tables2 import RequestConfig


from nautobot.core.views import generic, mixins as view_mixins
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.utilities.forms import ConfirmationForm
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.utilities.utils import count_related


from . import filters, forms, tables
from .api import serializers
from .choices import CircuitTerminationSideChoices
from .models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork


class CircuitTypeUIViewSet(
    view_mixins.ObjectDetailViewMixin,
    view_mixins.ObjectListViewMixin,
    view_mixins.ObjectEditViewMixin,
    view_mixins.ObjectDestroyViewMixin,
    view_mixins.ObjectBulkDestroyViewMixin,
    view_mixins.ObjectBulkCreateViewMixin,
    view_mixins.ObjectChangeLogViewMixin,
    view_mixins.ObjectNotesViewMixin,
):
    bulk_create_form_class = forms.CircuitTypeCSVForm
    filterset_class = filters.CircuitTypeFilterSet
    form_class = forms.CircuitTypeForm
    queryset = CircuitType.objects.annotate(circuit_count=count_related(Circuit, "type"))
    serializer_class = serializers.CircuitTypeSerializer
    table_class = tables.CircuitTypeTable

    def get_extra_context(self, request, instance):
        # Circuits
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            # v2 TODO(jathan): Replace prefetch_related with select_related
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
            context["circuits_table"] = circuits_table
        return context


class CircuitTerminationUIViewSet(
    view_mixins.ObjectDetailViewMixin,
    view_mixins.ObjectEditViewMixin,
    view_mixins.ObjectDestroyViewMixin,
    view_mixins.ObjectChangeLogViewMixin,
    view_mixins.ObjectNotesViewMixin,
):
    form_class = forms.CircuitTerminationForm
    lookup_field = "pk"
    queryset = CircuitTermination.objects.all()
    serializer_class = serializers.CircuitTerminationSerializer

    def get_object(self):
        obj = super().get_object()
        if self.action in ["create", "update"] and "circuit" in self.kwargs:
            obj.circuit = get_object_or_404(Circuit, pk=self.kwargs["circuit"])
        return obj

    def get_return_url(self, request, obj):
        return obj.circuit.get_absolute_url()


class ProviderUIViewSet(NautobotUIViewSet):
    bulk_create_form_class = forms.ProviderCSVForm
    bulk_update_form_class = forms.ProviderBulkEditForm
    filterset_class = filters.ProviderFilterSet
    filterset_form_class = forms.ProviderFilterForm
    form_class = forms.ProviderForm
    queryset = Provider.objects.annotate(count_circuits=count_related(Circuit, "provider"))
    serializer_class = serializers.ProviderSerializer
    table_class = tables.ProviderTable

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            # v2 TODO(jathan): Replace prefetch_related with select_related
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

            context["circuits_table"] = circuits_table
        return context


class CircuitUIViewSet(NautobotUIViewSet):
    bulk_create_form_class = forms.CircuitCSVForm
    bulk_update_form_class = forms.CircuitBulkEditForm
    filterset_class = filters.CircuitFilterSet
    filterset_form_class = forms.CircuitFilterForm
    form_class = forms.CircuitForm
    lookup_field = "pk"
    # v2 TODO(jathan): Replace prefetch_related with select_related
    prefetch_related = ["provider", "type", "tenant", "termination_a", "termination_z"]
    queryset = Circuit.objects.all()
    serializer_class = serializers.CircuitSerializer
    table_class = tables.CircuitTable

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            # A-side termination
            # v2 TODO(jathan): Replace prefetch_related with select_related
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
            # v2 TODO(jathan): Replace prefetch_related with select_related
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

            context["termination_a"] = termination_a
            context["termination_z"] = termination_z
        return context


class ProviderNetworkUIViewSet(NautobotUIViewSet):
    model = ProviderNetwork
    bulk_create_form_class = forms.ProviderNetworkCSVForm
    bulk_update_form_class = forms.ProviderNetworkBulkEditForm
    filterset_class = filters.ProviderNetworkFilterSet
    filterset_form_class = forms.ProviderNetworkFilterForm
    form_class = forms.ProviderNetworkForm
    queryset = ProviderNetwork.objects.all()
    serializer_class = serializers.ProviderNetworkSerializer
    table_class = tables.ProviderNetworkTable

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            # v2 TODO(jathan): Replace prefetch_related with select_related
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

            context["circuits_table"] = circuits_table
        return context


class CircuitSwapTerminations(generic.ObjectEditView):
    """
    Swap the A and Z terminations of a circuit.
    """

    queryset = Circuit.objects.all()

    def get(self, request, *args, **kwargs):
        circuit = get_object_or_404(self.queryset, pk=kwargs["pk"])
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

    def post(self, request, *args, **kwargs):
        circuit = get_object_or_404(self.queryset, pk=kwargs["pk"])
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
