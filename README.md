# Nautobot

<!-- pyml disable-num-lines 3 no-inline-html,proper-names -->
<p align="center">
  <img src="https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/nautobot_logo.svg" alt="Nautobot logo" width="350">
</p>

Nautobot is the open source **Network Source of Truth** and **Network Automation Platform** for enterprises operating complex networks at scale.

[Network to Code](https://networktocode.com/) is the sponsor and official steward of Nautobot.

Nautobot is used by thousands of organizations around the world, including NVIDIA, Intel, Cox, Hughes, Chevron, BPCE, TNS, Arizona State University, the U.S. Department of Defense, and many others.

<!-- pyml disable-next-line proper-names -->
Try Nautobot at [demo.nautobot.com](https://demo.nautobot.com), a live instance of the open source platform with several open source Apps installed.

## What Nautobot Is

### Network Source of Truth

Nautobot's data models define the *intended state* of your network: locations and racks, devices and interfaces, IP address space, VLANs, circuits, cables, and more.

Beyond the out-of-the-box data models, Nautobot provides flexible ways to extend and validate the source of truth. Custom fields, user-defined relationships, and data validation rules allow teams to represent their own network standards, processes, and requirements directly in Nautobot.

### Network Automation Platform

Nautobot also includes a built-in Automation Engine for running network automation directly against the data in the source of truth.

Nautobot Jobs execute against your network data on demand or on a schedule, with permissions, logging, and approvals built in. REST and GraphQL APIs, webhooks, and native Git integration connect Nautobot to the rest of your tooling.

The Nautobot App framework extends the platform with new models, APIs, UI, and Jobs while inheriting authentication, permissions, change logging, and everything else the core platform already provides.

## Nautobot Apps and Editions

**Open source Apps** include [Golden Configuration](https://docs.nautobot.com/projects/golden-config/en/latest/), [Device Onboarding](https://docs.nautobot.com/projects/device-onboarding/en/latest/), [Single Source of Truth](https://docs.nautobot.com/projects/ssot/en/latest/), [Device Lifecycle Management](https://github.com/nautobot/nautobot-app-device-lifecycle-mgmt), and [Firewall Models](https://docs.nautobot.com/projects/firewall-models/en/latest/). Find more in the [Apps documentation](https://docs.nautobot.com).

<!-- pyml disable-next-line proper-names -->
**Commercial editions** from Network to Code build on the same open source Nautobot core. [Nautobot Professional](https://networktocode.com/nautobot/nautobot-professional/) adds supported capabilities for network discovery, onboarding, and operations. [Nautobot Enterprise](https://networktocode.com/nautobot/nautobot-enterprise/) extends the platform with additional Apps for compliance, OS upgrades, reporting, automation, and AI. [Nautobot Cloud](https://networktocode.com/nautobot/nautobot-cloud/) delivers the Enterprise platform as a fully managed SaaS offering. See [networktocode.com/nautobot](https://networktocode.com/nautobot/) to compare editions.

The complete documentation for Nautobot can be found at [Read the Docs](https://docs.nautobot.com/).

Questions? Comments? Start by perusing our [GitHub discussions](https://github.com/nautobot/nautobot/discussions) for the topic you have in mind, or join the `#nautobot` channel on [Network to Code's Slack community](https://slack.networktocode.com/)!

## Build Status

| Branch      | Status |
|-------------|------------|
| **[main](https://github.com/nautobot/nautobot/tree/main)** | [![Build Status](https://github.com/nautobot/nautobot/actions/workflows/ci_integration.yml/badge.svg?branch=main)](https://github.com/nautobot/nautobot/actions/workflows/ci_integration.yml) |
| **[develop](https://github.com/nautobot/nautobot/tree/develop)** | [![Build Status](https://github.com/nautobot/nautobot/actions/workflows/ci_integration.yml/badge.svg?branch=develop)](https://github.com/nautobot/nautobot/actions/workflows/ci_integration.yml) |
| **[next](https://github.com/nautobot/nautobot/tree/next)** | [![Build Status](https://github.com/nautobot/nautobot/actions/workflows/ci_integration.yml/badge.svg?branch=next)](https://github.com/nautobot/nautobot/actions/workflows/ci_integration.yml) |

## Screenshots

![Gif of main page](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/media/nautobot_mainpage.gif?raw=true "Main page")

---

![Gif of config contexts](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/media/nautobot_config_context.gif?raw=true "Config Contexts")

---

![Gif of prefix hierarchy](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/media/nautobot_prefix_hierarchy.gif?raw=true "Prefix hierarchy")

---

![Gif of GraphQL](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/media/nautobot_graphql.gif?raw=true "GraphQL API")

---

![Gif of Modes](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/media/nautobot_modes.gif?raw=true "Modes")

## Nautobot Apps and Extensibility

Nautobot offers the ability to customize your setup to better align with your direct business needs. It does so through the use of various Apps that have been developed for network automation, and are designed to be used in environments where needed.

There are many Apps available within the Nautobot Apps ecosystem. The below screenshots are an example of some popular ones that are currently available.

### App Screenshots

#### Golden Config

![Gif of golden config](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/media/nautobot_golden_config.gif?raw=true "Golden config")

#### Device Lifecycle Management

![Gif of DLM](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/media/nautobot_device_lifecycle_management.gif?raw=true "Device Lifecycle Management")

#### ChatOps

![Gif of chatops](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/media/nautobot_chatops.gif?raw=true "ChatOps")

## Installation

Please see [the documentation](https://docs.nautobot.com/projects/core/en/stable/user-guide/administration/installation/) for instructions on installing Nautobot.

## Application Stack

Below is a simplified overview of the Nautobot application stack for reference:

![Application stack diagram](https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/media/nautobot_application_stack_high_level.png "Application stack diagram")

## Providing Feedback

The best platform for general feedback, assistance, and other discussion is our [GitHub discussions](https://github.com/nautobot/nautobot/discussions). To report a bug or request a specific feature, please open a GitHub issue using the [appropriate template](https://github.com/nautobot/nautobot/issues/new/choose).

If you are interested in contributing to the development of Nautobot, please read our [contributing guide](https://docs.nautobot.com/projects/core/en/stable/development/core/#contributing) prior to beginning any work.

## Related projects

Please check out [the GitHub `nautobot` topic](https://github.com/topics/nautobot) for a list of relevant community projects.

## Notices

> Nautobot was initially developed as a fork of NetBox (v2.10.4).  NetBox was originally developed by Jeremy Stretch at DigitalOcean and the NetBox Community.
