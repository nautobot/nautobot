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
            "level": "DEBUG",
            "class": "logging.StreamHandler",
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
