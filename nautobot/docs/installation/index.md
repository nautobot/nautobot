# Installation

This set of documents will help you get Nautobot up and running.  As an alternative, you can also [run Nautobot in Docker](../docker/index.md).

## About Dependencies

This section describes the system dependencies required for Nautobot. They can be all installed on a single system, or distributed across your environment. That will be up to you. Our install instructions assume a single system install, and that is good for most use cases. More advanced configurations are also possible, but are not covered here.

The [installation instructions](#installing-nautobot-dependencies) below will guide you through a fresh installation.

### Mandatory dependencies

The following minimum versions are required for Nautobot to operate:

| Dependency | Role         | Minimum Version |
|------------|--------------|-----------------|
| Python     | Application  | 3.7             |
| PostgreSQL | Database     | 9.6             |
| MySQL      | Database     | 8.0             |
| Redis      | Cache, Queue | 4.0             |

!!! note
    Either PostgreSQL or MySQL must be selected, but not both.

+++ 1.1.0
    MySQL support was added.

+++ 1.3.0
    Python 3.10 support was added.

--- 1.3.0
    Python 3.6 support was removed.

Nautobot will not work without these dependencies.

#### Python

Nautobot is written in the [Python programming language](https://www.python.org/). The official Python package installer is called [Pip](https://pip.pypa.io/en/stable/), and you will see the `pip` command referenced often to install or
update Python packages.

All Nautobot plugins and library dependencies will be written using Python.

#### Database

Nautobot uses a relational database to store its data. Both MySQL and PostgreSQL are officially supported.

##### MySQL

[MySQL](https://mysql.com) is an open-source relational database management system that’s relatively easy to set up and manage, fast, reliable, and well-understood.

##### PostgreSQL

[PostgreSQL](https://www.postgresql.org) is a powerful, feature-rich open source relational database server that can handle complex queries and massive databases.

#### Redis

[Redis](https://redis.io/) is an open source, in-memory data store which Nautobot employs for caching and queuing.

### Optional dependencies

Nautobot will still operate without these optional dependencies, but would likely not be ready for use in a production environment without them. The installation and configuration of these dependencies are covered in the detailed guides which follow.

For production deployment we recommend the following:

- [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) WSGI server
- [NGINX](https://www.nginx.com/resources/wiki/) HTTP server
- [External authentication](external-authentication.md) service for SSO such as SAML, OAuth2, or LDAP, or an authenticating proxy

For additional features:

- [NAPALM support](../additional-features/napalm.md) for retrieving operational data from network devices
- [Prometheus metrics](../additional-features/prometheus-metrics.md) for exporting application performance and telemetry data

## Installing Nautobot Dependencies

Nautobot was designed to be a cross-platform application that can run on nearly any system that is able to run the
required dependencies. *Only the operating system platforms listed below are officially supported at this time*.

Nautobot has been tested and confirmed to work on the following platforms. Detailed install and deployment instructions
can be found by following the link to each.

### Installing Nautobot Dependencies on CentOS/RHEL

Red Hat flavors of Linux including CentOS 8.2+ or Red Hat Enterprise Linux (RHEL) 8.2+ are supported. The same installation instructions can be used on either.

- [Installing Nautobot Dependencies on CentOS/RHEL](centos.md)

### Installing Nautobot Dependencies on Ubuntu

Ubuntu 20.04 or later is supported.

- [Installing Nautobot Dependencies on Ubuntu](ubuntu.md)

### Installing on Other Systems

Nautobot should work on any POSIX-compliant system including practically any flavor of Linux, BSD, or even macOS, but those are not *officially* supported at this time.

### Running Nautobot in Docker

Nautobot docker images are available for use in a containerized deployment for an easier installation, see the [Docker overview](../docker/index.md) for more information.

## Upgrading

If you are upgrading from an existing installation, please consult the [upgrading guide](upgrading.md).
