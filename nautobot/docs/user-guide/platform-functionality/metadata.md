# Metadata

> metadata, noun: a set of data that describes and gives information about other data. -- Oxford Languages

Nautobot's _Metadata_ feature set allows users and administrators to define data _about_ the network data (database records, or even individual database fields) recorded in Nautobot. Some examples of metadata that you might use in your organization:

* Which system of record is this data originally sourced from?
* When was this data last synced from that system into Nautobot? (Note that this is different than the `last_updated` field, as a sync may indicate "no change" since some previous sync date)
* Who is responsible for the accuracy of this data?
* When (after what date) can this data be deleted?

At a first glance, it might seem that Metadata is very similar to [Custom Fields](customfield.md), and to a certain extent this is true - the two features have a lot in common from a technical standpoint. The key conceptual distinction that should guide you is that Custom Fields are for _additional network data_ not accounted for in the base data models, while Metadata is for _information about your network data_. Additionally, while Custom Fields apply to a record as a whole (effectively becoming additional database fields), Metadata can be scoped to a record or to an individual field(s) within that record.

The following data models are parts of the Metadata feature set.

## The `MetadataType` model

This model defines a type of metadata that you will use for various data in your Nautobot system. Each of the examples given in the introduction to this document would be defined as a distinct `MetadataType`. Much like a `CustomField` record, this doesn't define a specific value for the data, so much as it defines the structure that that data will take. Each Metadata Type has a unique name, description, a data type that it describes (such as freeform text, integers, date/time, or choices from a defined list of text values), and a set of object types (content-types) that metadata of this type can be applied to.

### The `MetadataChoice` model

If you define a Metadata Type with a `data_type` of "selection" or "multiple selection", you must also define one or more `MetadataChoice` records to define the set of values that can be selected from. Each choice applies to a specific Metadata Type, has a distinct `value`, and has a `weight` that can be set to influence the ordering among all choices within a given type.

### The `ObjectMetadata` model

Once you have defined appropriate `MetadataType` and `MetadataChoice` records, you can then define actual object metadata making use of these.

TODO
