# Add User information for error requests (4xx and 5xx)

By default django logs [4xx and 5xx requests](https://docs.djangoproject.com/en/3.2/topics/logging/#django-request) 
but is missing details such as the request user name.  This can be helpful in debugging. This example 
shows how the request user can be added to the logs for 4xx and 5xx responses.

```python
def add_username(record):
    if hasattr(record, "request") and hasattr(record.request, "user"):
        record.username = record.request.user.username
    else:
        record.username = ""
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
            "level": "INFO",
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

---

# Add user information for ALL requests

Unfortunately, when running Nautobot behind uWSGI only failed requests are logged through the django.request logger.  We can get more information
from all requests by installing the [`django-request-logging`]((https://github.com/Rhumbix/django-request-logging)) package.  

```no-highlight
$ sudo -u nautobot pip install django-request-logging
```

Add the following to `nautobot_config.py`:

```python
EXTRA_MIDDLEWARE = ["request_logging.middleware.LoggingMiddleware"]
```

## Example Logs

```no-highlight
20:15:56.177 INFO    django.request: user= GET /health/
20:15:56.177 INFO    django.request: user= GET /health/ - 200
20:15:58.447 INFO    django.request: user=admin GET /api/circuits/circuit-terminations/
20:15:58.450 INFO    django.request: user=admin GET /api/circuits/circuit-terminations/ - 200
20:16:13.989 INFO    django.request: user=admin GET /api/circuits/circuit-terminations/?circuit_id=asdfasdfasdfasdf
20:16:13.990 ERROR   django.request: user=admin {'HTTP_HOST': 'localhost:8080', 'HTTP_CONNECTION': 'keep-alive', 'HTTP_SEC_CH_UA': '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"', 'HTTP_ACCEPT': 'application/json', 'HTTP_USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36', 'HTTP_SEC_CH_UA_MOBILE': '?0', 'HTTP_AUTHORIZATION': '*****', 'HTTP_X_CSRFTOKEN': 'pm8I0mnAiAzPA3XIILzu45k7B1wzXCCyZD5eanxVWglxeZVqLfzaurnIfN9wD8Cg', 'HTTP_SEC_FETCH_SITE': 'same-origin', 'HTTP_SEC_FETCH_MODE': 'cors', 'HTTP_SEC_FETCH_DEST': 'empty', 'HTTP_REFERER': 'http://localhost:8080/api/docs/', 'HTTP_ACCEPT_ENCODING': 'gzip, deflate, br', 'HTTP_ACCEPT_LANGUAGE': 'en-US,en;q=0.9', 'HTTP_COOKIE': 'rl_anonymous_id=%22337aa074-9fc4-46cb-a5f7-b71b811e9312%22; rl_user_id=%22%22; grafana_session=74f409830dea81d2a06dfd88fc0deda5; csrftoken=VFeVVhUPOJjMOr8wvlKQXKKqkJVGo522vWbr5i4asp5usn6eyPKwn6N1YvyD4B2K; sessionid=4pcy6m4zv187ys96dm5d0s9cmf1qt4oh'}
20:16:13.990 ERROR   django.request: user=admin b''
20:16:13.992 INFO    django.request: user=admin GET /api/circuits/circuit-terminations/?circuit_id=asdfasdfasdfasdf - 400
20:16:13.992 ERROR   django.request: user=admin {'content-type': ('Content-Type', 'application/json'), 'vary': ('Vary', 'Accept'), 'allow': ('Allow', 'GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS, TRACE')}
20:16:13.992 ERROR   django.request: user=admin b'{"circuit_id":["\xe2\x80\x9casdfasdfasdfasdf\xe2\x80\x9d is not a valid UUID."]}'
```

The [`django-request-logging`](https://github.com/Rhumbix/django-request-logging) module provides both the request and the response. In the case of a 400-599 response code it also provides detailed information about the request -- this may not be ideal for some environments.
