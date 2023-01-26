from itertools import count, groupby
import json

from django.core.serializers import serialize
from django.utils.tree import Node
from taggit.managers import _TaggableManager


def array_to_string(array):
    """
    Generate an efficient, human-friendly string from a set of integers. Intended for use with ArrayField.
    For example:
        [0, 1, 2, 10, 14, 15, 16] => "0-2, 10, 14-16"
    """
    group = (list(x) for _, x in groupby(sorted(array), lambda x, c=count(): next(c) - x))
    return ", ".join("-".join(map(str, (g[0], g[-1])[: len(g)])) for g in group)


def is_taggable(obj):
    """
    Return True if the instance can have Tags assigned to it; False otherwise.
    """
    if hasattr(obj, "tags"):
        if issubclass(obj.tags.__class__, _TaggableManager):
            return True
    return False


def pretty_print_query(query):
    """
    Given a `Q` object, display it in a more human-readable format.

    Args:
        query (Q): Query to display.

    Returns:
        str: Pretty-printed query logic

    Example:
        >>> print(pretty_print_query(Q))
        (
          site__slug='ams01' OR site__slug='bkk01' OR (
            site__slug='can01' AND status__slug='active'
          ) OR (
            site__slug='del01' AND (
              NOT (site__slug='del01' AND status__slug='decommissioning')
            )
          )
        )
    """

    def pretty_str(self, node=None, depth=0):
        """Improvement to default `Node.__str__` with a more human-readable style."""
        template = f"(\n{'  ' * (depth + 1)}"
        if self.negated:
            template += "NOT (%s)"
        else:
            template += "%s"
        template += f"\n{'  ' * depth})"
        children = []

        # If we don't have a node, we are the node!
        if node is None:
            node = self

        # Iterate over children. They will be either a Q object (a Node subclass) or a 2-tuple.
        for child in node.children:
            # Trust that we can stringify the child if it is a Node instance.
            if isinstance(child, Node):
                children.append(pretty_str(child, depth=depth + 1))
            # If a 2-tuple, stringify to key=value
            else:
                key, value = child
                children.append(f"{key}={value!r}")

        return template % (f" {self.connector} ".join(children))

    # Use pretty_str() as the string generator vs. just stringify the `Q` object.
    return pretty_str(query)


def serialize_object(obj, extra=None, exclude=None):
    """
    Return a generic JSON representation of an object using Django's built-in serializer. (This is used for things like
    change logging, not the REST API.) Optionally include a dictionary to supplement the object data. A list of keys
    can be provided to exclude them from the returned dictionary. Private fields (prefaced with an underscore) are
    implicitly excluded.
    """
    json_str = serialize("json", [obj])
    data = json.loads(json_str)[0]["fields"]

    # Include custom_field_data as "custom_fields"
    if hasattr(obj, "_custom_field_data"):
        data["custom_fields"] = data.pop("_custom_field_data")

    # Include any tags. Check for tags cached on the instance; fall back to using the manager.
    if is_taggable(obj):
        tags = getattr(obj, "_tags", []) or obj.tags.all()
        data["tags"] = [tag.name for tag in tags]

    # Append any extra data
    if extra is not None:
        data.update(extra)

    # Copy keys to list to avoid 'dictionary changed size during iteration' exception
    for key in list(data):
        # Private fields shouldn't be logged in the object change
        if isinstance(key, str) and key.startswith("_"):
            data.pop(key)

        # Explicitly excluded keys
        if isinstance(exclude, (list, tuple)) and key in exclude:
            data.pop(key)

    return data


def serialize_object_v2(obj):
    """
    Return a JSON serialized representation of an object using obj's serializer.
    """
    from nautobot.core.api.exceptions import SerializerNotFound
    from nautobot.core.api.utils import get_serializer_for_model

    # Try serializing obj(model instance) using its API Serializer
    try:
        serializer_class = get_serializer_for_model(obj.__class__)
        data = serializer_class(obj, context={"request": None}).data
    except SerializerNotFound:
        # Fall back to generic JSON representation of obj
        data = serialize_object(obj)

    return data
