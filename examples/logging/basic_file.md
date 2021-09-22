This example sends logging to files in `/var/log/nautobot`, please note this directory should exist and 
be writeable by the nautobot user.  Files are rotated daily for 5 days at midnight UTC.

```python
LOG_DIR = "/var/log/nautobot"
LOG_LEVEL = "DEBUG" if DEBUG else "INFO"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "normal": {
            "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s:  %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "nautobot_log": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": f"{LOG_DIR}/nautobot.log",
            "when": "midnight",
            "utc": True,
            "interval": 1,
            "backupCount": 5,
            "formatter": "normal",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["nautobot_log"],
            "level": "INFO"
        },
        "nautobot": {
            "handlers": ["nautobot_log"],
            "level": LOG_LEVEL,
        },
    },
}
```

## Example Logs

```no-highlight
20:38:28.967 INFO    django.server: "GET / HTTP/1.1" 200 29409
20:38:29.174 INFO    django.server: "GET /static/debug_toolbar/js/toolbar.js HTTP/1.1" 304 0
20:38:29.194 INFO    django.server: "GET /static/debug_toolbar/css/toolbar.css HTTP/1.1" 304 0
20:38:29.677 INFO    django.server: "GET /static/debug_toolbar/css/print.css HTTP/1.1" 304 0
20:38:29.775 INFO    django.server: "GET /static/debug_toolbar/js/utils.js HTTP/1.1" 304 0
20:38:33.433 INFO    django.server: "GET /login/?next=/ HTTP/1.1" 200 18335
20:38:40.878 DEBUG   nautobot.auth.login: Login form validation was successful
20:38:41.121 INFO    nautobot.auth.login: User admin successfully authenticated
20:38:41.121 DEBUG   nautobot.auth.login: Redirecting user to /
20:38:42.053 INFO    django.server: "POST /login/ HTTP/1.1" 302 0
```
