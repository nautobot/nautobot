class PluginError(Exception):
    """Base exception for all plugin-related errors."""


class PluginNotFound(PluginError):
    """Raised when a specified plugin module cannot be found."""


class PluginImproperlyConfigured(PluginError):
    """Raised when a plugin is not properly configured."""
