# DCIM

## Replace Site and Region with Location Model

`Site` and `Region` Models are replaced by `Site` and `Region` `LocationTypes` and `Locations`. Your models and data that are associated with `Site` or `Region` via ForeignKey or ManyToMany relationships are now required to be migrated to `Locations`. Please go [here](region-and-site-to-location.md) for a comprehensive migration guide on how to migrate your data from `Site` and `Region` to `Location` and `LocationType`.
