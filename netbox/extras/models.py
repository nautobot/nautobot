from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.http import HttpResponse
from django.template import Template, Context


from dcim.models import Site


GRAPH_TYPE_INTERFACE = 100
GRAPH_TYPE_PROVIDER = 200
GRAPH_TYPE_SITE = 300
GRAPH_TYPE_CHOICES = (
    (GRAPH_TYPE_INTERFACE, 'Interface'),
    (GRAPH_TYPE_PROVIDER, 'Provider'),
    (GRAPH_TYPE_SITE, 'Site'),
)

EXPORTTEMPLATE_MODELS = [
    'site', 'rack', 'device', 'consoleport', 'powerport', 'interfaceconnection',
    'aggregate', 'prefix', 'ipaddress', 'vlan',
    'provider', 'circuit'
]


class Graph(models.Model):
    type = models.PositiveSmallIntegerField(choices=GRAPH_TYPE_CHOICES)
    weight = models.PositiveSmallIntegerField(default=1000)
    name = models.CharField(max_length=100, verbose_name='Name')
    source = models.CharField(max_length=500, verbose_name='Source URL')
    link = models.URLField(verbose_name='Link URL', blank=True)

    class Meta:
        ordering = ['type', 'weight', 'name']

    def __unicode__(self):
        return self.name

    def embed_url(self, obj):
        template = Template(self.source)
        return template.render(Context({'obj': obj}))


class ExportTemplate(models.Model):
    content_type = models.ForeignKey(ContentType, limit_choices_to={'model__in': EXPORTTEMPLATE_MODELS})
    name = models.CharField(max_length=200)
    template_code = models.TextField()
    mime_type = models.CharField(max_length=15, blank=True)
    file_extension = models.CharField(max_length=15, blank=True)

    class Meta:
        ordering = ['content_type', 'name']
        unique_together = [
            ['content_type', 'name']
        ]

    def __unicode__(self):
        return "{}: {}".format(self.content_type, self.name)

    def to_response(self, context_dict, filename):
        """
        Render the template to an HTTP response, delivered as a named file attachment
        """
        template = Template(self.template_code)
        mime_type = 'text/plain' if not self.mime_type else self.mime_type
        response = HttpResponse(
            template.render(Context(context_dict)),
            content_type=mime_type
        )
        if self.file_extension:
            filename += '.{}'.format(self.file_extension)
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        return response


class TopologyMap(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    site = models.ForeignKey(Site, related_name='topology_maps', blank=True, null=True)
    device_patterns = models.TextField(help_text="Identify devices to include in the diagram using regular expressions,"
                                                 "one per line. Each line will result in a new tier of the drawing. "
                                                 "Separate multiple regexes on a line using commas. Devices will be "
                                                 "rendered in the order they are defined.")
    description = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name

    @property
    def device_sets(self):
        if not self.device_patterns:
            return None
        return [line.strip() for line in self.device_patterns.split('\n')]
