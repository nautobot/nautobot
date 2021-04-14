# Caching

Nautobot supports database query caching using [django-cacheops](https://github.com/Suor/django-cacheops) and Redis. When a query is made, the results are cached in Redis for a short period of time, as defined by the [`CACHEOPS_DEFAULTS`](../../configuration/optional-settings/#cacheops_defaults) parameter (15 minutes by default). Within that time, all recurrences of that specific query will return the pre-fetched results from the cache.

If a change is made to any of the objects returned by the query within that time, or if the timeout expires, the results are automatically invalidated and the next request for those results will be sent to the database.

!!! important
    Cacheops does not utilize the built-in [Django cache
framework](https://docs.djangoproject.com/en/stable/topics/cache/) to perform caching. Therefore it does not rely upon the `CACHES` setting. Instead it monkey patches the underlying queryset methods to intercept calls to get and set cached items in Redis.

## Invalidating Cached Data

Although caching is performed automatically and rarely requires administrative intervention, Nautobot provides the `invalidate` management command to force invalidation of cached results. This command can reference a specific object my its type and UUID:

```no-highlight
$ nautobot-server invalidate dcim.Device.84ae706d-c189-4d13-a898-9737648e34b3
```

Alternatively, it can also delete all cached results for an object type:

```no-highlight
$ nautobot-server invalidate dcim.Device
```

Finally, calling it with the `all` argument will force invalidation of the entire cache database:

```no-highlight
$ nautobot-server invalidate all
```
