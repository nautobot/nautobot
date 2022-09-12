# Location Types

+++ 1.4.0

Before defining individual Locations, you must first define the hierarchy of Location Types that you wish to use for the organization of your network. An example hierarchy might be `Building ← Floor ← Room`, but you might have more or fewer distinct types depending on your specific organizational requirements.

Each Location Type can define a set of "content types" that are permitted to associate to Locations of this type. For example, you might permit assigning Prefixes and VLAN Groups to an entire Building or Floor, but only allow Devices and Racks to be assigned to Rooms, never to a more abstract location. Doing so can help ensure consistency of your data.

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
