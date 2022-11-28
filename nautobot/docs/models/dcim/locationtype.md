# Location Types

+++ 1.4.0

Before defining individual Locations, you must first define the hierarchy of Location Types that you wish to use for the organization of your network. An example hierarchy might be `Building ← Floor ← Room`, but you might have more or fewer distinct types depending on your specific organizational requirements.

Each Location Type can define a set of "content types" that are permitted to associate to Locations of this type. For example, you might permit assigning Prefixes and VLAN Groups to an entire Building or Floor, but only allow Devices and Racks to be assigned to Rooms, never to a more abstract location. Doing so can help ensure consistency of your data.

+++ 1.5.0
    Location Types can now be marked as `nestable`. When this flag is set, Locations of this type may nest within one another, allowing for variable-depth hierarchies of Locations and reducing the number of distinct Location Types you may need to define. For example, with two Location Types, "Building Group" and "Building", by flagging "Building Group" as nestable, you could model the following hierarchy of Locations:

    * Main Campus (Building Group)
        * West Campus (Building Group)
            * Building A (Building)
            * Building B (Building)
        * East Campus (Building Group)
            * Building C (Building)
            * Building D (Building)
        * South Campus (Building Group)
            * Western South Campus (Building Group)
                * Building G (Building)
            * Eastern South Campus (Building Group)
                * Building H (Building)
    * Satellite Campus (Building Group)
        * Building Z (Building)

!!! tip
    Although it is possible to define a "tree" of Location Types with multiple "branches", in the majority of cases doing so adds more unnecessary complexity than it's worth. Consider the following hypothetical Location Type tree:

    ```
    Branch Office
      ↳ Branch Floor
          ↳ Branch Floor Room
      ↳ Branch Basement
          ↳ Branch Basement Room
    Headquarters
      ↳ Headquarters Floor
          ↳ Headquarters Floor Room
      ↳ Headquarters Basement
          ↳ Headquarters Basement Room
    ```

    This would complicate your life significantly when constructing queries, filters, and so forth to actually work with your data - for example, if you wanted a list of all Prefixes that are mapped to floors rather than individual rooms, you would now need to construct a query for Prefixes that are mapped to (a `Branch Floor` OR a `Headquarters Floor` OR a `Branch Basement` OR a `Headquarters Basement`). In most cases you would be better served with a far simpler "linear" sequence of Location Types, such as `Building ← Floor ← Room`; you could then use tags or custom fields to distinguish whether a given Building is a Branch Office or a Headquarters, if that distinction is even important to your network model.
