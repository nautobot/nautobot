from netaddr import IPNetwork, cidr_merge

from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from dcim.models import Interface
from .fields import IPNetworkField, IPAddressField


AF_CHOICES = (
    (4, 'IPv4'),
    (6, 'IPv6'),
)

PREFIX_STATUS_CHOICES = (
    (0, 'Container'),
    (1, 'Active'),
    (2, 'Reserved'),
    (3, 'Deprecated')
)

VLAN_STATUS_CHOICES = (
    (1, 'Active'),
    (2, 'Reserved'),
    (3, 'Deprecated')
)

STATUS_CHOICE_CLASSES = {
    0: 'default',
    1: 'primary',
    2: 'info',
    3: 'danger',
}


class VRF(models.Model):
    """
    A discrete layer three forwarding domain (e.g. a routing table)
    """
    name = models.CharField(max_length=50)
    rd = models.CharField(max_length=21, unique=True, verbose_name='Route distinguisher')
    description = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'VRF'
        verbose_name_plural = 'VRFs'

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('ipam:vrf', args=[self.pk])


class RIR(models.Model):
    """
    A regional Internet registry (e.g. ARIN) or governing standard (e.g. RFC 1918)
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'RIR'
        verbose_name_plural = 'RIRs'

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "{}?rir={}".format(reverse('ipam:aggregate_list'), self.slug)


class Aggregate(models.Model):
    """
    A top-level IPv4 or IPv6 prefix
    """
    family = models.PositiveSmallIntegerField(choices=AF_CHOICES)
    prefix = IPNetworkField()
    rir = models.ForeignKey('RIR', related_name='aggregates', on_delete=models.PROTECT, verbose_name='RIR')
    date_added = models.DateField(blank=True, null=True)
    description = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['family', 'prefix']

    def __unicode__(self):
        return str(self.prefix)

    def get_absolute_url(self):
        return reverse('ipam:aggregate', args=[self.pk])

    def clean(self):

        if self.prefix:

            # Clear host bits from prefix
            self.prefix = self.prefix.cidr

            # Ensure that the aggregate being added is not covered by an existing aggregate
            covering_aggregates = Aggregate.objects.filter(prefix__net_contains_or_equals=str(self.prefix))
            if self.pk:
                covering_aggregates = covering_aggregates.exclude(pk=self.pk)
            if covering_aggregates:
                raise ValidationError("{} is already covered by an existing aggregate ({})"
                                      .format(self.prefix, covering_aggregates[0]))

    def save(self, *args, **kwargs):
        if self.prefix:
            # Infer address family from IPNetwork object
            self.family = self.prefix.version
        super(Aggregate, self).save(*args, **kwargs)

    def get_utilization(self):
        """
        Determine the utilization rate of the aggregate prefix and return it as a percentage.
        """
        child_prefixes = Prefix.objects.filter(prefix__net_contained_or_equal=str(self.prefix))
        # Remove overlapping prefixes from list of children
        networks = cidr_merge([c.prefix for c in child_prefixes])
        children_size = float(0)
        for p in networks:
            children_size += p.size
        return int(children_size / self.prefix.size * 100)


class Role(models.Model):
    """
    The role of an address resource (e.g. customer, infrastructure, mgmt, etc.)
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    weight = models.PositiveSmallIntegerField(default=1000)

    class Meta:
        ordering = ['weight', 'name']

    def __unicode__(self):
        return self.name

    @property
    def count_prefixes(self):
        return self.prefixes.count()

    @property
    def count_vlans(self):
        return self.vlans.count()


class PrefixQuerySet(models.QuerySet):

    def annotate_depth(self, limit=None):
        """
        Iterate through a QuerySet of Prefixes and annotate the hierarchical level of each. While it would be preferable
        to do this using .extra() on the QuerySet to count the unique parents of each prefix, that approach introduces
        performance issues at scale.

        Because we're adding a non-field attribute to the model, annotation must be made *after* any QuerySet
        modifications.
        """
        queryset = self
        stack = []
        for p in queryset:
            try:
                prev_p = stack[-1]
            except IndexError:
                prev_p = None
            if prev_p is not None:
                while (p.prefix not in prev_p.prefix) or p.prefix == prev_p.prefix:
                    stack.pop()
                    try:
                        prev_p = stack[-1]
                    except IndexError:
                        prev_p = None
                        break
            if prev_p is not None:
                prev_p.has_children = True
            stack.append(p)
            p.depth = len(stack) - 1
        if limit is None:
            return queryset
        return filter(lambda p: p.depth <= limit, queryset)


class Prefix(models.Model):
    """
    An IPv4 or IPv6 prefix, including mask length
    """
    family = models.PositiveSmallIntegerField(choices=AF_CHOICES, editable=False)
    prefix = IPNetworkField()
    site = models.ForeignKey('dcim.Site', related_name='prefixes', on_delete=models.PROTECT, blank=True, null=True)
    vrf = models.ForeignKey('VRF', related_name='prefixes', on_delete=models.PROTECT, blank=True, null=True, verbose_name='VRF')
    vlan = models.ForeignKey('VLAN', related_name='prefixes', on_delete=models.PROTECT, blank=True, null=True, verbose_name='VLAN')
    status = models.PositiveSmallIntegerField('Status', choices=PREFIX_STATUS_CHOICES, default=1)
    role = models.ForeignKey('Role', related_name='prefixes', on_delete=models.SET_NULL, blank=True, null=True)
    description = models.CharField(max_length=100, blank=True)

    objects = PrefixQuerySet.as_manager()

    class Meta:
        ordering = ['family', 'prefix']
        verbose_name_plural = 'prefixes'

    def __unicode__(self):
        return str(self.prefix)

    def get_absolute_url(self):
        return reverse('ipam:prefix', args=[self.pk])

    def save(self, *args, **kwargs):
        if self.prefix:
            # Clear host bits from prefix
            self.prefix = self.prefix.cidr
            # Infer address family from IPNetwork object
            self.family = self.prefix.version
        super(Prefix, self).save(*args, **kwargs)

    @property
    def new_subnet(self):
        if self.family == 4:
            if self.prefix.prefixlen <= 30:
                return IPNetwork('{}/{}'.format(self.prefix.network, self.prefix.prefixlen + 1))
            return None
        if self.family == 6:
            if self.prefix.prefixlen <= 126:
                return IPNetwork('{}/{}'.format(self.prefix.network, self.prefix.prefixlen + 1))
            return None

    def get_status_class(self):
        return STATUS_CHOICE_CLASSES[self.status]


class IPAddress(models.Model):
    """
    An IPv4 or IPv6 address
    """
    family = models.PositiveSmallIntegerField(choices=AF_CHOICES, editable=False)
    address = IPAddressField()
    vrf = models.ForeignKey('VRF', related_name='ip_addresses', on_delete=models.PROTECT, blank=True, null=True, verbose_name='VRF')
    interface = models.ForeignKey(Interface, related_name='ip_addresses', on_delete=models.CASCADE, blank=True, null=True)
    nat_inside = models.OneToOneField('self', related_name='nat_outside', on_delete=models.SET_NULL, blank=True, null=True, verbose_name='NAT IP (inside)')
    description = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['family', 'address']
        verbose_name = 'IP address'
        verbose_name_plural = 'IP addresses'

    def __unicode__(self):
        return str(self.address)

    def get_absolute_url(self):
        return reverse('ipam:ipaddress', args=[self.pk])

    def save(self, *args, **kwargs):
        if self.address:
            # Infer address family from IPAddress object
            self.family = self.address.version
        super(IPAddress, self).save(*args, **kwargs)

    @property
    def device(self):
        if self.interface:
            return self.interface.device
        return None


class VLAN(models.Model):
    """
    A VLAN within a site
    """
    site = models.ForeignKey('dcim.Site', related_name='vlans', on_delete=models.PROTECT)
    vid = models.PositiveSmallIntegerField(verbose_name='ID', validators=[
        MinValueValidator(1),
        MaxValueValidator(4094)
    ])
    name = models.CharField(max_length=30)
    status = models.PositiveSmallIntegerField('Status', choices=VLAN_STATUS_CHOICES, default=1)
    role = models.ForeignKey('Role', related_name='vlans', on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        ordering = ['site', 'vid']
        verbose_name = 'VLAN'
        verbose_name_plural = 'VLANs'

    def __unicode__(self):
        return "{0} ({1})".format(self.vid, self.name)

    def get_absolute_url(self):
        return reverse('ipam:vlan', args=[self.pk])

    def get_status_class(self):
        return STATUS_CHOICE_CLASSES[self.status]
