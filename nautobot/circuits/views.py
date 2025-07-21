from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import format_html, format_html_join

from nautobot.core.forms import ConfirmationForm
from nautobot.core.templatetags import helpers
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.ui.object_detail import (
    ObjectDetailContent,
    ObjectFieldsPanel,
    ObjectsTablePanel,
)
from nautobot.core.ui.utils import render_component_template
from nautobot.core.views import generic
from nautobot.core.views.utils import get_obj_from_context
from nautobot.core.views.viewsets import NautobotUIViewSet

from . import filters, forms, tables
from .api import serializers
from .choices import CircuitTerminationSideChoices
from .models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork


class CircuitTypeUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.CircuitTypeBulkEditForm
    filterset_class = filters.CircuitTypeFilterSet
    filterset_form_class = forms.CircuitTypeFilterForm
    form_class = forms.CircuitTypeForm
    queryset = CircuitType.objects.all()
    serializer_class = serializers.CircuitTypeSerializer
    table_class = tables.CircuitTypeTable

    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
            ),
            ObjectsTablePanel(
                section=SectionChoices.FULL_WIDTH,
                weight=100,
                table_class=tables.CircuitTable,
                table_filter="circuit_type",
                select_related_fields=["circuit_type", "tenant"],
                prefetch_related_fields=["circuit_terminations__location"],
                exclude_columns=["circuit_type"],
            ),
        ),
    )


class CircuitTerminationObjectFieldsPanel(ObjectFieldsPanel):
    def get_extra_context(self, context):
        return {"termination": context["object"]}

    def render_key(self, key, value, context):
        if key == "connected_endpoint":
            return "IP Addressing"
        return super().render_key(key, value, context)

    def render_value(self, key, value, context):
        instance = get_obj_from_context(context, self.context_object_key)
        location = getattr(instance, "location", None)

        # Cable column is hidden if the location is unset
        if not location and key == "cable":
            return None

        if location and key == "cable":
            return render_component_template("circuits/inc/circuit_termination_cable_fragment.html", context)

        if key == "connected_endpoint":
            ip_addresses = getattr(value, "ip_addresses", None)
            if not ip_addresses or not ip_addresses.exists():
                return helpers.HTML_NONE
            return format_html_join(
                ", ",
                "{} ({})",
                ((helpers.hyperlinked_object(ip), getattr(ip, "vrf", None) or "Global") for ip in ip_addresses.all()),
            )
        return super().render_value(key, value, context)


class CircuitTerminationUIViewSet(NautobotUIViewSet):
    action_buttons = ("import", "export")
    bulk_update_form_class = forms.CircuitTerminationBulkEditForm
    filterset_class = filters.CircuitTerminationFilterSet
    filterset_form_class = forms.CircuitTerminationFilterForm
    form_class = forms.CircuitTerminationForm
    queryset = CircuitTermination.objects.all()
    serializer_class = serializers.CircuitTerminationSerializer
    table_class = tables.CircuitTerminationTable

    object_detail_content = ObjectDetailContent(
        panels=(
            CircuitTerminationObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=[
                    "location",
                    "provider_network",
                    "cloud_network",
                    "cable",
                    "port_speed",
                    "upstream_speed",
                    "connected_endpoint",
                    "xconnect_id",
                    "pp_info",
                    "description",
                ],
                hide_if_unset=[
                    "location",
                    "provider_network",
                    "cloud_network",
                    "port_speed",
                    "upstream_speed",
                ],
                exclude_fields=[
                    "circuit",
                ],
                value_transforms={
                    "port_speed": [helpers.humanize_speed],
                    "upstream_speed": [helpers.humanize_speed],
                },
            ),
        )
    )

    def get_object(self):
        obj = super().get_object()
        if self.action in ["create", "update"] and "circuit" in self.kwargs:
            obj.circuit = get_object_or_404(Circuit, pk=self.kwargs["circuit"])
        return obj

    def get_return_url(self, request, obj=None, default_return_url=None):
        if obj is not None and obj.present_in_database and obj.pk:
            return super().get_return_url(request, obj=obj.circuit, default_return_url=default_return_url)

        return super().get_return_url(request, obj=obj, default_return_url=default_return_url)


class ProviderUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.ProviderBulkEditForm
    filterset_class = filters.ProviderFilterSet
    filterset_form_class = forms.ProviderFilterForm
    form_class = forms.ProviderForm
    queryset = Provider.objects.all()
    serializer_class = serializers.ProviderSerializer
    table_class = tables.ProviderTable
    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
            ),
            ObjectsTablePanel(
                weight=200,
                table_class=tables.CircuitTable,
                table_filter="provider",
                section=SectionChoices.FULL_WIDTH,
                exclude_columns=["provider"],
            ),
        ),
    )


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

    class CircuitTerminationPanel(ObjectFieldsPanel):
        def __init__(self, **kwargs):
            self.side = kwargs.pop("side")
            super().__init__(
                fields=(
                    "location",  # TODO: render location hierarchy
                    "cable",
                    "provider_network",
                    "cloud_network",
                    "port_speed",
                    "upstream_speed",
                    "ip_addresses",
                    "xconnect_id",
                    "pp_info",
                    "description",
                ),
                value_transforms={
                    "port_speed": [helpers.humanize_speed, helpers.placeholder],
                    "upstream_speed": [helpers.humanize_speed],
                },
                hide_if_unset=("location", "provider_network", "cloud_network", "upstream_speed"),
                ignore_nonexistent_fields=True,  # ip_addresses may be undefined
                header_extra_content_template_path="circuits/inc/circuit_termination_header_extra_content.html",
                **kwargs,
            )

        def should_render(self, context):
            return True

        def get_extra_context(self, context):
            return {"termination": context[self.context_object_key], "side": self.side}

        def get_data(self, context):
            """
            Extend the panel data to include custom relationships on the termination.

            This is done for feature parity with the existing UI, and is not a pattern we *generally* should emulate.
            """
            data = super().get_data(context)
            termination = context["termination"]
            if termination is not None:
                for side, relationships in termination.get_relationships_with_related_objects(
                    include_hidden=False
                ).items():
                    for relationship, value in relationships.items():
                        key = (relationship, side)
                        data[key] = value

            return data

        def render_key(self, key, value, context):
            """
            Extend the panel rendering to render custom relationship information.

            This is done for feature parity with the existing UI, and is not a pattern we *generally* should emulate.
            """
            if isinstance(key, tuple):
                # Copied from _ObjectRelationshipsPanel.render_key()
                relationship, side = key
                return format_html(
                    '<span title="{} ({})">{}</span>',
                    relationship.label,
                    relationship.key,
                    helpers.bettertitle(relationship.get_label(side)),
                )
            if key == "ip_addresses":
                return "IP Addressing"
            return super().render_key(key, value, context)

        def render_value(self, key, value, context):
            """
            Add custom rendering of connected cables.

            TODO: this might make sense to move into the base class to handle Cable objects in general?
            """
            if key == "cable":
                if not context["termination"].location:
                    return ""
                return render_component_template("circuits/inc/circuit_termination_cable_fragment.html", context)
            return super().render_value(key, value, context)

        def queryset_list_url_filter(self, key, value, context):
            """
            Extend the panel rendering to render custom relationship information.

            This is done for feature parity with the existing UI, and is not a pattern we *generally* should emulate.
            """
            if isinstance(key, tuple):
                # Copied from _ObjectRelationshipsPanel.queryset_list_url_filter()
                relationship, side = key
                termination = context["termination"]
                return f"cr_{relationship.key}__{side}={termination.pk}"
            return super().queryset_list_url_filter(key, value, context)

    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
                exclude_fields=["comments", "circuit_termination_a", "circuit_termination_z"],
                value_transforms={"commit_rate": [helpers.humanize_speed, helpers.placeholder]},
            ),
            CircuitTerminationPanel(
                label="Termination - A Side",
                section=SectionChoices.RIGHT_HALF,
                weight=100,
                context_object_key="circuit_termination_a",
                side=CircuitTerminationSideChoices.SIDE_A,
            ),
            CircuitTerminationPanel(
                label="Termination - Z Side",
                section=SectionChoices.RIGHT_HALF,
                weight=200,
                context_object_key="circuit_termination_z",
                side=CircuitTerminationSideChoices.SIDE_Z,
            ),
        ),
    )

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

    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
            ),
            ObjectsTablePanel(
                weight=200,
                section=SectionChoices.FULL_WIDTH,
                table_class=tables.CircuitTable,
                table_filter=["circuit_termination_a__provider_network", "circuit_termination_z__provider_network"],
                prefetch_related_fields=["circuit_terminations__location"],
                select_related_fields=["circuit_type", "tenant"],
                exclude_columns=["provider_network", "circuit_termination_a", "circuit_termination_z"],
                related_field_name="provider_network",
                add_button_route=None,
            ),
        )
    )


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
