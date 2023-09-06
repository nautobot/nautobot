# Node.js Configuration

This document provides instructions on how to configure Node.js for builds and rebuilds of the 2.x Nautobot UI.

## Adding an Alternate `npm` registry

By configuring `npm` with an alternate registry, you can have more control over where `npm` looks for packages and how it resolves dependencies. There are several reasons why you might want to add an alternate npm registry such as:

1. **Network Restrictions**: In certain network environments, such as corporate networks or restricted networks, access to the default [npm registry](https://registry.npmjs.org) might be blocked. This can prevent you from installing or updating packages. By adding an alternate registry, which is accessible from your network, you can bypass these restrictions and ensure seamless package installations.
2. **Package Management Control**: Hosting your own npm registry gives you greater control over the packages used in your project. You can curate a set of packages that are tailored to your organization's needs, ensuring consistency and stability across your projects. Additionally, by hosting your own registry, you can enforce stricter version controls and ensure that only approved packages are used.

To add an alternate `npm` registry to your Nautobot installation, follow these steps:

1. Open your terminal or command prompt.
2. Navigate to the `nautobot/ui` directory.
3. Use the `npm config set` command to set the registry URL. Replace REGISTRY_URL with the URL of the alternate registry you want to use.

    ```shell
    npm config set registry REGISTRY_URL
    ```

    For example, if you want to configure npm to use the npm public registry as the fallback registry, you can use the following command:

    ```shell
    npm config set registry https://registry.npmjs.org
    ```

4. Verify the configuration by running the `npm config list` command. This will display the current `npm` configuration, including the registry URL.

    ```shell
    npm config list
