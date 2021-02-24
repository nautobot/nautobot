# Nautobot Installation

This section of the documentation discusses installing and configuring the Nautobot application itself.

## Install System Packages

Begin by installing all system packages required by Nautobot and its dependencies.

!!! note
    Nautobot requires Python 3.6, 3.7, or 3.8.

### Ubuntu

```no-highlight
$ sudo apt install -y git python3 python3-pip python3-venv python3-dev 
```

### CentOS

```no-highlight
$ sudo yum install -y git python36 python36-devel python3-pip
```

Before continuing with either platform, update [`pip`](https://pip.pypa.io/), Python's package installer, to its latest release:

```no-highlight
$ sudo pip3 install --upgrade pip
```

## Download Nautobot

This documentation provides several options for installing Nautobot: 

- From a downloadable archive
- From the Git repository

### Download a Release Archive

Installing from a package requires manually fetching and extracting the archive for every future update.

Download the [latest stable release](https://github.com/nautobot/nautobot/releases) from GitHub as a tarball or ZIP
archive and extract it to your desired path. In this example, we'll use `/opt/nautobot` as the Nautobot root.

```no-highlight
$ sudo wget https://github.com/nautobot-community/nautobot/archive/vX.Y.Z.tar.gz
$ sudo tar -xzf vX.Y.Z.tar.gz -C /opt
$ sudo ln -s /opt/nautobot-X.Y.Z/ /opt/nautobot
$ ls -ld /opt/nautobot*
lrwxrwxrwx 1 root root   22 Feb 24 05:54 /opt/nautobot -> /opt/nautobot-1.0.0b1/
drwxrwxr-x 8 root root 4096 Feb 24 00:40 /opt/nautobot-1.0.0b1
```

!!! note
    It is recommended to install Nautobot in a directory named for its version number. For example, Nautobot v1.0.0
    would be installed into `/opt/nautobot-1.0.0`, and a symlink from `/opt/nautobot/` would point to this location.
    This allows for future releases to be installed in parallel without interrupting the current installation. When
    changing to the new release, only the symlink needs to be updated.

### Clone the Git Repository

Installation via git allows for seamless upgrades by re-pulling the `main` branch.

Create the base directory for the Nautobot installation. For this guide, we'll use `/opt/nautobot`.

```no-highlight
sudo mkdir -p /opt/nautobot/ && cd /opt/nautobot/
```

Next, clone the **main** branch of the Nautobot GitHub repository into the current directory. (This branch always holds
the current stable release.)

```no-highlight
$ sudo git clone -b main https://github.com/nautobot/nautobot.git .
Cloning into '.'...
remote: Counting objects: 1994, done.
remote: Compressing objects: 100% (150/150), done.
remote: Total 1994 (delta 80), reused 0 (delta 0), pack-reused 1842
Receiving objects: 100% (1994/1994), 472.36 KiB | 0 bytes/s, done.
Resolving deltas: 100% (1495/1495), done.
Checking connectivity... done.
```

!!! note
    Installation via git also allows you to easily try out development versions of Nautobot. The `develop` branch
    contains all work underway for the next minor release, and the `feature` branch tracks progress on the next major
    release. 

## Setup the Nautobot User Environment

### Create the Nautobot System User

Create a system user account named `nautobot`. We'll configure the WSGI and HTTP services to run under this account.
We'll also assign this user ownership of the media directory. This ensures that Nautobot will be able to save uploaded
files.

#### Ubuntu

```no-highlight
$ sudo adduser --system --group nautobot
```

#### CentOS

```no-highlight
$ sudo groupadd --system nautobot
$ sudo adduser --system -g nautobot nautobot
```

## Install Nautobot

!!! warning
    As of Nautobot v1.0.0b1 these instructions are in a pre-release state and will be evolving rapidly!

### Run the Install Script

Now that you've established the prerequisites for Nautobot, you're ready to proceed with the actual installation. 

The included install script (`install.sh`) will perform the following actions:

- Create a Python virtual environment
- Install Nautobot and all required Python packages
- Run the database schema migrations
- Aggregate static resource files on disk

!!! warning
    As of Nautobot v1.0.0b1 the first time you run `install.sh` it will fail with the error `Configuration file does not exist at '/opt/nautobot/nautobot_config.py'`


```no-highlight
$ sudo /opt/nautobot/install.sh
```

You should see a lot of Python packages get installed, and then end here:

```
Skipping local dependencies (local_requirements.txt not found)
Applying database migrations (nautobot-server migrate)...
Configuration file does not exist at '/opt/nautobot/nautobot_config.py'
```

Great! We have a virtualenv to use now that was created by the `install.sh` script, so let's proceed to verifying the
installation. We will end up running `install.sh` again after this.

### Activate the Virtual Environment

To verify the installation worked, activate the Python virtual environment (aka virtualenv) created by the install
script and observe that afterward your prompt will change to the name of the virtualenv (`venv`):

```no-highlight
$ source /opt/nautobot/venv/bin/activate
(venv) $
```

### Verify your installation

You should now have a fancy `nautobot-server` command in your environment. This will be your gateway to all things
Nautobot! Run it to confirm the installed version of `nautobot`:

```
(venv) $ nautobot-server --version
1.0.0b1
```

## Deactivate the Virtual Environment

Now exit the virtualenv. Observe that your prompt returns to normal.

```
(venv) $ deactivate
$
```

You've now got a working Nautobot virtual environment. Excellent!

## Configuration

Before you can use Nautobot, you'll need to configure it by telling it where your database and Redis servers can be
found, among other things. This is done with the `nautobot_config.py` configuration file.

### Initializing a Configuration

Initialize a new configuration by running `nautobot-server init`. You may specify an alternate location and detailed
instructions for this are covered in the documentation on [Nautobot Configuration](../../configuration).

!!! warning
    For pre-release, please run `nautobot-server init` as root using `sudo`. This will not be required as we approach
    final release.

We'll want to create the `nautobot_config.py` your current directory at `/opt/nautobot`:

```no-highlight
$ sudo /opt/nautobot/venv/bin/nautobot-server init /opt/nautobot/nautobot_config.py
Configuration file created at '/opt/nautobot/nautobot_config.py'
```

### Required Settings

Your `nautobot_config.py` provides sane defaults for all of the configuration settings. You will inevitably need to
update the settings for your environment.

Head over to the documentation on [Required Settings](../../configuration/required-settings) to tweak your settings, and
then return here.

## Optional Settings

All Python packages required by Nautobot will be installed automatically when running the `install.sh` script.

Nautobot also supports the ability to install optional Python packages. If desired, these packages must be listed in
`local_requirements.txt` within the Nautobot root directory at `/opt/nautobot`.

### Configuring NAPALM

Nautobot provides built-in support for the [NAPALM automation](https://napalm-automation.net/) library, which allows
Nautobot to fetch live data from devices and return it to a requester via its REST API. The `NAPALM_USERNAME` and
`NAPALM_PASSWORD` configuration parameters define the credentials to be used when connecting to a device.

```no-highlight
sudo echo napalm >> /opt/nautobot/local_requirements.txt
```

### Remote File Storage

By default, Nautobot will use the local filesystem to store uploaded files. To use a remote filesystem, install the
[`django-storages`](https://django-storages.readthedocs.io/en/stable/) library and configure your [desired storage
backend](/configuration/optional-settings/#storage_backend) in `configuration.py`.

```no-highlight
sudo echo django-storages >> /opt/nautobot/local_requirements.txt
```

## Run the Install Script Again

!!! warning
    Just a brief reminder that these are pre-release instructions that are rapidly evolving! You will not be required to
    run `install.sh` twice as we approach final release.

Now that you have a `nautobot_config.py` with your database and Redis servers defined, run `install.sh` again:

```no-highlight
$ sudo /opt/nautobot/install.sh
```

This time the script should complete with output that looks something like this:

```no-highlight
Upgrade complete! Don't forget to restart the Nautobot services:
  > sudo systemctl restart nautobot nautobot-rq
```

!!! note
    Upon completion, the upgrade script may warn that no existing virtual environment was detected. As this is a new
    installation, this warning can be safely ignored.

## Set the NAUTOBOT_CONFIG variable

This will tell the `nautobot-server` command where to find the configuration when it isn't deployed to a default
location. This can also be done using the `--config` argument.

```
$ export NAUTOBOT_CONFIG=/opt/nautobot/nautobot_config.py
```

## Create a Super User

Nautobot does not come with any predefined user accounts. You'll need to create a super user (administrative account) to
be able to log into Nautobot.

Earlier, we had you enter the Python virtual environment created by `install.sh`, but just in case, here is the command again:

```no-highlight
$ source /opt/nautobot/venv/bin/activate
```

Once the virtual environment has been activated, you should notice the string `(venv)` prepended to your console prompt.

Next, we'll create a superuser account using the `createsuperuser` Django management command (via `nautobot-server`).
Specifying an email address for the user is not required, but be sure to use a very strong password.

```no-highlight
(venv) $ nautobot-server createsuperuser
Username: admin
Email address: admin@example.com
Password:
Password (again):
Superuser created successfully.
```

## Start the RQ Workers

[The previous section](2-redis.md) had you install Redis for caching and queuing. Additionally, a separate "worker"
process needs to be running to pick up and execute queued tasks; if no such process is running, tasks will remain
enqueued indefinitely.

In production environments, it is advised to use a process manager for running workers; [the next
section](4-gunicorn.md) provides instructions for setting up systemd with Nautobot. If not using a process manager, you
must use the `rqworker` Django management command to start the workers.

```no-highlight
(venv) $ nautobot-server rqworker
```

## Test the Application

At this point, we should be able to run Nautobot's development server for testing. We can check by starting a
development instance:

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
