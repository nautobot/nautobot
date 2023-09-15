from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import is_safe_url
from django_tables2 import RequestConfig


from nautobot.core.forms import ConfirmationForm
from nautobot.core.models.querysets import count_related
from nautobot.core.views import generic, mixins as view_mixins
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.core.views.viewsets import NautobotUIViewSet


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
    filterset_class = filters.CircuitTypeFilterSet
    form_class = forms.CircuitTypeForm
    queryset = CircuitType.objects.annotate(circuit_count=count_related(Circuit, "circuit_type"))
    serializer_class = serializers.CircuitTypeSerializer
    table_class = tables.CircuitTypeTable

    def get_extra_context(self, request, instance):
        # Circuits
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            circuits = (
                Circuit.objects.restrict(request.user, "view")
                .filter(circuit_type=instance)
                .select_related("circuit_type", "tenant")
                .prefetch_related("circuit_terminations__location")
            )

            circuits_table = tables.CircuitTable(circuits)
            circuits_table.columns.hide("circuit_type")

            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(circuits_table)
            context["circuits_table"] = circuits_table
        return context


class CircuitTerminationUIViewSet(
    view_mixins.ObjectDetailViewMixin,
    view_mixins.ObjectListViewMixin,
    view_mixins.ObjectEditViewMixin,
    view_mixins.ObjectDestroyViewMixin,
    view_mixins.ObjectBulkDestroyViewMixin,
    view_mixins.ObjectBulkCreateViewMixin,
    view_mixins.ObjectChangeLogViewMixin,
    view_mixins.ObjectNotesViewMixin,
):
    action_buttons = ("import", "export")
    filterset_class = filters.CircuitTerminationFilterSet
    form_class = forms.CircuitTerminationForm
    queryset = CircuitTermination.objects.all()
    serializer_class = serializers.CircuitTerminationSerializer
    table_class = tables.CircuitTerminationTable

    def get_object(self):
        obj = super().get_object()
        if self.action in ["create", "update"] and "circuit" in self.kwargs:
            obj.circuit = get_object_or_404(Circuit, pk=self.kwargs["circuit"])
        return obj

    def get_return_url(self, request, obj=None):
        # First, see if `return_url` was specified as a query parameter or form data. Use this URL only if it's
        # considered safe.
        query_param = request.GET.get("return_url") or request.POST.get("return_url")
        if query_param and is_safe_url(url=query_param, allowed_hosts=request.get_host()):
            return query_param

        if obj is not None and obj.present_in_database and obj.pk:
            return obj.circuit.get_absolute_url()

        return super().get_return_url(request, obj=obj)


class ProviderUIViewSet(NautobotUIViewSet):
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
            circuits = (
                Circuit.objects.restrict(request.user, "view")
                .filter(provider=instance)
                .select_related("circuit_type", "tenant")
                .prefetch_related("circuit_terminations__location")
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
    bulk_update_form_class = forms.CircuitBulkEditForm
    filterset_class = filters.CircuitFilterSet
    filterset_form_class = forms.CircuitFilterForm
    form_class = forms.CircuitForm
    # v2 TODO(jathan): Replace prefetch_related with select_related
    prefetch_related = ["provider", "circuit_type", "tenant", "circuit_termination_a", "circuit_termination_z"]
    queryset = Circuit.objects.all()
    serializer_class = serializers.CircuitSerializer
    table_class = tables.CircuitTable
    # NOTE: This is how `NautobotUIViewSet` would define use_new_ui attr
    # use_new_ui = ["list", "retrieve"]

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            # A-side termination
            circuit_termination_a = (
                CircuitTermination.objects.restrict(request.user, "view")
                .select_related("location")
                .filter(circuit=instance, term_side=CircuitTerminationSideChoices.SIDE_A)
                .first()
            )
            if (
                circuit_termination_a
                and circuit_termination_a.connected_endpoint
                and hasattr(circuit_termination_a.connected_endpoint, "ip_addresses")
            ):
                circuit_termination_a.ip_addresses = circuit_termination_a.connected_endpoint.ip_addresses.restrict(
                    request.user, "view"
                )

            # Z-side termination
            circuit_termination_z = (
                CircuitTermination.objects.restrict(request.user, "view")
                .select_related("location")
                .filter(circuit=instance, term_side=CircuitTerminationSideChoices.SIDE_Z)
                .first()
            )
            if (
                circuit_termination_z
                and circuit_termination_z.connected_endpoint
                and hasattr(circuit_termination_z.connected_endpoint, "ip_addresses")
            ):
                circuit_termination_z.ip_addresses = circuit_termination_z.connected_endpoint.ip_addresses.restrict(
                    request.user, "view"
                )

            context["circuit_termination_a"] = circuit_termination_a
            context["circuit_termination_z"] = circuit_termination_z
        return context


class ProviderNetworkUIViewSet(NautobotUIViewSet):
    model = ProviderNetwork
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
            circuits = (
                Circuit.objects.restrict(request.user, "view")
                .filter(
                    Q(circuit_termination_a__provider_network=instance.pk)
                    | Q(circuit_termination_z__provider_network=instance.pk)
                )
                .select_related("circuit_type", "tenant")
                .prefetch_related("circuit_terminations__location")
            )

            circuits_table = tables.CircuitTable(circuits)
            circuits_table.columns.hide("circuit_termination_a")
            circuits_table.columns.hide("circuit_termination_z")

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
        if not circuit.circuit_termination_a and not circuit.circuit_termination_z:
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
                "circuit_termination_a": circuit.circuit_termination_a,
                "circuit_termination_z": circuit.circuit_termination_z,
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
            circuit_termination_a = CircuitTermination.objects.filter(
                circuit=circuit, term_side=CircuitTerminationSideChoices.SIDE_A
            ).first()
            circuit_termination_z = CircuitTermination.objects.filter(
                circuit=circuit, term_side=CircuitTerminationSideChoices.SIDE_Z
            ).first()

            if circuit_termination_a and circuit_termination_z:
                # Use a placeholder to avoid an IntegrityError on the (circuit, term_side) unique constraint
                with transaction.atomic():
                    circuit_termination_a.term_side = "_"
                    circuit_termination_a.save()
                    circuit_termination_z.term_side = "A"
                    circuit_termination_z.save()
                    circuit_termination_a.term_side = "Z"
                    circuit_termination_a.save()
            elif circuit_termination_a:
                circuit_termination_a.term_side = "Z"
                circuit_termination_a.save()
            else:
                circuit_termination_z.term_side = "A"
                circuit_termination_z.save()

            messages.success(request, f"Swapped terminations for circuit {circuit}.")
            return redirect("circuits:circuit", pk=circuit.pk)

        return render(
            request,
            "circuits/circuit_terminations_swap.html",
            {
                "circuit": circuit,
                "circuit_termination_a": circuit.circuit_termination_a,
                "circuit_termination_z": circuit.circuit_termination_z,
                "form": form,
                "panel_class": "default",
                "button_class": "primary",
                "return_url": circuit.get_absolute_url(),
            },
        )
