This logging configuration is great for running Nautobot locally in Docker with `DEBUG=True`.  It is 
impractical to use in production due to the multi-line output:

```python
LOG_LEVEL = "DEBUG" if DEBUG else "INFO"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "normal": {
            "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s :\n  %(message)s",
            "datefmt": "%H:%M:%S",
        },
        "verbose": {
            "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)-20s %(filename)-15s %(funcName)30s() :\n  %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "normal_console": {
            "level": "INFO",
            "class": "rq.utils.ColorizingStreamHandler",
            "formatter": "normal",
        },
        "verbose_console": {
            "level": "DEBUG",
            "class": "rq.utils.ColorizingStreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {"handlers": ["normal_console"], "level": "INFO"},
        "nautobot": {
            "handlers": ["verbose_console" if DEBUG else "normal_console"],
            "level": LOG_LEVEL,
        },
        "rq.worker": {
            "handlers": ["verbose_console" if DEBUG else "normal_console"],
            "level": LOG_LEVEL,
        },
    },
}
```
