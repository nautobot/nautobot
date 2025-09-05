from itertools import count, groupby
import json
import unicodedata
from urllib.parse import quote_plus, unquote_plus

from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from django.core.serializers import serialize
from django.utils.tree import Node
import emoji
from slugify import slugify

from nautobot.core import constants
from nautobot.core.utils.data import is_uuid


def array_to_string(array):
    """
    Generate an efficient, human-friendly string from a set of integers. Intended for use with ArrayField.
    For example:
        [0, 1, 2, 10, 14, 15, 16] => "0-2, 10, 14-16"
    """
    group = (list(x) for _, x in groupby(sorted(array), lambda x, c=count(): next(c) - x))
    return ", ".join("-".join(map(str, (g[0], g[-1])[: len(g)])) for g in group)


def get_all_concrete_models(base_class):
    """Get a list of all non-abstract models that inherit from the given base_class."""
    models = []
    for appconfig in apps.get_app_configs():
        for model in appconfig.get_models():
            if issubclass(model, base_class) and not model._meta.abstract:
                models.append(model)
    return sorted(models, key=lambda model: (model._meta.app_label, model._meta.model_name))


def is_taggable(obj):
    """
    Return True if the instance can have Tags assigned to it; False otherwise.
    """
    from nautobot.core.models.managers import TagsManager

    return hasattr(obj, "tags") and isinstance(obj.tags, TagsManager)


def pretty_print_query(query):
    """
    Given a `Q` object, display it in a more human-readable format.

    Args:
        query (Q): Query to display.

    Returns:
        (str): Pretty-printed query logic

    Example:
        >>> print(pretty_print_query(Q))
        (
          location__name='Campus-01' OR location__name='Campus-02' OR (
            location__name='Room-01' AND status__name='Active'
          ) OR (
            location__name='Building-01' AND (
              NOT (location__name='Building-01' AND status__name='Decommissioning')
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
        # Note that when upgrading from Nautobot 1.x to 2.0, this method may be called during data migrations,
        # specifically ipam_0022 and dcim_0034, to create ObjectChange records.
        # This can be problematic (see issue #6952) as the Tag records in the DB still have `created` as a `DateField`,
        # but the 2.x code expects this to be a `DateTimeField` (as it will be after the upgrade completes in full).
        # We "cleverly" bypass that issue by using `.only("name")` since that's the only actual Tag field we need here.
        tags = getattr(obj, "_tags", []) or obj.tags.only("name")
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
        data = serializer_class(obj, context={"request": None, "depth": 1}).data
    except SerializerNotFound:
        # Fall back to generic JSON representation of obj
        data = serialize_object(obj)

    return data


def find_models_with_matching_fields(app_models, field_names=None, field_attributes=None, additional_constraints=None):
    """
    Find all models that have fields with the specified names and satisfy the additional constraints,
    and return them grouped by app.

    Args:
        app_models (list[BaseModel]): A list of model classes to search through.
        field_names (list[str]): A list of names of fields that must be present in order for the model to be considered
        field_attributes (dict): Optional dictionary of attributes to filter the fields by.
        additional_constraints (dict): Optional dictionary of `{field: value}` to further filter the models by.

    Return:
        (dict): A dictionary where the keys are app labels and the values are sets of model names.
    """
    registry_items = {}
    field_names = field_names or []
    field_attributes = field_attributes or {}
    additional_constraints = additional_constraints or {}
    for model_class in app_models:
        app_label, model_name = model_class._meta.label_lower.split(".")
        valid_model = True
        for field_name in field_names:
            try:
                field = model_class._meta.get_field(field_name)
                if not all((getattr(field, item, None) == value for item, value in field_attributes.items())):
                    valid_model = False
                    break
            except FieldDoesNotExist:
                valid_model = False
                break
        if valid_model:
            if not all(
                getattr(model_class, additional_field, None) == additional_value
                for additional_field, additional_value in additional_constraints.items()
            ):
                valid_model = False
        if valid_model:
            registry_items.setdefault(app_label, set()).add(model_name)

    registry_items = {key: sorted(value) for key, value in registry_items.items()}
    return registry_items


def construct_composite_key(values):
    """
    Convert the given list of natural key values to a single URL-path-usable string.

    - Non-URL-safe characters are percent-encoded.
    - Null (`None`) values are percent-encoded as a literal null character `%00`.

    Reversible by `deconstruct_composite_key()`.
    """
    values = [str(value) if value is not None else "\0" for value in values]
    # . and : are generally "safe enough" to use in URL parameters, and are common in some natural key fields,
    # so we don't quote them by default (although `deconstruct_composite_key` will work just fine if you do!)
    # / is a bit trickier to handle in URL paths, so for now we *do* quote it, even though it appears in IPAddress, etc.
    values = constants.COMPOSITE_KEY_SEPARATOR.join(quote_plus(value, safe=".:") for value in values)
    return values


def deconstruct_composite_key(composite_key):
    """
    Convert the given composite-key string back to a list of distinct values.

    - Percent-encoded characters are converted back to their raw values
    - Single literal null characters `%00` are converted back to a Python `None`.

    Inverse operation of `construct_composite_key()`.
    """
    values = [unquote_plus(value) for value in composite_key.split(constants.COMPOSITE_KEY_SEPARATOR)]
    values = [value if value != "\0" else None for value in values]
    return values


def construct_natural_slug(values, pk=None):
    """
    Convert the given list of natural key `values` to a single human-readable string.

    If `pk` is provided, it will be appended to the end of the natural slug. If the PK is a UUID,
    only the first four characters will be appended.

    A third-party lossy `slugify()` function is used to convert each natural key value to a
    slug, and then they are joined with an underscore.

    - Spaces or repeated dashes are converted to single dashes.
    - Accents and ligatures from Unicode characters are reduced to ASCII.
    - Remove remaining characters that are not alphanumerics, underscores, or hyphens.
    - Converted to lowercase.
    - Strips leading/trailing whitespace, dashes, and underscores.
    - Each natural key value in the list is separated by underscores.
    - Emojis will be converted to their registered name.

    This value is not reversible, is lossy, and is not guaranteed to be unique.
    """
    # In some cases the natural key might not be a list.
    if isinstance(values, tuple):
        values = list(values)

    # If a pk is passed through, append it to the values.
    if pk is not None:
        pk = str(pk)
        # Keep the first 4 characters of the UUID.
        if is_uuid(pk):
            pk = pk[:4]
        values.append(pk)

    values = (str(value) if value is not None else "\0" for value in values)
    # Replace any emojis with their string name, and then slugify that.
    values = (slugify(emoji.replace_emoji(value, unicodedata.name)) for value in values)
    return constants.NATURAL_SLUG_SEPARATOR.join(values)
