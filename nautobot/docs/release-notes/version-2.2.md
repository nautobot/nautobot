<!-- markdownlint-disable MD024 -->

# Nautobot v2.2

This document describes all new features and changes in Nautobot 2.2.

## Release Overview

### Added

#### Contact and Team Models ([#230](https://github.com/nautobot/nautobot/issues/230))

Contact and Team are models that represent an individual and a group of individuals who can be linked to an object. Contacts and teams store the necessary information (name, phone number, email, and address) to uniquely identify and contact them. They are added to track ownerships of organizational entities and to manage resources more efficiently in Nautobot. Check out the documentation for [contact](../user-guide/core-data-model/extras/contact.md) and [team](../user-guide/core-data-model/extras/team.md). There is also a [user guide](../user-guide/feature-guides/contact-and-team.md) available on how to utilize these models.
