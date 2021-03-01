# Relationships
Sometimes it is desirable to create a new kind of relationship between one (or more) objects in your source of truth to reflect business logic or other relationships that may be useful to you but that haven't been defined. This is where the Relationships feature comes in: like defining custom fields to hold atributes specific to your use cases, relationships define specific links between objects that might be specific to your network or data.

## Relationship Types

* Many to Many -  where both sides of the relationship connection can be connected to multiple objects. e.g. VLANs can be connected to multiple devices and devices will have multiple VLANs.
* One to Many - where one side of the connection can only have one object. e.g. where a controller has many supplicants like FEX and parent switch. A FEX can be uplinked to one parent switch (in most cases), but the parent switch can have many FEX. 
* One to One - where there can be only one object on either side of the relationship. e.g. a primary VLAN for a site or device. It doesn't make sense to have more than 1 'primary' vlan for a device.

## Relationship Filters

Filters can be defined to restrict the type or selection of objects for either side of the connection. From the FEX example above, you can restrict the FEX side of the connection to only of devices with the FEX role, and restrict the controller side to only devices with Controller roles.

## Relationship Labels

Realtionship connections can be labeled with a friendly name so that when they are displayed in the GUI, they will have a more descriptive or friendly name. From the VLANs example above, you might label the relationship so that on the VLANs side the connection appears as 'Devices' and on the Device side the connection appears as 'VLANs'. 

### Options

It's also possible to hide the relationship from either side of the connection. 

# Creating new Relationships

Relationships can be added through the UI under Extensibility > Relationships

Each relationship must have a Name, Slug, Type, Source Object(s), and Destination Object(s). Optionally, Source Labels, Source Filters, Destination Labels, and Destination Filters may be configured. 

Once a new relationship is added, the Relationship configuration section will appear under that device in the UI edit screen. Once a specific instance relationship has been configured for the object, that new relationship will appear under the Relationship section heading when viewing the object.


# API

Relationships are fully supported by the API. 

## Adding a new type of Relationship

The API endpoint for relationship creation is `/extras/relationships/`

From our many to many example above, we would use the following data to create the relationship. 

```json
{"name": "Device VLANs",
"slug": "device-vlans",
"type": "many-to-many",
"source_type": "ipam.vlan",
"destination_type": "dcim.device"}
```

## Configuring the Relationship between Objects

Configuring the relationship is similarly easy. Send a request to `/extras/relationship-associations/` like the following:

Here we specify the IDs of each object. We specify the UUID of each object in their respective fields.

```json
{"relationship": "bff38197-26ed-4bbd-b637-3e688acf361c",
"source_type": "ipam.vlan",
"source_id": "89588629-2d70-45ce-9e20-f6b159b41b0c",
"destination_type": "dcim.device",
"destination_id": "6e8e72da-ce6e-468d-90f9-b4473d449db7"}
```

In the relationship field, you may specify a dictionary of object attributes instead:

```json
{"relationship": {"slug": "device-vlans"},
"source_type": "ipam.vlan",
"source_id": "89588629-2d70-45ce-9e20-f6b159b41b0c",
"destination_type": "dcim.device",
"destination_id": "6e8e72da-ce6e-468d-90f9-b4473d449db7"}
```