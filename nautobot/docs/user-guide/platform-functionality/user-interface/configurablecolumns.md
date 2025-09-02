# Configurable Table Columns

In Nautobot, you can choose which columns appear in any list view table. To optimize performance, Nautobot attempts to automatically adjust database queries to retrieve only the requested table columns, rather than always fetching every possible field. This targeted approach generally results in faster page loads compared to a “fetch everything” query.

However, your column choices directly affect performance. Two users viewing the same table can experience very different load times if their selected columns require different amounts of data processing, especially when those columns involve additional queries.

!!! tip "Enable only the columns you truly need for your workflow."

Why are some columns slower? On a technical level, columns that pull data from related tables are more resource-intensive. Here is a performance ranking (from fastest to slowest):

- Same-table data — simple numeric or textual values, generally editable directly on the form (e.g., `serial number` on Devices, Custom Fields on any model).
- Foreign key fields — directly related single objects from another table, generally selectable from a dropdown (e.g., Location on Devices).
- Many-to-many fields — a set of related objects, generally selectable from a multi-select list (e.g., Tags on Devices, Locations on Prefixes).
- Nested or layered lookups — indirect lookups that involve traversing multiple levels of foreign keys or many-to-many fields (e.g., Locations on Rack Reservations, Device on Interfaces belonging to a nested series of Modules, custom Relationships).
- Calculated values — values that are not stored directly in the database but instead are calculated dynamically at display time (e.g. Computed Fields, `utilization` on Prefixes and Racks).

These guidelines won’t cover every scenario, but they provide a quick way to estimate the performance impact of enabling a given column.
