# Installation

Nautobot can be deployed via Docker (Compose or Kubernetes) or directly onto a supported Linux system:

* [Nautobot Docker images](../guides/docker.md) are available via [Docker Hub](https://hub.docker.com/r/networktocode/nautobot) & [GitHub Container Registry](https://github.com/nautobot/nautobot/pkgs/container/nautobot) for use within a containerized environment
    * Install Nautobot via [Docker Compose](https://github.com/nautobot/nautobot-docker-compose)
    * [Install Nautobot via Helm Charts](https://docs.nautobot.com/projects/helm-charts/en/stable/) for Kubernetes
* [Install Nautobot](install_system.md) onto a [RHEL (Red Hat Enterprise Linux)](https://www.redhat.com/en/technologies/linux-platforms/enterprise-linux) or [Ubuntu](https://ubuntu.com/) virtual machine.

For more information about the Docker tags, Docker configurations, or using container images for your own development environment, see [Nautobot in Docker](../guides/docker.md).

??? info "Supported Platforms"

    Nautobot was designed to be a cross-platform application that can run on nearly any system that is able to run the required dependencies. *Only the operating system platforms listed below are officially supported at this time*.

    - Red Hat flavors of Linux including CentOS 8.2+ and Red Hat Enterprise Linux (RHEL) 8.2+ are supported.
    - Debian/Ubuntu flavors of Linux including Ubuntu 20.04+ and Debian 11+ are supported.

    Nautobot *should* work on any POSIX-compliant system including practically any flavor of Linux, BSD, or even macOS, but those are not *officially* supported at this time.

To begin installing Nautobot, click the link to your preferred deployment approach from the list above.

## About Dependencies

This section describes the system dependencies required for Nautobot. They can be all installed on a single system, or distributed across your environment. That will be up to you. Our install instructions assume a single system install, and that is good for most use cases. More advanced configurations are also possible, but are not covered here.

### Mandatory dependencies

The following minimum versions are required for Nautobot to operate:

| Dependency | Role         | Minimum Version |
| ---------- | ------------ | --------------- |
| Python     | Application  | 3.9             |
| PostgreSQL | Database     | 12.0            |
| MySQL      | Database     | 8.0             |
| Redis      | Cache, Queue | 4.0             |
| Git        | Additional   | 2.0             |

Nautobot will not work without these dependencies.

#### Python

Nautobot is written in the [Python programming language](https://www.python.org/). The official Python package installer is called [Pip](https://pip.pypa.io/en/stable/), and you will see the `pip` command referenced often to install or update Python packages.

+++ 1.3.0 "Python 3.10 support added"
    Python 3.10 support was added.

--- 1.3.0 "Python 3.6 support removed"
    Python 3.6 support was removed.

+/- 1.6.0 "Python 3.11 support added, Python 3.7 support removed"
    Python 3.11 support was added and Python 3.7 support was removed.

+++ 2.3.0 "Python 3.12 support added"
    Python 3.12 support was added.

--- 2.4.0 "Python 3.8 support removed"
    Python 3.8 support was removed.

#### Database

Nautobot uses a relational database to store its data. Both MySQL and PostgreSQL are officially supported.

+++ 1.1.0 "MySQL support added"
    MySQL support was added.

--- 2.1.0 "PostgreSQL minimum version became 12.0"
    Support for versions of PostgreSQL older than 12.0 was removed.

!!! note "Only one database"
    Either PostgreSQL or MySQL must be selected, but not both.

=== "MySQL"

    [MySQL](https://mysql.com) is an open-source relational database management system that’s relatively easy to set up and manage, fast, reliable, and well-understood.

=== "PostgreSQL"

    [PostgreSQL](https://www.postgresql.org) is a powerful, feature-rich open source relational database server that can handle complex queries and massive databases.

#### Redis

[Redis](https://redis.io/) is an open source, in-memory data store which Nautobot employs for caching and queuing.

### Optional dependencies

???+ abstract "Optional dependency information"

    Nautobot will still operate without these optional dependencies, but would likely not be ready for use in a production environment without them. The installation and configuration of these dependencies are covered in the detailed guides which follow.

    For production deployment we recommend the following:

    - [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) WSGI server
    - [NGINX](https://www.nginx.com/resources/wiki/) HTTP server
    - [External authentication](external-authentication.md) service for SSO such as SAML, OAuth2, or LDAP, or an authenticating proxy

    For additional features:

    - [NAPALM support](../../platform-functionality/napalm.md) for retrieving operational data from network devices
    - [Prometheus metrics](../guides/prometheus-metrics.md) for exporting application performance and telemetry data

## Upgrading

If you are upgrading from an existing installation, please consult the [upgrading guide](../upgrading/upgrading.md).
