from django.core.urlresolvers import reverse
from django.db import models

from dcim.models import Site, Interface


PORT_SPEED_100M = 100
PORT_SPEED_1G = 1000
PORT_SPEED_10G = 10000
PORT_SPEED_25G = 25000
PORT_SPEED_40G = 40000
PORT_SPEED_50G = 50000
PORT_SPEED_100G = 100000
PORT_SPEED_CHOICES = [
    [PORT_SPEED_100M, '100 Mbps'],
    [PORT_SPEED_1G, '1 Gbps'],
    [PORT_SPEED_10G, '10 Gbps'],
    [PORT_SPEED_25G, '25 Gbps'],
    [PORT_SPEED_40G, '40 Gbps'],
    [PORT_SPEED_50G, '50 Gbps'],
    [PORT_SPEED_100G, '100 Gbps'],
]


class Provider(models.Model):
    """
    A transit provider, IX, or direct peer
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    asn = models.PositiveIntegerField(blank=True, null=True, verbose_name='ASN')
    account = models.CharField(max_length=30, blank=True, verbose_name='Account number')
    portal_url = models.URLField(blank=True, verbose_name='Portal')
    noc_contact = models.TextField(blank=True, verbose_name='NOC Contact')
    admin_contact = models.TextField(blank=True, verbose_name='Admin Contact')
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('circuits:provider', args=[self.slug])


class CircuitType(models.Model):
    """
    A type of circuit
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "{}?type={}".format(reverse('circuits:circuit_list'), self.slug)


class Circuit(models.Model):
    """
    A data circuit from a site to a provider (includes IX connections)
    """
    cid = models.CharField(max_length=50, verbose_name='Circuit ID')
    provider = models.ForeignKey('Provider', related_name='circuits', on_delete=models.PROTECT)
    type = models.ForeignKey('CircuitType', related_name='circuits', on_delete=models.PROTECT)
    site = models.ForeignKey(Site, related_name='circuits', on_delete=models.PROTECT)
    interface = models.OneToOneField(Interface, related_name='circuit', blank=True, null=True)
    install_date = models.DateField(blank=True, null=True, verbose_name='Date installed')
    port_speed = models.PositiveSmallIntegerField(choices=PORT_SPEED_CHOICES, verbose_name='Port speed')
    commit_rate = models.PositiveIntegerField(blank=True, null=True, verbose_name='Commit rate (Mbps)')
    xconnect_id = models.CharField(max_length=50, blank=True, verbose_name='Cross-connect ID')
    pp_info = models.CharField(max_length=100, blank=True, verbose_name='Patch panel/port(s)')
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ['provider', 'cid']
        unique_together = ['provider', 'cid']

    def __unicode__(self):
        return "{0} {1}".format(self.provider, self.cid)

    def get_absolute_url(self):
        return reverse('circuits:circuit', args=[self.pk])
