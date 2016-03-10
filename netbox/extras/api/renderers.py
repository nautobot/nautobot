import json
from rest_framework import renderers

# IP address family designations
AF = {
    4: 'A',
    6: 'AAAA',
}


class BINDZoneRenderer(renderers.BaseRenderer):
    """
    Generate a BIND zone file from a list of DNS records.
        Required fields: `name`, `primary_ip`
    """
    media_type = 'text/plain'
    format = 'bind-zone'

    def render(self, data, media_type=None, renderer_context=None):
        records = []
        for record in data:
            if record.get('name') and record.get('primary_ip'):
                try:
                    records.append("{} IN {} {}".format(
                        record['name'],
                        AF[record['primary_ip']['family']],
                        record['primary_ip']['address'].split('/')[0],
                    ))
                except KeyError:
                    pass
        return '\n'.join(records)


class FlatJSONRenderer(renderers.BaseRenderer):
    """
    Flattens a nested JSON reponse.
    """
    format = 'json_flat'
    media_type = 'application/json'

    def render(self, data, media_type=None, renderer_context=None):

        def flatten(entry):
            for key, val in entry.iteritems():
                if isinstance(val, dict):
                    for child_key, child_val in flatten(val):
                        yield "{}_{}".format(key, child_key), child_val
                else:
                    yield key, val

        return json.dumps([dict(flatten(i)) for i in data])
