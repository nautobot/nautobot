# Application Stack

Nautobot is built on the [Django](https://djangoproject.com/) Python Web framework and requires either a [PostgreSQL](https://www.postgresql.org/) or [MySQL](https://www.mysql.com) database backend. It runs as a WSGI service behind your choice of HTTP server.

## Components

<!-- markdownlint-disable no-inline-html heading-style blanks-around-headings-->
<div class="grid cards" markdown>

- :material-language-python:{ .lg .middle } **Python**

    ---
    :material-language-python: Python 3.8 - 3.11 support

- :material-database:{ .lg .middle } **Database**

    ---
    :simple-postgresql: PostgreSQL 12+  
    :simple-mysql: MySQL 8.0+

- :simple-django:{ .lg .middle } **Application**

    ---
    Django/Python for the Nautobot web application.

- :material-gate:{ .lg .middle } **WSGI Service**

    ---
    Handles communication between the Nautobot Python web framework and the HTTP web server.

- :material-web:{ .lg .middle } **HTTP Service**

    ---
    NGINX

- :material-cached:{ .lg .middle } **Cache**

    ---
    :simple-redis: Django/Redis

- :material-human-queue:{ .lg .middle } **Task Queuing**

    ---
   :simple-celery: Celary  
   :simple-redis: Redis

- :material-truck-delivery-outline:{ .lg .middle } **Live Device Access**

    ---
   [NAPALM](https://napalm.readthedocs.io/en/latest/) and [NAPALM Community Drivers](https://github.com/napalm-automation-community).

</div>
<!-- markdownlint-enable no-inline-html heading-style blanks-around-headings -->

## Application Diagram

The following diagram displays how data travels through Nautobot's application stack.

<!-- markdownlint-disable no-inline-html -->
<figure markdown="span">
![Application stack diagram](../media/nautobot_application_stack_low_level.png "Application stack diagram")
</figure>
<!-- markdownlint-enable no-inline-html -->

## Getting Started

See the [installation guide](../user-guide/administration/installation/index.md) for help getting Nautobot up and running quickly.


## Dependency History

+++ 1.1.0 "MySQL support"
    MySQL support was added.

+/- 1.3.0 "Python 3.6, Python 3.10"
    - Python 3.6 support was removed.
    - Python 3.10 support was added.
    
+/- 1.6.0 "Python 3.7, Python 3.11"
    - Python 3.7 support was removed.
    - Python 3.11 support was added.
    
--- 2.0.0 "django-rq and django-cacheops"
    - `django-rq` support was removed.
    - `django-cacheops` usage was removed and replaced with Django's native caching features.

--- 2.1.0 "PostgreSQL <12.0"
    Support for versions of PostgreSQL older than 12.0 was removed.

## Notices

> Nautobot was initially developed as a fork of NetBox (v2.10.4), which was originally created by Jeremy Stretch at DigitalOcean and by the NetBox open source community.
