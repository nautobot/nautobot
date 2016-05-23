#########################
#                       #
#   Required settings   #
#                       #
#########################

# This key is used for secure generation of random numbers and strings. It must never be exposed outside of this file.
# For optimal security, SECRET_KEY should be at least 50 characters in length and contain a mix of letters, numbers, and
# symbols. NetBox will not run without this defined. For more information, see
# https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-SECRET_KEY
SECRET_KEY = ''

# Set this to your server's FQDN. This is required when DEBUG = False.
# E.g. ALLOWED_HOSTS = ['netbox.yourdomain.com']
ALLOWED_HOSTS = []

# PostgreSQL database configuration.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'netbox',                           # Database name
        'USER': 'netbox',                           # PostgreSQL username
        'PASSWORD': '',                             # PostgreSQL password
        'HOST': 'localhost',                        # Database server
        'PORT': '',                                 # Database port (leave blank for default)
    }
}


#########################
#                       #
#   Optional settings   #
#                       #
#########################

# Setting this to True will display a "maintenance mode" banner at the top of every page.
MAINTENANCE_MODE = False

# If enabled, NetBox will run with debugging turned on. This should only be used for development or troubleshooting.
#
# NEVER ENABLE DEBUGGING ON A PRODUCTION SYSTEM!
DEBUG = False

# If True, user authentication will be required for all site access. If False, unauthenticated users will be able to
# access NetBox but not make any changes.
LOGIN_REQUIRED = False

# Determine how many objects to display per page within a list. (Default: 50)
PAGINATE_COUNT = 50

# Credentials that NetBox will use to access live devices.
NETBOX_USERNAME = ''
NETBOX_PASSWORD = ''
