# Deploy Nautobot

This section of the documentation discusses installing and configuring the Nautobot application itself.

The instructions will guide you through the following actions:

- Create a `nautobot` system account 
- Establish a Nautobot root at `/opt/nautobot`
- Create a Python virtual environment (virtualenv)
- Install Nautobot and all required Python packages
- Run the database schema migrations
- Aggregate static resource files on disk

## Create the Nautobot System User

Create a system user account named `nautobot`. This user will own all of the Nautobot files, and the Nautobot web services will be configured to run under this account. 

```no-highlight
$ sudo useradd --create-home --system --shell /bin/bash nautobot
```

## Upgrade Pip

[Pip]((https://pip.pypa.io/)) is Python's package installer and is referred interchangeably as `pip` or `pip3`. For the purpose of this document, we'll deliberately be referring to it as `pip3`.

Many common issues can be solved by running the latest version of Pip. Before continuing with installing Nautobot, upgrade Pip to its latest release:

```no-highlight
$ sudo pip3 install --upgrade pip
```

## Choose your `NAUTOBOT_ROOT`

This is where everything related to Nautobot will be installed. We're going to use this value across the documentation. You'll need to set the `NAUTOBOT_ROOT` environment variable to tell Nautobot where to find its files and settings at `/opt/nautobot`.

```no-highlight
$ export NAUTOBOT_ROOT=/opt/nautobot
```

## Create the Virtual Environment

A Python [virtual environment](https://docs.python.org/3/tutorial/venv.html) or *virtualenv* is like a container for a set of Python packages. A virtualenv allows you to build environments suited to specific projects without interfering with system packages or other projects. When installed per the documentation, Nautobot uses a virtual environment in production.

We're going to create the virtualenv as our `NAUTOBOT_ROOT` as the root user to bootstraps the `/opt/nautobot` directory and populate it with a self-contained Python environment. 

```no-highlight
$ sudo python3 -m venv $NAUTOBOT_ROOT
```

Next, change ownership of `NAUTOBOT_ROOT` to the `nautobot` user:

```no-highlight
$ sudo chown -R nautobot:nautobot $NAUTOBOT_ROOT
```

## Sudo to nautobot

Now that we've created the virtualenv, the remaining steps will be performed as the `nautobot` user. 

!!! warning
    Don't skip this step!!

    It's important to install Nautobot as the `nautobot` user so that we don't have to worry about fixing permissions later.

```no-highlight
$ sudo su - nautobot
```

After becoming `nautobot`, we need to set the `NAUTOBOT_ROOT` environment variable again for this user (since it is a fresh session as far as the system is concerned):

```no-highlight
$ export NAUTOBOT_ROOT=/opt/nautobot
```

### Add `NAUTOBOT_CONFIG` to `.bashrc`

For bonus points, add this to `~/.bashrc` for `nautobot`:

```no-highlight
$ echo "export NAUTOBOT_ROOT=/opt/autobot" >> ~/.bashrc
```

From here on out, anytime you become `nautobot`, your `NAUTOBOT_ROOT` will be set automatically.

## Activate the Virtual Environment

!!! warning
    This and all remaining steps in this document should all be performed as the `nautobot` user!

    Hint: Use `sudo su - nautobot`

To work inside a Python virtualenv, it must be activated. This makes sure that the version of Python you're using, as well any dependencies that you install remain isolated in this environment. 

If it helps, try to think of activating the virtualenv like entering a shell unique to Nautobot's application environment.

```no-highlight
$ source /opt/nautobot/bin/activate
(nautobot) $
```

Observe that after activating, your prompt will now be preceded with the name of the virtualenv (`nautobot`).

!!! note
    From here on out, any time you see a command prompt preceded by `(nautobot)`, that is your indicator that you should be activated in the virtualenv.

## Prepare the Virtual Environment

Before we install anything into the virtualenv, we want to make sure that Pip is running the latest version. This is neecessary because sometimes when a new virtualenv is created, a cached version of Pip is installed into it. (Yes, even after we've deliberately upgraded Pip at the system level!)

We also want to deliberately install the `wheel` library which will tell Pip to always try to install wheel packages if they are available. A [wheel is a pre-compiled Python package](https://realpython.com/python-wheels/), which is quicker and safer to install because it does not require development libraries or `gcc` to be installed on your system just so that some more advanced Python libraries can be compiled. 

```no-highlight
(nautobot) $ pip3 install --upgrade pip wheel
```

## Install Nautobot

Use Pip to install Nautobot:

```no-highlight
(nautobot) $ pip3 install nautobot
```

Great! We have a virtualenv ready for use by the `nautobot` user, so let's proceed to verifying the installation.

## Verify your Nautobot Installation

You should now have a fancy `nautobot-server` command in your environment. This will be your gateway to all things Nautobot! Run it to confirm the installed version of `nautobot`:

```no-highlight
(nautobot) $ nautobot-server --version
```

## Configuration

Before you can use Nautobot, you'll need to configure it by telling it where your database and Redis servers can be found, among other things. This is done with the `nautobot_config.py` configuration file.

### Initialize your configuration

Initialize a new configuration by running `nautobot-server init`. You may specify an alternate location and detailed instructions for this are covered in the documentation on [Nautobot Configuration](../../configuration).

However, because we've set the `NAUTOBOT_ROOT`, this command will automatically create a new `nautobot_config.py` at the default location based on this at `/opt/nautobot/nautobot_config.py`:

```no-highlight
(nautobot) $ nautobot-server init
```

### Required Settings

Your `nautobot_config.py` provides sane defaults for all of the configuration settings. You will inevitably need to update the settings for your environment.

Prepare to edit `/opt/nautobot/nautobot_config.py`, and head over to the documentation on [Required Settings](../../configuration/required-settings) to tweak your required settings.

Save your changes to your `nautobot_config.py` and then return here.

## Optional Settings

All Python packages required by Nautobot will be installed automatically when running `pip3 install nautobot`.

Nautobot also supports the ability to install optional Python packages. If desired, these packages should be listed in `local_requirements.txt` within the `NAUTOBOT_ROOT` directory at `/opt/nautobot/local_requirements.txt`.

If you decide to use any [Nautobot plugins](../../plugins), they should be listed in this file.

We will cover two examples of common optional settings below.

### Configuring NAPALM

Nautobot provides built-in support for the [NAPALM automation](https://napalm-automation.net/) library, which allows Nautobot to fetch live data from devices and return it to a requester via its REST API. The [`NAPALM_USERNAME`](../../configuration/optional-settings#napalm_username) and [`NAPALM_PASSWORD`](../../configuration/optional-settings#napalm_password) configuration parameters define the credentials to be used when connecting to a device.

To use NAPALM, add `napalm` to your `local_requirements.txt` so that it can be installed and kept up to date:

```no-highlight
(nautobot) $ echo napalm >> /opt/nautobot/local_requirements.txt
```

### Remote File Storage

By default, Nautobot will use the local filesystem to store uploaded files. To use a remote filesystem, install the [`django-storages`](https://django-storages.readthedocs.io/en/stable/) library and configure your [desired storage backend](/configuration/optional-settings/#storage_backend) in `nautobot_config.py`.

To use remote file storage, add `django-storages` to your `local_requirements.txt` so that it can be installed and kept up to date:

```no-highlight
(nautobot) $ echo django-storages >> /opt/nautobot/local_requirements.txt
```

## Prepare the Database

Before Nautobot can run, the database migrations must be performed to prepare the database for use. This will populate the database tables and relationships:

```no-highlight
(nautobot) $ nautobot-server migrate
```

## Create a Superuser

Nautobot does not come with any predefined user accounts. You'll need to create a super user (administrative account) to be able to log into Nautobot. Specifying an email address for the user is not required, but be sure to use a very strong password.

```no-highlight
(nautobot) $ nautobot-server createsuperuser
```

## Create Static Directories

Nautobot relies upon many static files including:

- `git` - For storing [Git repositories](../../models/extras/gitrepository)
- `jobs` - For storing [custom Jobs](../../additional-features/jobs)
- `media` - For storing [uploaded images and attachments](../../configuration/optional-settings/#media_root) (such as device type images)
- `static` - The home for [CSS, JavaScript, and images](../../configuration/optional-settings/#static_root) used to serve the web interface

Each of these have their own corresponding setting that defined in `nautobot_config.py`, but by default they will all be placed in `NAUTOBOT_ROOT` unless you tell Nautobot otherwise by customizing their unique variable.

The `collectstatic` command will create these directories if they do not exist, and in the case of the `static` files directory, it will also copy the appropriate files:

```no-highlight
(nautobot) $ nautobot-server collectstatic
```

## Install local requirements

This step is entirely optional. As indicated above, we mentioned that any extra local requirements should go into `/opt/nautobot/local_requirements.txt`.

```no-highlight
(nautobot) $ pip3 install -r /opt/nautobot/local_requirements.txt
```

## Test the Application

At this point, we should be able to run Nautobot's development server for testing. We can check by starting a
development instance:

```no-highlight
(nautobot) $ nautobot-server runserver 0.0.0.0:8000 --insecure
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

Type `Ctrl-C` to stop the development server.
