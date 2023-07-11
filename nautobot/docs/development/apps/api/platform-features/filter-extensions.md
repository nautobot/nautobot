# Extending Filters

+++ 1.3.0

Apps can extend any model-based `FilterSet` and `FilterForm` classes that are provided by the Nautobot core.

The requirements to extend a filter set or a filter form (or both) are:

* The file must be named `filter_extensions.py`
* The variable `filter_extensions` must be declared in that file, and contain a list of `FilterExtension` subclasses
* The `model` attribute of each `FilterExtension` subclass must be set to a valid model name in the dotted pair format (`{app_label}.{model}`, e.g. `tenant.tenant` or `dcim.device`)

Nautobot dynamically creates many additional filters based upon the defined filter type. Specifically, there are additional lookup expressions (referred to in code as `lookup_expr`) that are created for each filter, when there is neither a `lookup_expr` nor `method` parameter already set. These dynamically-added lookup expressions are added using a shorthand notation (e.g. `icontains` is `ic`). Nautobot will also add the negation of each, for example, so `icontains` will be added along with _not_ `icontains` using the `ic` and `nic` expressions respectively.

The dynamically-added lookup expressions can be found in the source code at [nautobot/core/constants.py](https://github.com/nautobot/nautobot/blob/main/nautobot/core/constants.py) and the mapping logic can be found in [nautobot/core/filters.py](https://github.com/nautobot/nautobot/blob/main/nautobot/core/filters.py). Please see the documentation on [filtering](../../../../user-guide/platform-functionality/rest-api/filtering.md##lookup-expressions) for more information.

!!! tip
    For developers of apps that define their own model filters, note that the above are added dynamically, as long as the class inherits from `nautobot.apps.filters.BaseFilterSet`.

However, that does not cover every possible use case, to list a few examples:

* Usage of a custom `method` argument on a filter that points to a `FilterSet` method, which would allow arbitrary filtering using custom logic. This is how the `q` field search logic is currently performed.
* Creation of a filter on a field that does not currently have filtering support
* Convenience methods for highly nested fields

There are several conditions that must be met in order to extend a filter:

* The original FilterSet must follow the pattern: `f"{model.__name__}FilterSet"` e.g. `TenantFilterSet`
* The `FilterExtension.filterset_fields` attribute must be a valid dict, with each key being the filter name (which must start with the plugin's `name` + `_`, e.g. `"example_plugin_description"`, not merely `"description"`) and each value being a valid [django-filter](https://django-filter.readthedocs.io/en/main/) filter

Nautobot will dynamically generate the additional relevant lookup expressions of an app's defined custom FilterSet field, so no need to additionally register `example_plugin_description__ic`, etc.

Similar to `FilterSet` fields, Nautobot provides a default filter form for each model, however that does not cover every possible use case. To list a few examples of why one may want to extend a filter form:

* The base filter form does not include a custom filter defined by the app as described above
* The base filter form does not provide a specific lookup expression to a filterable field, such as allowing regex on name

There are several conditions that must be met in order to extend a filter:

* The original `FilterForm` must follow the pattern: `f"{model.__name__}FilterForm"`, e.g. `TenantFilterForm`
* The `filterform_fields` attribute must be a valid dictionary of Django form fields

!!! note
    An app is not required to define both `filterset_fields` and `filterform_fields`.

You can view an example of `filter_extensions.py` by viewing [the one provided](https://github.com/nautobot/nautobot/blob/main/examples/example_plugin/example_plugin/filter_extensions.py) with the Example Plugin.

!!! tip
    The `method` parameter, if used, must be a callable (method/function). Note that because filters with a `method` do their filtering in Python code rather than at the database level, performance of `method` filters is generally much poorer than pure-database filters. The `method` parameter is not supported when using [Dynamic Groups](../../../../user-guide/platform-functionality/dynamicgroup.md).
