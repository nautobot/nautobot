from django.core.urlresolvers import reverse
from django.db import models

from dcim.models import Site, Interface


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

    def to_csv(self):
        return ','.join([
            self.name,
            self.slug,
            str(self.asn) if self.asn else '',
            self.account,
            self.portal_url,
        ])


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
    port_speed = models.PositiveIntegerField(verbose_name='Port speed (Kbps)')
    commit_rate = models.PositiveIntegerField(blank=True, null=True, verbose_name='Commit rate (Kbps)')
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

    def to_csv(self):
        return ','.join([
            self.cid,
            self.provider.name,
            self.type.name,
            self.site.name,
            self.install_date.isoformat() if self.install_date else '',
            str(self.port_speed),
            str(self.commit_rate) if self.commit_rate else '',
            self.xconnect_id,
            self.pp_info,
        ])
