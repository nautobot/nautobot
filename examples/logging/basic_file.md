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
        "verbose": {
            "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)-20s %(filename)-15s %(funcName)30s(): %(message)s",
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
