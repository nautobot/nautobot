# Configuration

NetBox's local configuration is held in `netbox/netbox/configuration.py`. An example configuration is provided at `netbox/netbox/configuration.example.py`. You may copy or rename the example configuration and make changes as appropriate. NetBox will not run without a configuration file.

## Mandatory Settings

---

#### DATABASE

NetBox requires access to a PostgreSQL database service to store data. This service can run locally or on a remote system. The following parameters must be defined within the `DATABASE` dictionary:

* NAME - Database name
* USER - PostgreSQL username
* PASSWORD - PostgreSQL password
* HOST - Name or IP address of the database server (use `localhost` if running locally)
* PORT - TCP port of the PostgreSQL service; leave blank for default port (5432)

---

#### SECRET_KEY

This is a secret cryptographic key is used to improve the security of cookies and password resets. The key defined here should not be shared outside of the configuration file. `SECRET_KEY` can be changed at any time, however be aware that doing so will invalidate all existing sessions.

Please note that this key is **not** used for hashing user passwords or for the encrypted storage of secret data in NetBox.

`SECRET_KEY` should be at least 50 characters in length and contain a random mix of letters, digits, and symbols. The following Python code can be used to generate a key:

```
import os
import random

charset = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
random.seed = (os.urandom(2048))
print ''.join(random.choice(charset) for c in range(50))
```

---

#### ALLOWED_HOSTS

This is a list of valid host names by which NetBox may be reached. This list is used to defend against cross-site scripting (XSS) attacks. You must specify at least one host name.

Example:

```
ALLOWED_HOSTS = ['netbox.example.com', 'netbox.internal.local']
```

## Optional Settings

---

#### TIME_ZONE

Default: UTC

The time zone NetBox will use when dealing with dates and times. It is recommended to use UTC time unless you have a specific need to use a local time zone. [List of available time zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

---

#### LOGIN_REQUIRED

Default: False,

Setting this to True will permit only authenticated users to access any part of NetBox. By default, anonymous users are permitted to access most data in NetBox (excluding secrets) but not make any changes.

---

#### PAGINATE_COUNT

Default: 50

Determine how many objects to display per page within each list of objects.

---

#### NETBOX_USERNAME

#### NETBOX_PASSWORD

If provided, NetBox will use these credentials to authenticate against devices when collecting data.

---

#### MAINTENANCE_MODE

Default: False

Setting this to True will display a "maintenance mode" banner at the top of every page.

---

#### DEBUG

Default: False

This setting enables debugging. This should be done only during development or troubleshooting. Never enable debugging on a production system, as it can expose sensitive data to unauthenticated users. 
