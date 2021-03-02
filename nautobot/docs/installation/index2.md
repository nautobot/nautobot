# Installation

This document will help you get Nautobot up and running.

!!! warning
    As of Nautobot v1.0.0b1 these instructions are still in a pre-release state. We are working to revise them for the recent changes. 

## Dependencies

### Mandatory dependencies

The following minimum versions are required for Nautobot to operate:

| Dependency | Minimum Version |
|------------|-----------------|
| Python     | 3.6             |
| PostgreSQL | 9.6             |
| Redis      | 4.0             |

Nautobot will not work with these dependencies.

#### Python

Nautobot is written in the [Python programming language](https://www.python.org/). The official Python package installer
is called [Pip](https://pip.pypa.io/en/stable/), and you will see the `pip` command referenced often to install or
update Python packages.

All Nautobot plugins and library dependencies will be written using Python.

#### PostgreSQL

[PostgreSQL](https://www.postgresql.org) is a powerful, open source relational database server. Nautobot uses the database to store its data.

PostgreSQL was selected as the database backend due to its native support for [network address types](https://www.postgresql.org/docs/13/datatype-net-types.html). 

MySQL or other relational databases are not currently supported.

#### Redis

[Redis](https://redis.io/) is an open source, in-memory data store which Nautobot employs for caching and queuing.

### Optional dependencies

Nautobot will still operate without these optional dependencies, but would likely not be ready for use in a production
environment without them. The installation and configuration of these dependencies are covered in the guide on
[Deploying Nautobot](deploying-nautobot).

For production deployment we recommend the following:

- Gunicorn WSGI server
- NGINX HTTP server
- External authentication service for SSO such as SAML, OAuth2, or LDAP, or an authenticating proxy

For additional features:

- NAPALM support
- Prometheus metrics

## Supported Platforms

!!! note
    Nautobot was designed to be a cross-platform application that can run on nearly any system that can run the
    dependencies. Only the following platforms are officially supported at this time.

Nautobot has been tested and confirmed to work on the following platforms. Detailed install and deployment instructions
can be found by following the link to each.

- [CentOS](centos)
- [Ubuntu](ubuntu)

### Additional Setup

The following sections detail how to set up a new instance of Nautobot:

3. [Nautobot components](3-nautobot.md)
4. [Gunicorn](4-gunicorn.md)
5. [HTTP server](5-http-server.md)
6. [External authentication](6-external-authentication.md) (optional)

## Upgrading

If you are upgrading from an existing installation, please consult the [upgrading guide](upgrading.md).
