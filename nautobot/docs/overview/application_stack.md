# Application Stack

Nautobot is built on the [Django](https://djangoproject.com/) Python Web framework and requires either a [PostgreSQL](https://www.postgresql.org/) or [MySQL](https://www.mysql.com) database backend. It runs as a WSGI service behind your choice of HTTP server.

## Components

<!-- pyml disable-num-lines 9 no-inline-html,proper-names -->
| Function           | Component                                                                                                                          |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| HTTP service       | :simple-nginx: NGINX                                                                                                               |
| WSGI service       | :material-web: uWSGI or Gunicorn                                                                                                   |
| Application        | :simple-django: Django <br> :material-language-python: Python 3.9 - 3.12 supported                                                 |
| Database           | :simple-postgresql: PostgreSQL 12+ or <br>  :simple-mysql: MySQL 8.0+                                                              |
| Cache              | :simple-redis: Django/Redis                                                                                                        |
| Task queuing       | :simple-redis: Redis / :simple-celery: Celery                                                                                      |
| Live device access | [NAPALM](https://napalm.readthedocs.io/en/latest/) and [NAPALM Community Drivers](https://github.com/napalm-automation-community). |

## Application Diagram

The following diagram displays how data travels through Nautobot's application stack.

![Application stack diagram](../media/nautobot_application_stack_low_level.png "Application stack diagram")

## Getting Started

See the [installation guide](../user-guide/administration/installation/index.md) for help getting Nautobot up and running quickly.

## Dependency History

--- 2.0.0 "`django-rq` and `django-cacheops`"
    - `django-rq` support was removed.
    - `django-cacheops` usage was removed and replaced with Django's native caching features.

--- 2.1.0 "PostgreSQL <12.0"
    Support for versions of PostgreSQL older than 12.0 was removed.

+++ 2.3.0 "Python 3.12, Django 4"
    - Python 3.12 support was added.
    - Nautobot migrated from Django 3.2 to Django 4.2.

--- 2.4.0 "Python 3.8"
    Python 3.8 support was removed.

## Notices

> Nautobot was initially developed as a fork of NetBox (v2.10.4), which was originally created by Jeremy Stretch at DigitalOcean and by the NetBox open source community.
