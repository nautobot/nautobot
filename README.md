# Nautobot

![Nautobot](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/nautobot_logo.svg "Nautobot logo")

Nautobot is a Network Source of Truth and Network Automation Platform.

> Nautobot was initially developed as a fork of NetBox (v2.10.4).  NetBox was originally developed by Jeremy Stretch at DigitalOcean and the NetBox Community.

Nautobot runs as a web application atop the [Django](https://www.djangoproject.com/) Python framework with a
[PostgreSQL](https://www.postgresql.org/) or [MySQL](https://www.mysql.com) database.

The complete documentation for Nautobot can be found at [Read the Docs](https://nautobot.readthedocs.io/en/stable/).

Questions? Comments? Start by perusing our [GitHub discussions](https://github.com/nautobot/nautobot/discussions) for the topic you have in mind, or join the **#nautobot** channel on [Network to Code's Slack community](https://slack.networktocode.com/)!

## Build Status

| Branch      | Status |
|-------------|------------|
| **main** | [![Build Status](https://github.com/nautobot/nautobot/actions/workflows/ci_integration.yml/badge.svg?branch=main)](https://github.com/nautobot/nautobot/actions/workflows/ci_integration.yml) |
| **develop** | [![Build Status](https://github.com/nautobot/nautobot/actions/workflows/ci_integration.yml/badge.svg?branch=develop)](https://github.com/nautobot/nautobot/actions/workflows/ci_integration.yml) |
| **next** | [![Build Status](https://github.com/nautobot/nautobot/actions/workflows/ci_integration.yml/badge.svg?branch=next)](https://github.com/nautobot/nautobot/actions/workflows/ci_integration.yml) |

## Screenshots

![Screenshot of main page](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/media/ss_main_page.png "Main page")

---

![Screenshot of config contexts](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/media/ss_config_contexts.png "Config Contexts")

---

![Screenshot of prefix hierarchy](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/media/ss_prefix_hierarchy.png "Prefix hierarchy")

---

![Screenshot of GraphQL](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/media/ss_graphiql.png "GraphQL API")

## Installation

Please see [the documentation](https://nautobot.readthedocs.io/en/stable/installation/) for instructions on installing Nautobot.

## Application Stack

Below is a simplified overview of the Nautobot application stack for reference:

![Application stack diagram](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/media/nautobot_application_stack_high_level.png "Application stack diagram")

## Plugins and Extensibility

Nautobot offers the ability to customize your setup to better align with your direct business needs. It does so through the use of various plugins that have been developed for network automation, and are designed to be used in environments where needed.

There are many plugins available within the Nautobot Apps ecosystem. The below screenshots are an example of some popular ones that are currently available.

### Plugin Screenshots

#### Golden Config Plugin

![Screenshot of golden config](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/media/ss_plugin_golden_config.png "Golden config")

#### ChatOps Plugin

![Screenshot of chatops](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/media/ss_plugin_chatops.png "ChatOps")

## Providing Feedback

The best platform for general feedback, assistance, and other discussion is our [GitHub discussions](https://github.com/nautobot/nautobot/discussions). To report a bug or request a specific feature, please open a GitHub issue using the [appropriate template](https://github.com/nautobot/nautobot/issues/new/choose).

If you are interested in contributing to the development of Nautobot, please read our [contributing guide](CONTRIBUTING.md) prior to beginning any work.

## Related projects

Please see [our wiki](https://github.com/nautobot/nautobot/wiki/Related-Projects) for a list of relevant community projects.
