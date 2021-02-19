![Nautobot](docs/nautobot_logo.svg "Nautobot logo")

Nautobot is an IP address management (IPAM) and data center infrastructure
management (DCIM) tool. Initially conceived by the network engineering team at
[DigitalOcean](https://www.digitalocean.com/), Nautobot was developed specifically
to address the needs of network and infrastructure engineers. It is intended to
function as a domain-specific source of truth for network operations.

Nautobot runs as a web application atop the [Django](https://www.djangoproject.com/)
Python framework with a [PostgreSQL](https://www.postgresql.org/) database. For a
complete list of requirements, see `requirements.txt`. The code is available [on GitHub](https://github.com/nautobot/nautobot).

The complete documentation for Nautobot can be found at [Read the Docs](https://nautobot.readthedocs.io/en/stable/).

Questions? Comments? Start by perusing our [GitHub discussions](https://github.com/nautobot/nautobot/discussions) for the topic you have in mind,
or join us in the **#nautobot** Slack channel on [NetworkToCode](https://networktocode.slack.com)!

### Build Status

|             | status |
|-------------|------------|
| **master** | ![Build status](https://github.com/nautobot/nautobot/workflows/CI/badge.svg?branch=master) |
| **develop** | ![Build status](https://github.com/nautobot/nautobot/workflows/CI/badge.svg?branch=develop) |

### Screenshots

![Screenshot of main page](docs/media/screenshot1.png "Main page")

---

![Screenshot of rack elevation](docs/media/screenshot2.png "Rack elevation")

---

![Screenshot of prefix hierarchy](docs/media/screenshot3.png "Prefix hierarchy")

## Installation

Please see [the documentation](https://nautobot.readthedocs.io/en/stable/) for
instructions on installing Nautobot. To upgrade Nautobot, please download the
[latest release](https://github.com/nautobot/nautobot/releases) and
run `upgrade.sh`.

## Providing Feedback

The best platform for general feedback, assistance, and other discussion is our
[GitHub discussions](https://github.com/nautobot/nautobot/discussions).
To report a bug or request a specific feature, please open a GitHub issue using
the [appropriate template](https://github.com/nautobot/nautobot/issues/new/choose).

If you are interested in contributing to the development of Nautobot, please read
our [contributing guide](CONTRIBUTING.md) prior to beginning any work.

## Related projects

Please see [our wiki](https://github.com/nautobot/nautobot/wiki/Community-Contributions)
for a list of relevant community projects.
