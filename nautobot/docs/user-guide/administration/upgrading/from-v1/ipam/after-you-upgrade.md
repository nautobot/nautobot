# After you Upgrade

This section includes various things to consider after you have successfully upgraded to Nautobot 2.0.

## Review any Cleanup or VRF Namespaces

> This may also apply to any "VRF Namespace" objects that were created, depending on your requirements on maintaining duplicate Prefix/IPAddress objects.

A priority of the upgrade process is to assert that no data will be lost. Due to the introduction of strict uniqueness constraints to disallow duplicate `Prefix`, `IPAddress`, and `VRF` objects within the same `Namespace`, depending on the nature of your data, you may have numerous "VRF" or "Cleanup" Namespaces that were automatically created by the upgrade process as described in the previous section.

### A word on Tenant affinity

A best effort is made to keep `Prefixes` and `IPAddresses` together in the same `Namespace` by shared attributes such as `Tenant`, but this is not always possible for various reasons such as numerous duplicates with identical or too-closely-similar criteria.

For more information on how this is done please see the section [Parenting affinity during the upgrade](./whats-changed.md#parenting-affinity-during-the-upgrade) above.

If you find that you have objects that were moved to the wrong Namespaces, you might try the next section on swapping Namespaces.

### Swapping Namespaces

If you need to swap a duplicate object into another `Namespace` (say "Global" and "Cleanup Namespace 1") where it conflicts with one in the desired `Namespace`, you can use this basic strategy to facilitate moving duplicate objects between `Namespaces` by using a temporary interstitial `Namespace`.

In this example we'll use three `Namespaces`. "Global", the `Namespace` in which you have duplicate objects that are found in "Cleanup Namespace 1", but you would like them to be the "Global" Namespace. We'll create a third Namespace called "Temporary" to act as the go-between to temporarily hold objects from one `Namespace` that we want to swap into another.

- First, Create a new  Namespace named "Temporary"
- Next, edit any desired objects you want to swap in objects from the "Global" Namespace and update their Namespace to "Temporary"
    - After performing this step, there should be no duplicates found in the "Global" Namespace
- Next, edit the duplicate objects you want moved in from "Cleanup Namespace 1" and set their Namespace to "Global".
    - After performing this step there should be no duplicates found in the "Cleanup Namespace 1" Namespace, as they've been moved to "Global"
- Finally, edit the original objects found in the "Temporary" Namespace that were moved from "Global" to "Temporary" and set their Namespace "Cleanup Namespace 1"
    - After performing this final step, the duplicate objects that were originally in the "Global" have now been swapped with those that were originally in the "Cleanup Namespace 1" Namespace.
    - There are no duplicate objects found in the "Temporary" Namespace. This Namespace can safely be deleted.
- Delete the "Temporary" Namespace when done.

## Merge duplicate IP Addresses

After upgrading to Nautobot v2.0 and running the data migrations necessary, duplicate `IPAddress` objects might exist in your database. We define duplicate `IPAddress` objects as those which have the same `host` attribute but exist in different `Namespaces`. If you have no use case to keep those duplicate `IPAddress` objects around, we recommend you to use this tool to de-duplicate those `IPAddress` objects and keep your database clean and manageable. But if you do have reasons to maintain duplicate `IPAddress` objects, this tool is not for you.

For more information, please see the [documentation on the Duplicate IP Address Merge Tool](../../../../feature-guides/ip-address-merge-tool.md).

## Delete duplicate objects

Because preventing data loss is prioritized, some objects that may have been required to be duplicates before may no longer be needed. For objects that weren't covered by the Duplicate IP Address Merge Tool, deleting objects might be your next course of action.

Some examples include:

- The same `IPAddress` assigned to multiple `Interfaces/VMInterfaces`. Where possible, a single `IPAddress` is now assigned leaving duplicate objects across other Namespaces to be potentially no longer necessary.
- `VRFs` that were used strictly for custom uniqueness boundaries with `enforce_unique` set to `True` may not necessarily be needed.

## Cleanup your config

Remove the now-deprecated settings from your `nautobot_config.py`:

- `DISABLE_PREFIX_LIST_HIERARCHY`
- `ENFORCE_GLOBAL_UNIQUE`
