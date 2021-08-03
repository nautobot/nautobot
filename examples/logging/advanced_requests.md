By default django logs [4xx and 5xx requests](https://docs.djangoproject.com/en/3.2/topics/logging/#django-request) 
but is missing details such as the request user name.  This can be helpful in debugging. This example 
shows how the request user can be added to the logs.

```python
def add_username(record):
    record.username = record.request.user.username
    return True


LOG_LEVEL = "DEBUG" if DEBUG else "INFO"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "normal": {
            "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s: %(message)s",
            "datefmt": "%H:%M:%S",
        },
        "request": {
            "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s: user=%(username)s %(message)s",
            "datefmt": "%H:%M:%S",
        },
        "verbose": {
            "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)-20s %(filename)-15s %(funcName)30s(): %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "normal_console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "normal",
        },
        "requests": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "request",
            "filters": ["add_username"],
        },
    },
    "filters": {
        "add_username": {
            "()": "django.utils.log.CallbackFilter",
            "callback": add_username,
        }
    },
    "loggers": {
        "django.request": {
            "handlers": ["requests"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django": {"handlers": ["normal_console"], "level": LOG_LEVEL},
        "nautobot": {
            "handlers": ["normal_console"],
            "level": LOG_LEVEL,
        },
        "rq.worker": {
            "handlers": ["normal_console"],
            "level": LOG_LEVEL,
        },
    },
}
```