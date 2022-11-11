# Nautobot

![Nautobot](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/nautobot_logo.svg "Nautobot logo")

Nautobot is a Network Source of Truth and Network Automation Platform built as a web application atop the [Django](https://www.djangoproject.com/) Python framework with a
[PostgreSQL](https://www.postgresql.org/) or [MySQL](https://www.mysql.com) database.

## Key Use Cases

**1. Flexible Source of Truth for Networking** - Nautobot core data models are used to define the intended state of network infrastructure enabling it as a Source of Truth. While a baseline set of models are provided (such as IP networks and addresses, devices and racks, circuits and cable, etc.) it is Nautobot's goal to offer maximum data model flexibility. This is enabled through features such as user-defined relationships, custom fields on any model, and data validation that permits users to codify everything from naming standards to having automated tests run before data can be populated into Nautobot.

**2. Extensible Data Platform for Automation** - Nautobot has a rich feature set to seamlessly integrate with network automation solutions. Nautobot offers GraphQL and native Git integration along with REST APIs and webhooks. Git integration dynamically loads YAML data files as Nautobot config contexts. Nautobot also has an evolving plugin system that enables users to create custom models, APIs, and UI elements. The plugin system is also used to unify and aggregate disparate data sources creating a Single Source of Truth to streamline data management for network automation.

**3. Platform for Network Automation Apps** - The Nautobot plugin system enables users to create Network Automation Apps. Apps can be as lightweight or robust as needed based on user needs. Using Nautobot for creating custom applications saves up to 70% development time by re-using features such as authentication, permissions, webhooks, GraphQL, change logging, etc. all while having access to the data already stored in Nautobot. Some production ready applications include:

The complete documentation for Nautobot can be found at [Read the Docs](https://docs.nautobot.com/).

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

Please see [the documentation](https://docs.nautobot.com/projects/core/en/stable/installation/) for instructions on installing Nautobot.

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

## Notices

> Nautobot was initially developed as a fork of NetBox (v2.10.4).  NetBox was originally developed by Jeremy Stretch at DigitalOcean and the NetBox Community.
