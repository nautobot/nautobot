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

!!! note
    MySQL or other relational databases are not currently supported.

#### Redis

[Redis](https://redis.io/) is an open source, in-memory data store which Nautobot employs for caching and queuing.

### Optional dependencies

Nautobot will still operate without these optional dependencies, but would likely not be ready for use in a production
environment without them. The installation and configuration of these dependencies are covered in the detailed guides on
[Deploying Nautobot](deploying-nautobot).

For production deployment we recommend the following:

- [Gunicorn](https://gunicorn.org) WSGI server
- [NGINX](https://www.nginx.com/resources/wiki/) HTTP server
- [External authentication](external-authentication) service for SSO such as SAML, OAuth2, or LDAP, or an authenticating proxy

For additional features:

- NAPALM support
- Prometheus metrics

## Install Nautobot

Nautobot was designed to be a cross-platform application that can run on nearly any system that is able to run the
required dependencies. Only the operating system platforms listed below are officially supported at this time.

### Supported Platforms

Nautobot has been tested and confirmed to work on the following platforms. Detailed install and deployment instructions
can be found by following the link to each.

- [CentOS](centos)
- [Ubuntu](ubuntu)

## Upgrading

If you are upgrading from an existing installation, please consult the [upgrading guide](upgrading.md).
