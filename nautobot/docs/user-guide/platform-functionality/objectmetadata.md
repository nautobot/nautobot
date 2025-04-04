# Object Metadata

> metadata, noun: a set of data that describes and gives information about other data. -- Oxford Languages

Nautobot's _Metadata_ feature set allows users and administrators to define data _about_ the network data (database records, or even individual database fields) recorded in Nautobot. This is an advanced feature set, targeting the needs of Enterprise Data Governance teams that desire the ability to track information about the data that Nautobot itself contains. Some examples of metadata that you might use in your organization:

* Who is responsible for the accuracy of this data?
* When (after what date) can this data be deleted?
* What is the classification or risk level of this data?
* Which system of record is this data originally sourced from?
* When was this data last synced from that system into Nautobot? (Note that this is different than the `last_updated` field, as a sync may indicate "no change" since some previous sync date)

While there are several data model extensibility features in Nautobot -- like Custom Fields & Computed Fields -- that aim to expand the existing network data model to suit your organization's specific needs, note that the Object Metadata feature set is not intended to represent data about the network. Rather, Object Metadata is a platform-level feature that supports ancillary business process pertaining to the management of data within Nautobot. Still though, there are aspects that are likely to be useful to networking teams alike, for example, knowing who to talk to about correcting some device records, or identify the upstream system that is providing location data into Nautobot.

This Object Metadata feature is entirely optional and very flexible in terms of the type of information it can support. At present, all data stored by Object Metadata is read-only in the web UI and the intention is that metadata is managed by Nautobot system integrations, namely SSoTs and REST API integrations. Thus, it is up to the maintainer of such integrations to implement support for tracking Object Metadata, but full ORM and REST API access is available.

The following data models are parts of the feature set.

## The `MetadataType` model

This model defines a type of metadata that you will use for various data in your Nautobot system. Each of the examples given in the introduction to this document would be defined as a distinct `MetadataType`. Much like a `CustomField` record, this doesn't define a specific value for the data, so much as it defines the structure that that data will take. Each Metadata Type has a unique name, description, a data type that it describes (such as freeform text, integers, date/time, or choices from a defined list of text values), and a set of object types (content-types) that metadata of this type can be applied to.

Specific data types include:

* Text
* Integer
* Floating point
* Boolean
* Date
* Datetime
* URL
* JSON
* Markdown
* Contact or Team
* Selection (from predefined choices)
* Multiple Selection (from predefined choices)

Of note, the "Contact or Team" type option allows for linking to a defined contact or team record within Nautobot, where rich information like contact details will exist.

### The `MetadataChoice` model

If you define a Metadata Type with a `data_type` of "selection" or "multiple selection", you must also define one or more `MetadataChoice` records to define the set of values that can be selected from. Each choice applies to a specific Metadata Type, has a distinct `value`, and has a `weight` that can be set to influence the ordering among all choices within a given type.

## The `ObjectMetadata` model

Once you have defined appropriate `MetadataType` and `MetadataChoice` records, you can then define actual object metadata making use of these. Thus, the `ObjectMetadata` model is used to store the actual values of data, attached to Nautobot objects. The model itself is rather simple, it links to the `MetadataType` that should be used, the Nautobot object to which metadata is being attached, the actual metadata value, and optionally, a list of scoped model fields on the Nautobot object that the metadata applies, instead of the entire object by default.

On standard Nautobot object detail views (e.g. the detail page for an individual device), the "Metadata" tab can be used to view all `ObjectMetadata` records which apply to the given Nautobot object. Addtionally, users with the appropriate `ObjectMetadata` model permissions are able to view _all_ metadata records under the "Object Metadata" page in the Extensibility section pf the UI.

## Developer Usage

Currently, administrators may manage `MetadataType` definitions in the UI, however all `ObjectMetadata` records are managed programmatically, specifically targeting data integrations, like SSoT jobs. Developers of such integrations will be responsible for managing the metadata for the Nautobot data that their integration touches. Depending on the use case, the integration should either rely on administrator defined `MetadataType` (and `MetadataChoice`) records, or programmatically create them, before `ObjectMetadata`. This is a simple example, showing how a Text field and Contact can be linked to a device record.

```python
from django.contrib.contenttypes.models import ContentType
from nautobot.extras.models.contacts import Contact
from nautobot.extras.models.metadata import MetadataChoice, MetadataTypeDataTypeChoices, MetadataType, ObjectMetadata


#
# Create the MetadataType representing upstream CMDB data sources (this assumes the type does not already exist)
#

# Create the selection type
source_cmdb_type = MetadataType(
    name="Upstream CMDB",
    description="Describes the upstream system for some parts of the device inventory data",
    data_type=MetadataTypeDataTypeChoices.TYPE_SELECTION
)
source_cmdb_type.validated_save()
# Add the Device model so it can have this type of metadata attached to it
source_cmdb_type.content_types.add(ContentType.objects.get_for_model(Device))

# Create the selection choices for the type
choice_service_now = MetadataChoice(
    metadata_type=source_cmdb_type,
    value="SNOW"
)
choice_service_now.validated_save()
choice_remedy = MetadataChoice(
    metadata_type=source_cmdb_type,
    value="BMC Remedy"
)
choice_remedy.validated_save()


#
# Create the MetadataType representing the person that manages the record in the upstream CMDB
# (this again assumes that the type does not already exist)
#

# Create the contact type
source_cmdb_owner_type = MetadataType(
    name="Upstream data owner",
    description="Describes the person that owns the record in the upstream CMDB system",
    data_type=MetadataTypeDataTypeChoices.TYPE_CONTACT_TEAM
)
source_cmdb_owner_type.validated_save()
# Add the Device model so it can have this type of metadata attached to it
source_cmdb_owner_type.content_types.add(ContentType.objects.get_for_model(Device))


#
# Now ObjectMetadata records can be created
#

# Locate the device that ObjectMetadata instances will be attached to
device = Device.objects.first()

# Create the Source CMDB metadata record
source_cmdb_metadata = ObjectMetadata(
    metadata_type=source_cmdb_type,
    assigned_object=device,
    scoped_fields=["name", "location", "primary_ip4", "device_type"]  # Only these fields are sourced from the upstream CMDB
)
source_cmdb_metadata.value = choice_service_now.value  # ObjectMetadata data values are always set and retrieved via the `value` property
source_cmdb_metadata.validated_save()

# Locate (or create) the Contact for the upstream data owner
owner = Contact.objects.get(name="John Smith")

# Create the Source CMDB Data Owner metadata record
source_cmdb_owner_metadata = ObjectMetadata(
    metadata_type=source_cmdb_owner_type,
    assigned_object=device,
    contact=owner
)
source_cmdb_owner_metadata.validated_save()
```
