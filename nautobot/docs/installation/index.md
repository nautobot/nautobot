# Installation

This set of documents will help you get Nautobot up and running.  As an alternative, you can also [run Nautobot in Docker](/docker).

!!! warning
    As of Nautobot v1.0.0b3 these instructions are still in a pre-release state. We are working to revise them for the recent changes.

## About Dependencies

This section describes the system dependencies required for Nautobot. They can be all installed on a single system, or distributed across your environment. That will be up to you. Our install instructions assume a single system install, and that is good for most use cases. More advanced configurations are also possible, but are not covered here.

The [installation instructions](#installing-nautobot-dependencies) below will guide you through a fresh installation.

### Mandatory dependencies

The following minimum versions are required for Nautobot to operate:

| Dependency | Minimum Version |
|------------|-----------------|
| Python     | 3.6             |
| PostgreSQL | 9.6             |
| Redis      | 4.0             |

Nautobot will not work without these dependencies.

#### Python

Nautobot is written in the [Python programming language](https://www.python.org/). The official Python package installer
is called [Pip](https://pip.pypa.io/en/stable/), and you will see the `pip` command referenced often to install or
update Python packages.

All Nautobot plugins and library dependencies will be written using Python.

#### PostgreSQL

[PostgreSQL](https://www.postgresql.org) is a powerful, open source relational database server. Nautobot uses the database to store its data.

!!! note
    MySQL or other relational databases are not currently supported.

#### Redis

[Redis](https://redis.io/) is an open source, in-memory data store which Nautobot employs for caching and queuing.

### Optional dependencies

Nautobot will still operate without these optional dependencies, but would likely not be ready for use in a production
environment without them. The installation and configuration of these dependencies are covered in the detailed guides on
[Deploying Nautobot](deploying-nautobot).

For production deployment we recommend the following:

- [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) WSGI server
- [NGINX](https://www.nginx.com/resources/wiki/) HTTP server
- [External authentication](external-authentication) service for SSO such as SAML, OAuth2, or LDAP, or an authenticating proxy

For additional features:

- [NAPALM support](../additional-features/napalm) for retrieving operational data from network devices
- [Prometheus metrics](../additional-features/prometheus-metrics) for exporting application performance and telemetry data

## Installing Nautobot Dependencies

Nautobot was designed to be a cross-platform application that can run on nearly any system that is able to run the
required dependencies. *Only the operating system platforms listed below are officially supported at this time*.

Nautobot has been tested and confirmed to work on the following platforms. Detailed install and deployment instructions
can be found by following the link to each.

### Installing Nautobot Dependencies on CentOS/RHEL

Red Hat flavors of Linux including CentOS 8.2+ or Red Hat Enterprise Linux (RHEL) 8.2+ are supported. The same installation instructions can be used on either.

- [Installing Nautobot Dependencies on CentOS/RHEL](centos)

### Installing Nautobot Dependencies on Ubuntu

Ubuntu 20.04 or later is supported.

- [Installing Nautobot Dependencies on Ubuntu](ubuntu)

### Installing on Other Systems

Nautobot should work on any POSIX-compliant system including practically any flavor of Linux, BSD, or even macOS, but those are not *officially* supported at this time.

### Running Nautobot in Docker

Nautobot docker images are available for use in a containerized deployment for an easier installation, see the [Docker overview](/docker) for more information.

## Upgrading

If you are upgrading from an existing installation, please consult the [upgrading guide](upgrading.md).
