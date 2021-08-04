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
            "class": "logging.StreamHandler",
            "formatter": "normal",
        },
        "verbose_console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["normal_console"],
            "level": "INFO"
        },
        "nautobot": {
            "handlers": ["verbose_console" if DEBUG else "normal_console"],
            "level": LOG_LEVEL,
        },
    },
}
```

## Example Logs

```no-highlight
  "GET / HTTP/1.1" 200 29109
20:23:04.320 INFO    django.server :
  "GET /static/debug_toolbar/css/toolbar.css HTTP/1.1" 200 11461
20:23:04.326 INFO    django.server :
  "GET /static/debug_toolbar/js/toolbar.js HTTP/1.1" 200 10452
20:23:04.957 INFO    django.server :
  "GET /static/debug_toolbar/css/print.css HTTP/1.1" 200 43
20:23:05.013 INFO    django.server :
  "GET /static/debug_toolbar/js/utils.js HTTP/1.1" 200 2988
20:23:06.901 INFO    django.server :
  "GET /login/?next=/ HTTP/1.1" 200 18334
20:23:10.246 DEBUG   nautobot.auth.login  views.py                                  post() :
  Login form validation was successful
20:23:10.335 INFO    nautobot.auth.login  views.py                                  post() :
  User admin successfully authenticated
20:23:10.335 DEBUG   nautobot.auth.login  views.py                      redirect_to_next() :
  Redirecting user to /
20:23:10.801 INFO    django.server :
  "POST /login/ HTTP/1.1" 302 0
20:23:11.254 DEBUG   nautobot.releases    releases.py                 get_latest_release() :
  Skipping release check; RELEASE_CHECK_URL not defined
20:23:12.806 INFO    django.server :
  "GET / HTTP/1.1" 200 118574
```