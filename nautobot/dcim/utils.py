import uuid

from django.contrib.contenttypes.models import ContentType

from nautobot.utilities.utils import hex_to_rgb, lighten_color, rgb_to_hex


def compile_path_node(ct_id, object_id):
    return f"{ct_id}:{object_id}"


def decompile_path_node(representation):
    ct_id, object_id = representation.split(":")
    # The value is stored as a string, but the lookup later uses UUID objects as keys so we convert it now.
    # Note that the content type ID is still an integer because we have no control over that model.
    return int(ct_id), uuid.UUID(object_id)


def object_to_path_node(obj):
    """
    Return a representation of an object suitable for inclusion in a CablePath path. Node representation is in the
    form <ContentType ID>:<Object ID>.
    """
    ct = ContentType.objects.get_for_model(obj)
    return compile_path_node(ct.pk, obj.pk)


def path_node_to_object(representation):
    """
    Given the string representation of a path node, return the corresponding instance.
    """
    ct_id, object_id = decompile_path_node(representation)
    ct = ContentType.objects.get_for_id(ct_id)
    return ct.model_class().objects.get(pk=object_id)


def cable_status_color_css(record):
    """
    Given a record such as an Interface, return the CSS needed to apply appropriate coloring to it.
    """
    if not record.cable:
        return ""
    # The status colors are for use with labels and such, and tend to be quite bright.
    # For this function we want a much milder, mellower color suitable as a row background.
    base_color = record.cable.get_status_color().strip("#")
    lighter_color = rgb_to_hex(*lighten_color(*hex_to_rgb(base_color), 0.75))
    return f"background-color: #{lighter_color}"
