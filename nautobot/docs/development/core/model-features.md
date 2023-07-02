# Registry Model Features

A dictionary of particular features (e.g. custom fields) mapped to the Nautobot models which support them, arranged by app.

## Add a new feature to the `model_features` registry

The `populate_model_features_registry()` function updates the registry model features with new apps. This is done by defining a list of dictionaries called `lookup_confs`. Each dictionary in `lookup_confs` contains the following three keys:

- `feature_name`: The name of the feature to be updated in the registry.
- `field_names`: A list of names of fields that must be present in order for the model to be considered a valid `model_feature`.
- `field_attributes`: An optional dictionary of attributes used to filter the fields. Only models with fields matching all the attributes specified in the dictionary will be considered. This parameter can be useful to narrow down the search for fields that match certain criteria. For example, if `field_attributes` is set to `{"related_model": RelationshipAssociation}`, only fields with a `related_model` of `RelationshipAssociation` will be considered.

To add a new feature to the `lookup_confs` list, follow these steps:

1. Determine the name of the feature to be added, This name should be in `snake_case` as per convention
2. Determine the names of the fields that must be present in order for the model to be considered a valid `model_feature`.
3. (Optional) Determine any field attributes that can be used to filter the fields if `field_names` would not be enough.
4. Add a new dictionary with the following keys to `lookup_confs` which is in  `nautobot.extras.utils.populate_model_features_registry()`:
    - `feature_name`: The name of the feature.
    - `field_names`: The list of names of fields.
    - `field_attributes`: (Optional) The dictionary of attributes to filter the fields.

```python
from nautobot.extras.models.relationships import RelationshipAssociation


def populate_model_features_registry():
    """..."""

    lookup_confs = [
        ...,
        {
            "feature_name": "relationships",
            "field_names": ["source_for_associations", "destination_for_associations"],
            "field_attributes": {"related_model": RelationshipAssociation},
        },
       ...
    ]
```

With this only Models which have fields names of `source_for_associations` and `destination_for_associations`, which in turn has the attribute `related_model=RelationshipAssociation`, would be a valid model for the feature `relationships`.

!!! note
   `populate_model_features_registry()` and `lookup_confs` provide an alternative to the older method of feature flagging models via the `@extras_features` decorator. In general new feature flags should preferentially be implemented via additions to `lookup_confs`, *not* by any new additions to `extras_features`.
