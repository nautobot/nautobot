# Tags

Tags are user-defined labels which can be applied to a variety of objects within Nautobot. They can be used to establish dimensions of organization beyond the relationships built into Nautobot. For example, you might create a tag to identify a particular ownership or condition across several types of objects.

+++ 1.3.0
    When created, a `Tag` can be associated to one or more model content-types using a many-to-many relationship. The tag will then apply only to models belonging to those associated content-types.

Each tag has a name, label, color, content-types and a URL-friendly slug. For example, the slug for a tag named "Dunder Mifflin, Inc." would be `dunder-mifflin-inc`. The slug is generated automatically and makes tags easier to work with as URL parameters. Each tag can also be assigned a description indicating its purpose.

Objects can be filtered by the tags they have applied. For example, the following API request will retrieve all devices tagged as "monitored":

```no-highlight
GET /api/dcim/devices/?tag=monitored
```

The `tag` filter can be specified multiple times to match only objects which have _all_ of the specified tags assigned:

```no-highlight
GET /api/dcim/devices/?tag=monitored&tag=deprecated
```

Tags can also be created in the ORM or REST API of Nautobot. The following HEX color values in the table below correspond to the dropdown selection when building tags using the UI. Any HEX color value can be used with the ORM or REST API, but a non-standard color will cause some inconsistency when editing the tag via the UI.

| Color | HEX value |
| :------------ | :------------ |
| Dark Red | aa1409 |
| Red | f44336 |
| Pink | e91e63 |
| Rose | ffe4e1 |
| Fuchsia | ff66ff |
| Purple | 9c27b0 |
| Dark Purple | 673ab7 |
| Indigo | 3f51b5 |
| Blue | 2196f3 |
| Light blue | 03a9f4 |
| Cyan | 00bcd4 |
| Teal | 009688 |
| Aqua | 00ffff |
| Dark green | 2f6a31 |
| Green | 4caf50 |
| Light green | 8bc34a |
| Lime | cddc39 |
| Yellow | ffeb3b |
| Amber | ffc107 |
| Orange | ff9800 |
| Dark orange | ff5722 |
| Brown | 795548 |
| Light grey | c0c0c0 |
| Grey | 9e9e9e |
| Dark grey | 607d8b |
| Black | 111111 |
| White | ffffff |

Example of ORM creation:

```python
Tag.objects.get_or_create(
    name="Cisco-3650CX",
    slug="cisco-3650cx",
    description="Device tag for Cisco 3650CX series",
    color="2196f3"
)
```
