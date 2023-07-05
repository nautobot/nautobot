# Duplicate IP Address Merge Post Migration Tool

In order to satisfy new uniqueness constraints, upgrading from Nautobot v1.x to v2.0 can create duplicate `IPAddress` objects in the existing database. This tool is designated to help users to reduce unnecessary duplicate `IPAddress` objects by merging them into a single IP Address with all the desired attributes.

## When to use this tool

After upgrading to Nautobot v2.0 and running the data migrations necessary, duplicate `IPAddress` objects might exist in your database. We define duplicate `IPAddress` objects as those which have the same `host` attribute but exist in different `namespaces`. If you have no use case to keep those duplicate `IPAddress` objects around, we recommend you to use this tool to de-duplicate those `IPAddress` objects and keep your database clean and manageable. But if you do have reasons to maintain duplicate `IPAddress` objects, this tool is not for you.

!!! important
    One of the possible reasons to maintain duplicate `IPAddress` objects can be the following:
    1. You have use cases for duplicate `IPAddress` objects with different `nat_inside` attributes. Only one `nat_inside` IP address can be assigned per object.

## How to access this tool

To use this tool:

1. Go to the `IPAM` tab on the navigation menu and click on `IP Addresses`. This will take you to the list view of all `IPAddress` objects that exist in the database.
2. On the top right of the page, you will find a group of buttons representing different available actions and the first one should be `Find and Merge Duplicate IPs`.
3. Click on that button to access the tool.

![Homepage Navigation](./images/ip-address-merge-tool/navigation.png)

![Merge Button](./images/ip-address-merge-tool/ip_merge_button.png)

## How it works

1. All of the selected `IPAddress` objects will be deleted and a new `IPAddress` object with all of the desired attributes will be created.
2. If you de-select all other duplicates and attempt to merge, nothing will happen (the operation is a no-op) and the object will be skipped over as if you had clicked the `Skip and Go to the Next Duplicate` button.
3. All `Interface` assignments of the deleted `IPAddress` objects will be automatically updated to reference the newly created `IPAddress` object.
4. All `VMInterface` assignments of the deleted `IPAddress` objects will be automatically updated to reference the newly created `IPAddress` object.
5. The newly created `IPAddress` object will be added to `IPAddress` assignments of related `Service` objects.
6. `primary_ip4/primary_ip6` of `Devices` that are referencing the deleted `IPAddress` objects will be automatically updated to reference the newly created `IPAddress` object.

## How to use this tool

Clicking on the `Find and Merge Duplicate IPs` button will automatically query your database for duplicate `IPAddress` objects and group them by their respective `host` values. The tool will present the duplicate `IPAddress` objects in order from lowest to highest `mask_length` values.

![IP Address Merge View](./images/ip-address-merge-tool/merge_view.png)

### Merging All Duplicate IP Addresses Presented with Desired Attributes

Once the duplicate `IPAddress` objects are found, the tool will put them in a table ordered by their `mask_length` and the table presents all their editable attributes. Select the desired attribute values for the eventually merged `IPAddress` and click on the `Merge and Go to the Next Duplicate` button to collapse/delete all the `IPAddress` objects presented into a new `IPAddress` with all the attributes you selected. This will also take you to a page of the next available duplicate `IPAddress` objects with a different `host` value.

![Merging All Duplicate IPs](./images/ip-address-merge-tool/merge_button.png)

### Merging Only Some Duplicate IP Addresses Presented with Desired Attributes

If you want to keep some of the `IPAddress` objects around and merge the others, you can de-select the checkboxes in the first column correpsonding to the `IPAddress` objects you do not wish to merge, select the desired attributes and click on the `Merge and Go to the Next Duplicate` button. This operation will only collapse/delete the `IPAddress` objects that have their checkboxes selected in the first column.

![Merging Some Duplicate IPs](./images/ip-address-merge-tool/unselect_ips.png)

!!! note
    Unchecking the checkbox of the corresponding `IP Address` means that the attributes of the `IP Addresses` will not be available for selection. Moreover, If there are not at least two checkboxes checked, clicking on the `Merge and Go to the Next Duplicate` button will cause the IP address to be skipped and not be merged.

### Skip Merging All Duplicate IP Addresses Presented

If you decide that these `IPAddress` objects presented do not need to be merged, you can click on the `Skip and Go to the Next Duplicate` button to skip merging these `IPAddress` objects and go to the next set of duplicate `IPAddress` objects with a different `host` value.

![Skip Merging Duplicate IPs](./images/ip-address-merge-tool/skip_button.png)

### No more Duplicate IP Addresses

If you have gone through all duplicate `IPAddress` objects, you will be taken back to the list view of `IPAddress` objects with a message indicating that `No additional duplicate IPs found.`.

![No More Duplicate IPs](./images/ip-address-merge-tool/no_more_dup_ips.png)
