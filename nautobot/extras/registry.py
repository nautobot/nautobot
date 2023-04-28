from collections import defaultdict


class Registry(dict):
    """
    Central registry for registration of functionality. Once a store (key) is defined, it cannot be overwritten or
    deleted (although its value may be manipulated).
    """

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            raise KeyError(f"Invalid store: {key}")

    def __setitem__(self, key, value):
        if key in self:
            raise KeyError(f"Store already set: {key}")
        super().__setitem__(key, value)

    def __delitem__(self, key):
        raise TypeError("Cannot delete stores from registry")


registry = Registry(
    datasource_contents=defaultdict(list),
    secrets_providers={},
)


class DatasourceContent:
    """
    Args:
      name (str): Human-readable name for this content type, such as "config contexts"
      content_identifier (str): Brief unique identifier of this content type; by convention a string such as "extras.configcontext"
      icon (str): Material Design Icons icon name, such as "mdi-code-json" or "mdi-script-text"
      callback (callable): Callback function to invoke whenever a given datasource is created, updated, or deleted.
          This callback should take three arguments (record, job_result, delete) where "record" is the GitRepository, etc.
          that is being refreshed, "job_result" is an extras.JobResult record for logging purposes, and
          "delete" is a boolean flag to distinguish between the "create/update" and "delete" cases.
      weight (int): Defines the order in which datasources will be loaded.
    """

    __slots__ = ["name", "content_identifier", "icon", "callback", "weight"]

    def __init__(self, name, content_identifier, icon, callback, weight=1000):
        """Ensure datasource properties."""
        self.name = name
        self.content_identifier = content_identifier
        self.icon = icon
        self.callback = callback
        self.weight = weight


def register_datasource_contents(datasource_contents_list):
    """
    Register a list of (model_name, DatasourceContent) entries.
    """
    for model_name, content in datasource_contents_list:
        if not isinstance(model_name, str):
            raise TypeError(f"{model_name} must be a string")
        if not isinstance(content, DatasourceContent):
            raise TypeError(f"{content} must be an instance of extras.datasources.DatasourceContent")
        registry["datasource_contents"][model_name].append(content)
