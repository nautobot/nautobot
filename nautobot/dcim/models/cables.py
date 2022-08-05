import logging
from collections import defaultdict
import itertools
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Sum
from django.urls import reverse
from django.utils.functional import classproperty
from django.dispatch import Signal

from nautobot.dcim.choices import CableLengthUnitChoices, CableTypeChoices, CableEndpointSideChoices
from nautobot.dcim.constants import CABLE_TERMINATION_MODELS, COMPATIBLE_TERMINATION_TYPES, NONCONNECTABLE_IFACE_TYPES

from nautobot.dcim.fields import JSONPathField
from nautobot.dcim.utils import (
    decompile_path_node,
    object_to_path_node,
    path_node_to_object,
)
from nautobot.extras.models import Status, StatusModel
from nautobot.extras.utils import extras_features
from nautobot.core.models.generics import BaseModel, PrimaryModel
from nautobot.utilities.fields import ColorField
from nautobot.utilities.utils import to_meters
from .devices import Device
from .device_components import FrontPort, RearPort
from nautobot.utilities.querysets import RestrictedQuerySet
from nautobot.dcim.choices import CableStatusChoices


__all__ = (
    "Cable",
    "CableEndpoint",
    "CablePath",
)

logger = logging.getLogger(__name__)

trace_paths = Signal()

#
# Cables
#


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "statuses",
    "webhooks",
)
class Cable(PrimaryModel, StatusModel):
    """
    A physical connection between two endpoints.
    """
    type = models.CharField(max_length=50, choices=CableTypeChoices, blank=True)
    label = models.CharField(max_length=100, blank=True)
    color = ColorField(blank=True)
    length = models.PositiveSmallIntegerField(blank=True, null=True)
    length_unit = models.CharField(
        max_length=50,
        choices=CableLengthUnitChoices,
        blank=True,
    )
    # Stores the normalized length (in meters) for database ordering
    _abs_length = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)

    csv_headers = [
        "type",
        "status",
        "label",
        "color",
        "length",
        "length_unit",
    ]

    @property
    def termination_a_type(self):
        termination_a = self.endpoints.filter(cable_side=CableEndpointSideChoices.SIDE_A).first()
        a_type = termination_a.termination._meta.model if termination_a else None

        return a_type

    @property
    def termination_b_type(self):
        termination_b = self.endpoints.filter(cable_side=CableEndpointSideChoices.SIDE_B).first()
        b_type = termination_b.termination._meta.model if termination_b else None

        return b_type

    @property
    def a_terminations(self):
        if hasattr(self, '_a_terminations'):
            return self._a_terminations
        # Query self.terminations.all() to leverage cached results
        return [
            endpoint.termination for endpoint in self.endpoints.all() if endpoint.cable_side == CableEndpointSideChoices.SIDE_A
        ]

    @a_terminations.setter
    def a_terminations(self, value):
        self._terminations_modified = True
        self._a_terminations = value

    @property
    def b_terminations(self):
        if hasattr(self, '_b_terminations'):
            return self._b_terminations
        # Query self.terminations.all() to leverage cached results
        return [
            endpoint.termination for endpoint in self.endpoints.all() if endpoint.cable_side == CableEndpointSideChoices.SIDE_B
        ]

    @b_terminations.setter
    def b_terminations(self, value):
        self._terminations_modified = True
        self._b_terminations = value

    def __init__(self, *args, a_terminations=None, b_terminations=None, **kwargs):
        super().__init__(*args, **kwargs)

        # A copy of the PK to be used by __str__ in case the object is deleted
        self._pk = self.pk

        # Cache the original status so we can check later if it's been changed
        self._orig_status = self.status

        self._terminations_modified = False

        # Assign or retrieve A/B terminations
        if a_terminations:
            self.a_terminations = a_terminations
        if b_terminations:
            self.b_terminations = b_terminations

    def __str__(self):
        pk = self.pk or self._pk
        return self.label or f"#{pk}"

    def get_absolute_url(self):
        return reverse("dcim:cable", args=[self.pk])

    @classproperty
    def STATUS_CONNECTED(cls):
        """Return a cached "connected" `Status` object for later reference."""
        if getattr(cls, "__status_connected", None) is None:
            cls.__status_connected = Status.objects.get_for_model(Cable).get(slug="connected")
        return cls.__status_connected

    def clean(self):

        super().clean()

        # Validate length and length_unit
        if self.length is not None and not self.length_unit:
            raise ValidationError("Must specify a unit when setting a cable length")
        elif self.length is None:
            self.length_unit = ''

        if (not self.present_in_database) and (not self.a_terminations or not self.b_terminations):
            raise ValidationError("Must define A and B terminations when creating a new cable.")

        if self._terminations_modified:

            # Check that all termination objects for either end are of the same type
            for terms in (self.a_terminations, self.b_terminations):
                if len(terms) > 1 and not all(isinstance(t, type(terms[0])) for t in terms[1:]):
                    raise ValidationError("Cannot connect different termination types to same end of cable.")

            # Check that termination types are compatible
            if self.a_terminations and self.b_terminations:
                a_type = self.a_terminations[0]._meta.model_name
                b_type = self.b_terminations[0]._meta.model_name
                if b_type not in COMPATIBLE_TERMINATION_TYPES.get(a_type):
                    raise ValidationError(f"Incompatible termination types: {a_type} and {b_type}")

            # Run clean() on any new CableTerminations
            for termination in self.a_terminations:
                CableEndpoint(
                    cable=self,
                    cable_side=CableEndpointSideChoices.SIDE_A,
                    termination=termination
                ).clean()

            for termination in self.b_terminations:
                CableEndpoint(
                    cable=self,
                    cable_side=CableEndpointSideChoices.SIDE_B,
                    termination=termination
                ).clean()

    def save(self, *args, **kwargs):
        is_new = not self.present_in_database

        # Store the given length (if any) in meters for use in database ordering
        if self.length and self.length_unit:
            self._abs_length = to_meters(self.length, self.length_unit)
        else:
            self._abs_length = None

        super().save(*args, **kwargs)

        # Update the private pk used in __str__ in case this is a new object (i.e. just got its pk)
        self._pk = self.pk

        # Retrieve existing A/B terminations for the Cable
        a_terminations = {ct.termination: ct for ct in self.endpoints.filter(cable_side=CableEndpointSideChoices.SIDE_A)}  # TODO(mzb) rename to endpoints
        b_terminations = {ct.termination: ct for ct in self.endpoints.filter(cable_side=CableEndpointSideChoices.SIDE_B)}

        # Delete stale CableTerminations
        if self._terminations_modified:
            for termination, ct in a_terminations.items():
                if termination.pk and termination not in self.a_terminations:
                    ct.delete()
            for termination, ct in b_terminations.items():
                if termination.pk and termination not in self.b_terminations:
                    ct.delete()

        # Save new CableTerminations (if any)
        if self._terminations_modified:
            for termination in self.a_terminations:
                if not termination.present_in_database or termination not in a_terminations:
                    CableEndpoint(cable=self, cable_side=CableEndpointSideChoices.SIDE_A, termination=termination).save()
            for termination in self.b_terminations:
                if not termination.present_in_database or termination not in b_terminations:
                    CableEndpoint(cable=self, cable_side=CableEndpointSideChoices.SIDE_B, termination=termination).save()

        trace_paths.send(Cable, instance=self, created=is_new)

    def to_csv(self):
        return (  # TODO(mzb)
            # "{}.{}".format(self.termination_a_type.app_label, self.termination_a_type.model),
            # self.termination_a_id,
            # "{}.{}".format(self.termination_b_type.app_label, self.termination_b_type.model),
            # self.termination_b_id,
            self.get_type_display(),
            self.get_status_display(),
            self.label,
            self.color,
            self.length,
            self.length_unit,
        )

    def get_compatible_types(self):
        """
        Return all termination types compatible with termination A.
        """
        if self.termination_a is None:
            return
        return COMPATIBLE_TERMINATION_TYPES[self.termination_a._meta.model_name]


class CableEndpoint(BaseModel):
    """
    Cable Ends.
    """
    cable = models.ForeignKey(
        to="dcim.Cable",
        on_delete=models.CASCADE,
        related_name="endpoints",
    )
    cable_side = models.CharField(
        max_length=1,
        choices=CableEndpointSideChoices,
        verbose_name="Side",
    )
    termination_type = models.ForeignKey(
        to=ContentType,
        limit_choices_to=CABLE_TERMINATION_MODELS,
        on_delete=models.PROTECT,
        related_name="+",
    )
    termination_id = models.UUIDField(
        # blank=True,
        # null=True,
    )
    termination = GenericForeignKey(ct_field="termination_type", fk_field="termination_id")

    # Cached associations to enable efficient filtering
    _device = models.ForeignKey(
        to='dcim.Device',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    objects = RestrictedQuerySet.as_manager()

    class Meta:
        ordering = ('cable', 'cable_side')
        unique_together = (('termination_type', 'termination_id'),)  # TODO(mzb) ensure

    def __str__(self):
        return f"Cable {self.cable} to {self.termination}"

    def clean(self):
        super().clean()

        # Validate interface type (if applicable)
        if self.termination_type.model == 'interface' and self.termination.type in NONCONNECTABLE_IFACE_TYPES:
            raise ValidationError({
                'termination': f'Cables cannot be terminated to {self.termination.get_type_display()} interfaces'
            })

        # A CircuitTermination attached to a ProviderNetwork cannot have a Cable
        if self.termination_type.model == 'circuittermination' and self.termination.provider_network is not None:
            raise ValidationError({
                'termination': "Circuit terminations attached to a provider network may not be cabled."
            })

    def save(self, *args, **kwargs):

        # Cache objects associated with the terminating object (for filtering)
        self.cache_related_objects()

        super().save(*args, **kwargs)

        termination_model = self.termination._meta.model
        termination_model.objects.filter(pk=self.termination_id).update(  # TODO(mzb): Caching implications of .update
            cable=self.cable,
            cable_side=self.cable_side,
        )

    def delete(self, *args, **kwargs):

        termination_model = self.termination._meta.model
        termination_model.objects.filter(pk=self.termination_id).update(  # TODO(mzb): Caching implications of .update
            cable=None,
            cable_side=""
        )

        super().delete(*args, **kwargs)

    def cache_related_objects(self):
        """
        Cache objects related to the termination (e.g. device, rack, site) directly on the object to
        enable efficient filtering.
        """
        assert self.termination is not None

        # Device components
        if getattr(self.termination, 'device', None):
            self._device = self.termination.device


@extras_features("graphql")
class CablePath(BaseModel):
    """
    A CablePath instance represents the physical path from an origin to a destination, including all intermediate
    elements in the path. Every instance must specify an `origin`, whereas `destination` may be null (for paths which do
    not terminate on a PathEndpoint).

    `path` contains a list of nodes within the path, each represented by a tuple of (type, ID). The first element in the
    path must be a Cable instance, followed by a pair of pass-through ports. For example, consider the following
    topology:

                     1                              2                              3
        Interface A --- Front Port A | Rear Port A --- Rear Port B | Front Port B --- Interface B

    This path would be expressed as:

    CablePath(
        origin = Interface A
        destination = Interface B
        path = [Cable 1, Front Port A, Rear Port A, Cable 2, Rear Port B, Front Port B, Cable 3]
    )

    `is_active` is set to True only if 1) `destination` is not null, and 2) every Cable within the path has a status of
    "connected".
    """

    path = models.JSONField(
        default=list
    )
    is_active = models.BooleanField(
        default=False
    )
    is_complete = models.BooleanField(
        default=False
    )
    is_split = models.BooleanField(
        default=False
    )
    _nodes = JSONPathField()

    def __str__(self):
        return f"Path #{self.pk}: {len(self.path)} hops"

    def save(self, *args, **kwargs):

        # Save the flattened nodes list
        self._nodes = list(itertools.chain(*self.path))

        super().save(*args, **kwargs)

        # Record a direct reference to this CablePath on its originating object(s)
        origin_model = self.origin_type.model_class()
        origin_ids = [decompile_path_node(node)[1] for node in self.path[0]]
        origin_model.objects.filter(pk__in=origin_ids).update(_path=self.pk)

    @property
    def origin_type(self):
        if self.path:
            ct_id, _ = decompile_path_node(self.path[0][0])
            return ContentType.objects.get_for_id(ct_id)

    @property
    def destination_type(self):
        if self.is_complete:
            ct_id, _ = decompile_path_node(self.path[-1][0])
            return ContentType.objects.get_for_id(ct_id)

    @property
    def path_objects(self):
        """
        Cache and return the complete path as lists of objects, derived from their annotation within the path.
        """
        if not hasattr(self, '_path_objects'):
            self._path_objects = self._get_path()
        return self._path_objects

    @property
    def origins(self):
        """
        Return the list of originating objects.
        """
        if hasattr(self, '_path_objects'):
            return self.path_objects[0]
        return [
            path_node_to_object(node) for node in self.path[0]
        ]

    @property
    def destinations(self):
        """
        Return the list of destination objects, if the path is complete.
        """
        if not self.is_complete:
            return []
        if hasattr(self, '_path_objects'):
            return self.path_objects[-1]
        return [
            path_node_to_object(node) for node in self.path[-1]
        ]

    @property
    def segment_count(self):
        return int(len(self.path) / 3)

    @classmethod
    def from_origin(cls, terminations):
        """
        Create a new CablePath instance as traced from the given termination objects. These can be any object to which a
        Cable or WirelessLink connects (interfaces, console ports, circuit termination, etc.). All terminations must be
        of the same type and must belong to the same parent object.
        """
        from nautobot.circuits.models import CircuitTermination

        # Ensure all originating terminations are attached to the same cable
        if len(terminations) > 1:
            assert all(t.cable == terminations[0].cable for t in terminations[1:])

        path = []
        position_stack = []
        is_complete = False
        is_active = True
        is_split = False

        while terminations:

            # Terminations must all be of the same type
            assert all(isinstance(t, type(terminations[0])) for t in terminations[1:])

            # Check for a split path (e.g. rear port fanning out to multiple front ports with
            # different cables attached)
            if len(set(t.cable for t in terminations)) > 1:
                is_split = True
                break

            # Step 1: Record the near-end termination object(s)
            path.append([
                object_to_path_node(t) for t in terminations
            ])

            # Step 2: Determine the attached link (Cable), if any
            cable = terminations[0].cable
            if cable is None and len(path) == 1:
                # If this is the start of the path and no link exists, return None
                return None
            elif cable is None:
                # Otherwise, halt the trace if no link exists
                break
            assert type(cable) in (Cable,)

            # Step 3: Record the cable and update path status if not "connected"
            path.append([object_to_path_node(cable)])
            if hasattr(cable, 'status') and cable.status != CableStatusChoices.STATUS_CONNECTED:
                is_active = False

            # Step 4: Determine the far-end terminations
            termination_type = ContentType.objects.get_for_model(terminations[0])
            local_cable_endpoints = CableEndpoint.objects.filter(
                termination_type=termination_type,
                termination_id__in=[t.pk for t in terminations]
            )
            # Endpoints must all belong to same side of Cable
            local_cable_side = local_cable_endpoints[0].cable_side
            assert all(ct.cable_side == local_cable_side for ct in local_cable_endpoints[1:])
            remote_cable_endpoints = CableEndpoint.objects.filter(
                cable=cable,
                cable_side='A' if local_cable_side == 'B' else 'B'
            )
            remote_terminations = [ct.termination for ct in remote_cable_endpoints]

            # Step 5: Record the far-end termination object(s)
            path.append([
                object_to_path_node(t) for t in remote_terminations
            ])

            # Step 6: Determine the "next hop" terminations, if applicable
            if isinstance(remote_terminations[0], FrontPort):
                # Follow FrontPorts to their corresponding RearPorts
                rear_ports = RearPort.objects.filter(
                    pk__in=[t.rear_port_id for t in remote_terminations]
                )
                if len(rear_ports) > 1:
                    assert all(rp.positions == 1 for rp in rear_ports)
                elif rear_ports[0].positions > 1:
                    position_stack.append([fp.rear_port_position for fp in remote_terminations])

                terminations = rear_ports

            elif isinstance(remote_terminations[0], RearPort):

                if len(remote_terminations) > 1 or remote_terminations[0].positions == 1:
                    front_ports = FrontPort.objects.filter(
                        rear_port_id__in=[rp.pk for rp in remote_terminations],
                        rear_port_position=1
                    )
                elif position_stack:
                    front_ports = FrontPort.objects.filter(
                        rear_port_id=remote_terminations[0].pk,
                        rear_port_position__in=position_stack.pop()
                    )
                else:
                    # No position indicated: path has split, so we stop at the RearPorts
                    is_split = True
                    break

                terminations = front_ports

            elif isinstance(remote_terminations[0], CircuitTermination):
                # Follow a CircuitTermination to its corresponding CircuitTermination (A to Z or vice versa)
                term_side = remote_terminations[0].term_side
                assert all(ct.term_side == term_side for ct in remote_terminations[1:])
                circuit_termination = CircuitTermination.objects.filter(
                    circuit=remote_terminations[0].circuit,
                    term_side='Z' if term_side == 'A' else 'A'
                ).first()
                if circuit_termination is None:
                    break
                elif circuit_termination.provider_network:
                    # Circuit terminates to a ProviderNetwork
                    path.extend([
                        [object_to_path_node(circuit_termination)],
                        [object_to_path_node(circuit_termination.provider_network)],
                    ])
                    break
                elif circuit_termination.site and not circuit_termination.cable:
                    # Circuit terminates to a Site
                    path.extend([
                        [object_to_path_node(circuit_termination)],
                        [object_to_path_node(circuit_termination.site)],
                    ])
                    break

                terminations = [circuit_termination]

            # Anything else marks the end of the path
            else:
                is_complete = True
                break

        return cls(
            path=path,
            is_complete=is_complete,
            is_active=is_active,
            is_split=is_split
        )

    def retrace(self):
        """
        Retrace the path from the currently-defined originating termination(s)
        """
        _new = self.from_origin(self.origins)
        if _new:
            self.path = _new.path
            self.is_complete = _new.is_complete
            self.is_active = _new.is_active
            self.is_split = _new.is_split
            self.save()
        else:
            self.delete()

    def _get_path(self):
        """
        Return the path as a list of prefetched objects.
        """
        # Compile a list of IDs to prefetch for each type of model in the path
        to_prefetch = defaultdict(list)
        for node in self._nodes:
            ct_id, object_id = decompile_path_node(node)
            to_prefetch[ct_id].append(object_id)

        # Prefetch path objects using one query per model type. Prefetch related devices where appropriate.
        prefetched = {}
        for ct_id, object_ids in to_prefetch.items():
            model_class = ContentType.objects.get_for_id(ct_id).model_class()
            queryset = model_class.objects.filter(pk__in=object_ids)
            if hasattr(model_class, 'device'):
                queryset = queryset.prefetch_related('device')
            prefetched[ct_id] = {
                obj.id: obj for obj in queryset
            }

        # Replicate the path using the prefetched objects.
        path = []
        for step in self.path:
            nodes = []
            for node in step:
                ct_id, object_id = decompile_path_node(node)
                nodes.append(prefetched[ct_id][object_id])
            path.append(nodes)

        return path

    def get_cable_ids(self):
        """
        Return all Cable IDs within the path.
        """
        cable_ct = ContentType.objects.get_for_model(Cable).pk
        cable_ids = []

        for node in self._nodes:
            ct, id = decompile_path_node(node)
            if ct == cable_ct:
                cable_ids.append(id)

        return cable_ids

    def get_total_length(self):
        """
        Return a tuple containing the sum of the length of each cable in the path
        and a flag indicating whether the length is definitive.
        """
        cable_ids = self.get_cable_ids()
        cables = Cable.objects.filter(id__in=cable_ids, _abs_length__isnull=False)
        total_length = cables.aggregate(total=Sum('_abs_length'))['total']
        is_definitive = len(cables) == len(cable_ids)

        return total_length, is_definitive

    def get_split_nodes(self):
        """
        Return all available next segments in a split cable path.
        """
        rearport = path_node_to_object(self._nodes[-1])

        return FrontPort.objects.filter(rear_port=rearport)
