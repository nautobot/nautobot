# Configurable Columns

In Nautobot, you can choose which columns appear in any list view table. To optimize performance, Nautobot generates database queries only for the columns you select, rather than always fetching every possible field. This targeted approach generally results in faster page loads compared to a “fetch everything” query.

However, your column choices directly affect performance. Two users viewing the same table can experience very different load times if their selected columns require different amounts of data processing, especially when those columns involve additional queries.

!!! info
    Enable only the columns you truly need for your workflow.

Why are some columns slower? On a technical level, columns that pull data from related tables are more resource-intensive. Here is a performance ranking (from fastest to slowest):

- Table data — editable directly on the form (e.g., a serial number on a device).
- Foreign key fields — generally selectable from a dropdown (e.g., Location on Device).
- Many-to-many fields — generally selectable from a multi-select list (e.g., Tag on Device).
- Nested or layered lookups — lookups that involve foreign keys or many-to-many fields with multiple levels of nesting  (e.g., Locations on Rack Reservation).

These guidelines won’t cover every scenario, but they provide a quick way to estimate the performance impact of enabling a given column.