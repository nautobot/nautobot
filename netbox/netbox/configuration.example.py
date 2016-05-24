#########################
#                       #
#   Required settings   #
#                       #
#########################

# PostgreSQL database configuration.
DATABASE = {
    'NAME': 'netbox',         # Database name
    'USER': 'netbox',         # PostgreSQL username
    'PASSWORD': '',           # PostgreSQL password
    'HOST': 'localhost',      # Database server
    'PORT': '',               # Database port (leave blank for default)
}

# This key is used for secure generation of random numbers and strings. It must never be exposed outside of this file.
# For optimal security, SECRET_KEY should be at least 50 characters in length and contain a mix of letters, numbers, and
# symbols. NetBox will not run without this defined. For more information, see
# https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-SECRET_KEY
SECRET_KEY = ''

# Set this to your server's FQDN. This is required when DEBUG = False.
# E.g. ALLOWED_HOSTS = ['netbox.yourdomain.com']
ALLOWED_HOSTS = []


#########################
#                       #
#   Optional settings   #
#                       #
#########################

# Time zone (default: UTC)
TIME_ZONE = 'UTC'

# Setting this to True will permit only authenticated users to access any part of NetBox. By default, anonymous users
# are permitted to access most data in NetBox (excluding secrets) but not make any changes.
LOGIN_REQUIRED = False

# Determine how many objects to display per page within a list. (Default: 50)
PAGINATE_COUNT = 50

# Credentials that NetBox will use to access live devices.
NETBOX_USERNAME = ''
NETBOX_PASSWORD = ''

# Setting this to True will display a "maintenance mode" banner at the top of every page.
MAINTENANCE_MODE = False
