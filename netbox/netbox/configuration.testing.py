###################################################################
#  This file serves as a base configuration for testing purposes  #
#  only. It is not intended for production use.                   #
###################################################################

import os

ALLOWED_HOSTS = ['*']

DATABASE = {
    'NAME': os.getenv('NETBOX_DATABASE', 'netbox'),
    'USER': os.getenv('NETBOX_USER', ''),
    'PASSWORD': os.getenv('NETBOX_PASSWORD', ''),
    'HOST': 'localhost',
    'PORT': '',
    'CONN_MAX_AGE': 300,
}

PLUGINS = [
    'extras.tests.dummy_plugin',
]

REDIS = {
    'tasks': {
        'HOST': 'localhost',
        'PORT': 6379,
        'PASSWORD': '',
        'DATABASE': 0,
        'SSL': False,
    },
    'caching': {
        'HOST': 'localhost',
        'PORT': 6379,
        'PASSWORD': '',
        'DATABASE': 1,
        'SSL': False,
    }
}

SECRET_KEY = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
