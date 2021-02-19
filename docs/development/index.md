# Nautobot Development

Nautobot is maintained as a [GitHub project](https://github.com/nautobot/nautobot) under the Apache 2 license. Users are encouraged to submit GitHub issues for feature requests and bug reports, however we are very selective about pull requests. Please see the `CONTRIBUTING` guide for more direction on contributing to Nautobot.

## Communication

Communication among developers should always occur via public channels:

* [GitHub issues](https://github.com/nautobot/nautobot/issues) - All feature requests, bug reports, and other substantial changes to the code base **must** be documented in an issue.
* [GitHub discussions](https://github.com/nautobot/nautobot/discussions) - The preferred forum for general discussion and support issues. Ideal for shaping a feature request prior to submitting an issue.
* [#nautobot on NetworkToCode](http://slack.networktocode.com/) - Good for quick chats. Avoid any discussion that might need to be referenced later on, as the chat history is not retained long.

## Governance

Nautobot follows the [benevolent dictator](http://oss-watch.ac.uk/resources/benevolentdictatorgovernancemodel) model of governance, with [Jeremy Stretch](https://github.com/jeremystretch) ultimately responsible for all changes to the code base. While community contributions are welcomed and encouraged, the lead maintainer's primary role is to ensure the project's long-term maintainability and continued focus on its primary functions (in other words, avoid scope creep).

## Project Structure

All development of the current Nautobot release occurs in the `develop` branch; releases are packaged from the `master` branch. The `master` branch should _always_ represent the current stable release in its entirety, such that installing Nautobot by either downloading a packaged release or cloning the `master` branch provides the same code base.

Nautobot components are arranged into functional subsections called _apps_ (a carryover from Django vernacular). Each app holds the models, views, and templates relevant to a particular function:

* `circuits`: Communications circuits and providers (not to be confused with power circuits)
* `dcim`: Datacenter infrastructure management (sites, racks, and devices)
* `extras`: Additional features not considered part of the core data model
* `ipam`: IP address management (VRFs, prefixes, IP addresses, and VLANs)
* `tenancy`: Tenants (such as customers) to which Nautobot objects may be assigned
* `users`: Authentication and user preferences
* `utilities`: Resources which are not user-facing (extendable classes, etc.)
* `virtualization`: Virtual machines and clusters
