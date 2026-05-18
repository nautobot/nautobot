# Locations

To locate network information more precisely than a Site defines, you can define a hierarchy of Locations within each Site. Data objects such as devices, prefixes, VLAN groups, etc. can thus be mapped or assigned to a specific building, wing, floor, room, etc. as appropriate to your needs.

Once you have defined the hierarchy of Location Types that you wish to use, you can then define Locations. Any "top-level" Locations (those whose Location Type has no parent) belong directly to a Site, while "child" Locations belong to their immediate parent Location, rather than to the Site as a whole.

!!! info
    At present, Locations fill the conceptual space between the more abstract Region and Site models and the more concrete Rack Group model. In a future Nautobot release, some or all of these other models may be collapsed into Locations. That is to say, in the future you might not deal with Regions and Sites as distinct models, but instead your Location Type hierarchy might include these higher-level categories, becoming something like Country ← City ← Site ← Building ← Floor ← Room.

Much like Sites, each Location must be assigned a name and operational [`status`](../../platform-functionality/status.md). The same default operational statuses are defined for Locations as for Sites, but as always, you can customize these to suit your needs. Locations can also be assigned to a tenant.

+++ 2.0.0
    Location now supports all properties previously present on the Site model, including the `asn`, `comments`, `contact_email` `contact_name`, `contact_phone`, `facility`, `latitude`, `longitude`, `physical_address`, `shipping_address` and `time_zone` fields.

## Location List View and Hierarchy Display

The default (unfiltered) Location list view (`/dcim/locations/`) includes display elements to indicate the hierarchy or nesting of child Locations under their parent Locations, as this is useful information to be aware of. However, in most cases, applying sorting, filtering, or search to this list view will **remove** the hierarchy from the display, as it would be misleading or outright confusing when not showing the full list of Locations in context.

+++ 3.1.0 "Added exemptions for specific filters"

There are a small set of filters which, when applied individually or in combination, *do not* remove the hierarchy display, because these filters preserve the hierarchy of the filtered set of Locations. Examples of such filters include `max_depth` and `subtree`. The "default filter" described in the next section, for much the same reason, also does not remove indentation when in effect.

!!! tip
    The hierarchy-preserving filters only preserve the hierarchy display if they are the *only* filter(s) applied to the view. Adding search, sorting, or any additional filters will still hide the hierarchy as normal. In other words:

    * `/dcim/locations/max_depth=2` -- hierarchy shown
    * `/dcim/locations/max_depth=2&sort=status` -- hierarchy hidden due to sorting
    * `/dcim/locations/max_depth=2&status=Active` -- hierarchy hidden due to additional filtering

## Location List View Configuration

+++ 3.1.0 "Added configuration parameter"

To improve performance of the initial rendering of the Location list view when a large number of records and/or a deep hierarchy of records are present, an administrator can configure the setting [`LOCATION_LIST_DEFAULT_MAX_DEPTH`](../../administration/configuration/settings.md#location_list_default_max_depth). When enabled, this setting effectively applies a default `max_depth` filter (similar to a default [saved view](../../platform-functionality/user-interface/savedview.md) for all users when initially accessing the Location list view, such as from the navigation menu.

When this setting is configured to a positive number, the default Location list view will only display Locations down to a certain depth. For example, a value of `1` (one) will only display root Locations (those with no higher-level parent), a value of `2` (two) will display root Locations and their immediate children, but not their grandchildren, and so forth. Users can then either apply an appropriate filter of their choice to narrow the scope of the list view further, or simply select the relevant parent Location and navigate to its "detail" view to see and interact with any descendant Locations it contains.

This default filter only applies when initially accessing the Location list view with no explicit filters or sorting applied; applying any sorting or specifying other filter(s) to the view will bypass the default filter and display the full set of records as selected by the user-specified filter.
