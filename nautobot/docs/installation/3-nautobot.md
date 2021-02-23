# Nautobot Installation

This section of the documentation discusses installing and configuring the Nautobot application itself.

## Install System Packages

Begin by installing all system packages required by Nautobot and its dependencies.

!!! note
    Nautobot requires Python 3.6, 3.7, or 3.8.

### Ubuntu

```no-highlight
$ sudo apt install -y python3 python3-pip python3-venv python3-dev build-essential libxml2-dev libxslt1-dev libffi-dev libpq-dev libssl-dev zlib1g-dev
```

### CentOS

```no-highlight
$ sudo yum install -y gcc python36 python36-devel python3-pip libxml2-devel libxslt-devel libffi-devel openssl-devel redhat-rpm-config
```

Before continuing with either platform, update pip (Python's package management tool) to its latest release:

```no-highlight
$ sudo pip3 install --upgrade pip
```

## Install Nautobot

FIXME(glenn) FIXME(jathan) Add information here for installing from Pip and configuring `BASE_STORAGE_DIR` to `/opt/nautobot/`.

The quickest and easiest way to install Nautobot is using `pip`. We recommend that you install Nautobot into a Python virtualenv (more docs on this later). 

At this time, this is the only supported method. New instructions will be added in the near future.

```bash
$ python3 -m venv nautobot 
$ source nautobot/bin/activate
(nautobot) $ pip3 install nautobot
```

### Verify your installation

You should now have a fancy `nautobot-server` command in your environment. This will be your gateway to all things Nautobot!

## Configuration

Initialize a new configuration by running `nautobot-server init`. You may specify an alternate location and detailed instructions for this are covered in [Nautobot Configuration](../configuration).

```bashj
$ nautobot-server init
Configuration file created at '/home/example/.nautobot/nautobot_config.py'
```

Your `nautobot_config.py` provides sane defaults for all of the configuration settings. You will inevitably need to update the settings for your environment. Nautobot offers [many configuration parameters](/configuration/), but only the following four are required for new installations:

* `ALLOWED_HOSTS`
* `DATABASES`
* `REDIS`
* `SECRET_KEY`

### ALLOWED_HOSTS

This is a list of the valid hostnames and IP addresses by which this server can be reached. You must specify at least one name or IP address. (Note that this does not restrict the locations from which Nautobot may be accessed: It is merely for [HTTP host header validation](https://docs.djangoproject.com/en/3.0/topics/security/#host-headers-virtual-hosting).)

```python
ALLOWED_HOSTS = ['nautobot.example.com', '192.0.2.123']
```

If you are not yet sure what the domain name and/or IP address of the Nautobot installation will be, you can set this to a wildcard (asterisk) to allow all host values:

```python
ALLOWED_HOSTS = ['*']
```

### DATABASES

This parameter holds the database configuration details. You must define the username and password used when you configured PostgreSQL. If the service is running on a remote host, update the `HOST` and `PORT` parameters accordingly. See the [configuration documentation](/configuration/required-settings/#databases) for more detail on individual parameters.

!!! warning
    Nautobot only supports PostgreSQL as a database backend. Do not modify the `ENGINE` setting or you
    will be unable to connect to the database.

```python
DATABASES = {
    'default':
        'NAME': 'nautobot',                         # Database name
        'USER': 'nautobot',                         # PostgreSQL username
        'PASSWORD': 'best_password',                # PostgreSQL password
        'HOST': 'localhost',                        # Database server
        'PORT': '',                                 # Database port (leave blank for default)
        'CONN_MAX_AGE': 300,                        # Max database connection age (seconds)
        'ENGINE': 'django.db.backends.postgresql',  # Database driver (Do not change this!)
}
```

### REDIS

Redis is a in-memory key-value store used by Nautobot for caching and background task queuing. Redis typically requires minimal configuration; the values below should suffice for most installations. See the [configuration documentation](/configuration/required-settings/#redis) for more detail on individual parameters.

Note that Nautobot requires the specification of two separate Redis databases: `tasks` and `caching`. These may both be provided by the same Redis service, however each should have a unique numeric database ID.

```python
REDIS = {
    'tasks': {
        'HOST': 'localhost',      # Redis server
        'PORT': 6379,             # Redis port
        'PASSWORD': '',           # Redis password (optional)
        'DATABASE': 0,            # Database ID
        'SSL': False,             # Use SSL (optional)
    },
    'caching': {
        'HOST': 'localhost',
        'PORT': 6379,
        'PASSWORD': '',
        'DATABASE': 1,            # Unique ID for second database
        'SSL': False,
    }
}
```

### SECRET_KEY

This parameter must be assigned a randomly-generated key employed as a salt for hashing and related cryptographic functions. (Note, however, that it is _never_ directly used in the encryption of secret data.) This key must be unique to this installation and is recommended to be at least 50 characters long. It should not be shared outside the local system.

A `SECRET_KEY` is automatically generated when you create a new `nautobot_config.py` file using `nautobot-server init`.

If you would like to generate a new key you may use the `nautobot-server generate_secret_key` management command:

```no-highlight
$ nautobot-server generate_secret_key.py
+$_kw69oq&fbkfk6&q-+ksbgzw1&061ghw%420u3(wen54w(m
```

!!! warning
    In the case of a highly available installation with multiple web servers, `SECRET_KEY` must be identical among all servers in order to maintain a persistent user session state.

When you have finished modifying the configuration, remember to save the file.

## Optional Requirements

!!! danger
    `FIXME(jathan)` This section needs to be revised because there is no
    "Nautobot root directory" when installing via `pip`.

All Python packages required by Nautobot will be installed automatically when using `pip install nautobot`. 

Nautobot also supports the ability to install optional Python packages. If desired, these packages must be listed in `local_requirements.txt` within the Nautobot root directory.

### NAPALM

The [NAPALM automation](https://napalm-automation.net/) library allows Nautobot to fetch live data from devices and return it to a requester via its REST API. The `NAPALM_USERNAME` and `NAPALM_PASSWORD` configuration parameters define the credentials to be used when connecting to a device.

```no-highlight
sudo echo napalm >> /opt/nautobot/local_requirements.txt
```

### Remote File Storage

By default, Nautobot will use the local filesystem to store uploaded files. To use a remote filesystem, install the [`django-storages`](https://django-storages.readthedocs.io/en/stable/) library and configure your [desired storage backend](/configuration/optional-settings/#storage_backend) in `configuration.py`.

```no-highlight
sudo echo django-storages >> /opt/nautobot/local_requirements.txt
```

## Run the Upgrade Script

Once Nautobot has been configured, we're ready to proceed with the actual installation. We'll run the packaged upgrade script (`upgrade.sh`) to perform the following actions:

* Create a Python virtual environment
* Install all required Python packages
* Run database schema migrations
* Aggregate static resource files on disk

```no-highlight
sudo /opt/nautobot/upgrade.sh
```

!!! note
    Upon completion, the upgrade script may warn that no existing virtual environment was detected. As this is a new installation, this warning can be safely ignored.

## Create a Super User

Nautobot does not come with any predefined user accounts. You'll need to create a super user (administrative account) to be able to log into Nautobot. First, enter the Python virtual environment created by the upgrade script:

```no-highlight
source /opt/nautobot/venv/bin/activate
```

Once the virtual environment has been activated, you should notice the string `(venv)` prepended to your console prompt.

Next, we'll create a superuser account using the `createsuperuser` Django management command (via `nautobot-server`). Specifying an email address for the user is not required, but be sure to use a very strong password.

```no-highlight
(venv) $ cd /opt/nautobot/nautobot_root
(venv) $ nautobot-server createsuperuser
Username: admin
Email address: admin@example.com
Password:
Password (again):
Superuser created successfully.
```

## Start the RQ Workers

[The previous section](2-redis.md) had you install Redis for caching and queuing.
Additionally, a separate "worker" process needs to be running to pick up and execute queued tasks; if no such process is running, tasks will remain enqueued indefinitely.

In production environments, it is advised to use a process manager for running workers;
[the next section](4-gunicorn.md) provides instructions for setting up systemd with Nautobot.
If not using a process manager, you must use the `rqworker` Django management command to start the workers.

```no-highlight
(venv) $ nautobot-server rqworker
```

## Test the Application

At this point, we should be able to run Nautobot's development server for testing. We can check by starting a development instance:

```no-highlight
(venv) $ nautobot-server runserver 0.0.0.0:8000 --insecure
Performing system checks...

System check identified no issues (0 silenced).
November 17, 2020 - 16:08:13
Django version 3.1.3, using settings 'nautobot.core.settings'
Starting development server at http://0.0.0.0:8000/
Quit the server with CONTROL-C.
```

Next, connect to the name or IP of the server (as defined in `ALLOWED_HOSTS`) on port 8000; for example, <http://127.0.0.1:8000/>. You should be greeted with the Nautobot home page.

!!! warning
    The development server is for development and testing purposes only. It is neither performant nor secure enough for production use. **Do not use it in production.**

!!! warning
    If the test service does not run, or you cannot reach the Nautobot home page, something has gone wrong. Do not proceed with the rest of this guide until the installation has been corrected.

Note that the initial user interface will be locked down for non-authenticated users.

![Nautobot UI as seen by a non-authenticated user](../media/installation/nautobot_ui_guest.png)

Try logging in using the superuser account we just created. Once authenticated, you'll be able to access all areas of the UI:

![Nautobot UI as seen by an administrator](../media/installation/nautobot_ui_admin.png)

Type `Ctrl+c` to stop the development server.
