# User Guide Overview

Welcome to the Nautobot User Guide! The User Guide is designed to help you setup, use, and operate your Nautobot installation. 

There are four main headings within the guide: 

- **Administration**: Go here for [installation](./administration/installation/index.md), [migration](./administration/migration/migrating-from-netbox.md), [configuration](./administration/configuration/index.md) and [upgrade instructions](./administration/upgrading/upgrading.md).
- **Feature Guides**: Walk through these guides if you are a [new user to Nautobot](./feature-guides/getting-started/index.md) and wondering how to perform common tasks in the Web UI. 
- **Core Data Model**: Read about all the Nautobot [data models](./core-data-model/overview/introduction.md) to better understand what information you can store in Nautobot.
- **Platform Functionality**: Explore this area for deep-dives on specific Nautobot functionality such as [Jobs](./platform-functionality/jobs/index.md), [APIs](./platform-functionality/rest-api/overview.md) or [Git repository integration](./platform-functionality/gitrepository.md).

## Quick Links

!!! Tip
    Are a **new user** looking to get started with Nautobot?

<!-- pyml disable-num-lines 30 no-inline-html,proper-names -->
<div class="grid cards" markdown>

- :material-cloud-download:{ .lg .middle } **Installing Nautobot**

    ---
    Get up and running with a [Nautobot install](./administration/installation/index.md) on your own Linux Platform or in a Docker environment.


- :material-play-network:{ .lg .middle } **Using Nautobot**

    ---
    Dive into [how to use Nautobot](./feature-guides/getting-started/index.md) and the key components of the core web interface.

- :material-transition-masked:{ .lg .middle } **Migrating with Nautobot**

    ---
    Dig into how you can [migrate from NetBox](./administration/migration/migrating-from-netbox.md) to Nautobot seamlessly. 
</div>

!!! Tip
    Are you an **existing User** with Nautobot looking to dig deeper?

<!-- pyml disable-num-lines 30 no-inline-html,proper-names -->
<div class="grid cards" markdown>

- :material-api:{ .lg .middle } **Nautobot APIs**

    ---
    Check out the [REST API documentation](./platform-functionality/rest-api/overview.md) covering both basic features and advanced use cases. 
    
    Are you looking for [GraphQL](./platform-functionality/graphql.md) APIs instead? If you are new to GraphQL, you can also read the [Nautobot GraphQL User Guide](./feature-guides/graphql.md)

- :material-briefcase:{ .lg .middle } **Nautobot Jobs**

    ---
    Looking to use Nautobot to host your custom coding logic on demand? 
    
    Check out [Nautobot Jobs](./platform-functionality/jobs/index.md) which can also leverage your Nautobot data to automate using your Python code. 

- :material-fire:{ .lg .middle } **Nautobot & NAPALM**

    ---
    Are you curious how [NAPALM integrates with Nautobot?](./platform-functionality/napalm.md) Learn how you can use NAPALM functionality to fetch live data from network devices.

</div>