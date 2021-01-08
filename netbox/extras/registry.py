from collections import defaultdict, namedtuple


class Registry(dict):
    """
    Central registry for registration of functionality. Once a store (key) is defined, it cannot be overwritten or
    deleted (although its value may be manipulated).
    """
    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            raise KeyError("Invalid store: {}".format(key))

    def __setitem__(self, key, value):
        if key in self:
            raise KeyError("Store already set: {}".format(key))
        super().__setitem__(key, value)

    def __delitem__(self, key):
        raise TypeError("Cannot delete stores from registry")


registry = Registry()


DatasourceContent = namedtuple('DatasourceContent', ['name', 'token', 'icon', 'callback'])
"""
name (str): Human-readable name for this content type, such as "config contexts"
token (str): Brief unique identifier of this content type, such as "extras.ConfigContext"
icon (str): Material Design Icons icon name, such as "mdi-code-json" or "mdi-script-text"
callback (callable): Callback function to invoke whenever a given datasource is updated,
    if it provides this content type. This callback should take two arguments (model, job_result) where "model"
    is the record that is being refreshed and "job_result" is an extras.JobResult record for logging purposes.
"""


registry['datasource_contents'] = defaultdict(list)


def register_datasource_contents(datasource_contents_list):
    """
    Register a list of (model_name, DatasourceContent) entries.
    """
    for model_name, content in datasource_contents_list:
        if not isinstance(model_name, str):
            raise TypeError(f"{model_name} must be a string")
        if not isinstance(content, DatasourceContent):
            raise TypeError(f"{content} must be an instance of extras.datasources.DatasourceContent")
        registry['datasource_contents'][model_name].append(content)
