from functools import lru_cache

from nautobot.extras.registry import registry


def limited_lru_cache(function=None, *, max_size=128, typed=False):
    """
    Decorate a function's return value to be cached in memory for the lifetime of an HTTP request/response cycle.

    Similar to (and in fact uses) `functools.lru_cache`, but adds the cached function to the Nautobot registry.
    The registry is used in `nautobot.core.middleware.LRUCacheClearingMiddleware` to ensure all tracked caches
    are cleared after each time Nautobot processes an HTTP request.

    In many cases it's useful to cache data throughout the lifetime of a single HTTP request to avoid repeated
    database lookups of the same information, but not throughout the entire lifetime of the Nautobot server process.

    For example, retrieving the set of related objects relevant to a given object might be valid to cache for the
    lifetime of a single GET request, but since that set of related objects may change over time as other processes
    make changes to the database, it would not be appropriate to have this cached information be longer-lived.

    You can still explicitly clear the cache (`my_function.cache_clear()`) as needed during a request, for example
    when a POST or PATCH results in a change in cached data.

    Examples:
        @limited_lru_cache
        def add(a, b=1):
            return a + b

        @limited_lru_cache(max_size=None)
        def subtract(a, b=1):
            return a - b
    """

    def _decorate(f):
        wrapped = lru_cache(max_size, typed)(f)
        registry.setdefault("tracked_lru_caches", []).append(wrapped)
        return wrapped

    if function is not None:
        # @limited_lru_cache
        # def function(...):
        return _decorate(function)

    # @limited_lru_cache(max_size=None)
    # def function(...):
    return _decorate
