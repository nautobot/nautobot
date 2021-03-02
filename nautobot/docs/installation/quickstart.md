# Nautobot Quick Start

Nautobot is very easy to get running. If you want to get up and running with Nautobot, this guide is for you.

!!! note
    This quick start guide makes a lot of assumptions. If it doesn't work for you or these concepts are unfamiliar to
    you, please skip this and head directly to the [Installation](..) guide.

## Assumptions

This quick start guide makes the following assumptions:

- You have Python 3.6 or higher
- You have the latest version `pip`
- You have a Python `virtualenv` or similar isolated Python environment to 
- You have a PostgreSQL database or know how to create one
- You have a Redis server
- You can directly access the system where Nautobot will be installed

As mentioned above, if you don't have these things or they are unfamiliar to you, please skip this quick start and head
over to the [Installation](..) guide.

## Quick Start

### 1. Install Nautobot

```
$ pip install nautobot
```

### 2. Initialize a new configuration 

This will create a default config in `~/.nautobot/nautbot_config.py`:

```
$ nautobot-server init
```

### 3. Edit your `nautobot_config.py` 

You'll need to edit `nautobot_config.py` to update your database and Redis settings:

!!! note
    The default values assume that you're running PostgreSQL and Redis on `localhost`.

- Update `DATABASES` to point to your PostgreSQL database with any necessary credentials
- Update `RQ_QUEUES` and `CACHE_OPS` to point to your Redis server

### 4. Populate the database schema

Before Nautobot can run, the database migrations must be ran, to populate the database tables and relationships.

```
$ nautobot-server migrate
```

### 5. Create a Nautobot superuser

This user account will be used to administer Nautobot.

```
$ nautobot-server createsuperuser
```

### 6. Start the development server listening on port `8000`:

```
$ nautobot-server runserver 0.0.0.0:8000 --insecure
```

!!! note
    Hint: The `--insecure` flag tells the development server to also serve static files. For obvious reasons this is not
    intended for production use.

Fire up your favorite browser and visit [http://localhost:8000](http://localhost:8000)! If you're not running it on your
local system, just change `localhost` to match the hostname or IP of your server.

Use the superuser username/password you created in step 5 to login.

## Next Steps

Now that you've got a basic installation of Nautobot running, try the following:

!!! danger
    FIXME(jathan): Flesh out this section with what people SHOULD be doing after setting up Nautobot

- Head over to the tutorial to start getting to know Nautobot
- Familiarize yourself with the `nautobot-server` management command
- Eat a baked potato
- Melt some hot cheese
