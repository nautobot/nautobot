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
        "django": {
            "handlers": ["normal_console"],
            "level": "INFO"
        },
        "nautobot": {
            "handlers": ["normal_console"],
            "level": LOG_LEVEL,
        },
    },
}
```

## Example Logs

```no-highlight
20:50:57.972 INFO    django.server:  "GET /health/ HTTP/1.1" 200 11743
20:50:58.769 INFO    django.server:  "GET /login/?next=/ HTTP/1.1" 200 18336
20:51:04.710 INFO    django.server:  "GET /health/ HTTP/1.1" 200 11741
20:51:05.836 INFO    nautobot.auth.login:  User admin successfully authenticated
20:51:07.340 INFO    django.server:  "POST /login/ HTTP/1.1" 302 0
20:51:10.182 INFO    django.server:  "GET / HTTP/1.1" 200 118573
21:02:25.928 WARNING django.request: user=admin Not Found: /api/ipam/ip-addresses/63b38cc7-979d-52c4-b26f-e44dd5f390ca/
21:02:25.945 WARNING django.server: "GET /api/ipam/ip-addresses/63b38cc7-979d-52c4-b26f-e44dd5f390ca/ HTTP/1.1" 404 15611
```
