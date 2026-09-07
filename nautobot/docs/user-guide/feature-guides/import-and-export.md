# Importing and Exporting Objects

Nautobot can export any list of objects to a file in CSV, JSON, or YAML format. It can also import these same three formats to create new objects and/or update existing objects ("upsert") as desired.

From any object list view, under the **Actions** menu, there are two available action items:

- Export to file
- Import from file

These actions are backed by the built-in system Jobs `Export Object List` and `Import Objects` respectively. Because of this, you must have the *run* permission for these Jobs as well as the appropriate permissions for the object type you are exporting/importing (see [Permissions](#permissions)) in order to perform these actions. Additionally, each time you perform these actions, because they are Job-backed, the action runs asynchronously (allowing for export/import of quite large data sets without running the risk of your browser HTTP request timing out) and produces a Job Result and corresponding log entries.

## Exporting

From any supported object list view, choose **Export to file** from the **Actions** menu. A modal dialog will open, allowing you to choose the export file format, optionally pick and order the object fields ("id", "name", etc.) to include or exclude from the export, optionally apply filtering/sorting criteria to scope the export's content. When the Job finishes, you will be presented with the option to download the resulting file.

### Choosing an export format

| Format | What you get |
|--------|--------------|
| CSV    | A `.csv` file in UTF-8 encoding with a leading BOM so that it can open cleanly in Microsoft Excel and similar editors. The first line will be a metadata comment (see [The self-describing file](#the-self-describing-file)), the second line will define column headers corresponding to the object fields included in the export, and each subsequent line will describe a single record. |
| JSON   | A `.json` file, with top-level metadata keys (see [The self-describing file](#the-self-describing-file)) and a `records` key containing the list of exported objects. Data involving traversal to related objects via database foreign keys (and similar patterns) will be rendered as nested JSON objects, rather than the flattened set of columns present in CSV exports. |
| YAML   | A `.yaml` file, structured exactly the same as the JSON export but in YAML format, which you may find easier to review and edit as desired. |
| devicetype-library YAML | *For Device Types and Module Types only.* A `.yaml` file describing not only the selected [Device Types](../core-data-model/dcim/devicetype.md) or [Module Types](../core-data-model/dcim/moduletype.md), but also their associated component templates ([Interface Templates](../core-data-model/dcim/interfacetemplate.md), etc.). Suitable for interoperability with the [devicetype-library](https://github.com/nautobot/devicetype-library) Git repository. |

### Null values

Fields with a null value are represented in JSON and YAML as the native `null` type. Because CSV has no concept of a null type, the string `NULL` will be used in CSV export to represent a null value. This does unavoidably mean that a character field whose value is literally the text "NULL" will not survive an export-import loop via CSV - use JSON or YAML format instead if this is a concern for your data.

### Related objects

Related objects are represented differently per export format, but in all formats, Nautobot attempts to use the *natural key* (if any) to represent a related object, only falling back to its UUID if no natural key is available.

#### Foreign keys

**CSV** exports flatten related-object natural keys into columns where the database path is joined by `__` - for example, a related Device Type (with natural keys "manufacturer name" and "model") might be represented by the columns `device_type__manufacturer__name` and `device_type__model`. On import, the two columns would work together to identify the specific existing Device Type being referenced. For a null related object, CSV uses the string `NoObject` since, again, CSV has no native null type:

```csv
name,device_type__manufacturer__name,device_type__model,tenant__name
my-device,Cisco,ISR4331,my-tenant
my-other-device,Cisco,ISR4331,NoObject
```

**JSON and YAML** exports represent related objects as nested data, and use the native null type when appropriate:

```yaml
records:
  - name: "my-device"
    device_type:
      manufacturer:
        name: "Cisco"
      model: "ISR4331"
    tenant:
      name: "my-tenant"
  - name: "my-other-device"
    device_type:
      manufacturer:
        name: "Cisco"
      model: "ISR4331"
    tenant: null
```

JSON and YAML *imports* also support the CSV-style flattened columns as well, if you're creating your own import file and find it more convenient:

```yaml
records:
  - name: "my-other-device"
    device_type__manufacturer__name: "Cisco"
    device_type__model: "ISR4331"
    tenant: null
```

#### Many-to-many relations

Many to many relations to other objects follow a similar pattern to foreign keys, with some additional nuances.

Relations to an object type that has a *single-value natural key* (for example, `name`) or no natural key (falling back to `id`) are expressed as a list of such single values directly. In CSV, this will be a comma-separated list (escaped as appropriate) within the single column:

```csv
name,tags
my-device,"tag-1,tag-2"
my-other-device,tag-3
```

and in JSON or YAML this will be a list of values:

```yaml
  - name: "my-device"
    tags:
      - "tag-1"
      - "tag-2"
  - name: "my-other-device"
    tags:
      - "tag-3"
```

Conversely, relations to an object type with a *composite natural key* will be expressed as a list of natural-key dictionaries. In CSV, this is represented as a JSON string within the single column:

```csv
name,software_image_files
my-device,"[{""image_file_name"": ""ios.bin"", ""software_version__platform__name"": ""IOS"", ""software_version__version"": ""15.1""}]"
```

while in JSON or YAML it's a list of nested objects:

```yaml
  - name: "my-device"
    software_image_files:
      - image_file_name: "ios.bin"
        software_version:
          platform:
            name: "IOS"
          version: "15.1"
```

!!! tip "An alternate CSV representation for many-to-many imports with composite natural keys"
    Although CSV *exports* now always produce the above embedded-JSON representation of many-to-many relations that require a composite natural key to describe, CSV *imports* additionally support an alternative representation where there is one column per field in the natural key, and the value of each column is the list of values for that field. This could look something like:

    ```csv
    name,software_image_files__image_file_name,software_image_files__software_version__platform__name,software_image_files__software_version__version
    my-device,"ios151.bin,ios152.bin","IOS,IOS","15.1,15.2"
    ```

### Selecting fields to export

By default an export includes every field of the object type. In the **Export to file** dialog you can instead pick the specific fields you want and put them in the order you want them to appear. The `Export Object List` Job offers the same capability through its **Fields to Export** (`export_fields`) parameter, which takes a comma-separated list:

```no-highlight
model,manufacturer__name,u_height
```

The columns appear in exactly the order you list them, so this is also how you control column order:

```csv
# nautobot_import_version=3; model=dcim.devicetype; match_fields=manufacturer__name model
model,manufacturer__name,u_height
ISR4331,Cisco,1
```

Each entry is either a plain field (`model`), or a path that traverses one or more foreign keys to reach a field of a related object, joined by `__` (`manufacturer__name`, `device_type__manufacturer__name`). A single path may traverse at most three relations.

Naming a related object *without* expanding it selects that object's whole natural key - the same columns an unrestricted export would have produced for it. So `model,manufacturer` gives you the same file as the example above minus `u_height`, because `manufacturer` expands to `manufacturer__name`:

```csv
model,manufacturer__name
ISR4331,Cisco
```

Many-to-many fields, such as `tags`, can be selected like any other field, but cannot currently be traversed: `tags` is valid, `tags__name` is not. Selecting the field itself already gives you its members' natural keys, so `tags` yields the tag names; what is not yet supported is narrowing a member's representation to particular fields, such as asking for only `software_image_files__image_file_name`.

#### Selecting custom fields

Use `cf_<key>` to select an individual custom field, or `custom_fields` to select all of them at once.

In a CSV export both spellings produce one `cf_<key>` column per selected custom field, exactly as an unrestricted export does. In JSON and YAML exports, `custom_fields` keeps the nested dictionary, while an individual `cf_<key>` selection is emitted as a top-level key instead, since a single custom field cannot be named inside the dictionary:

```yaml
records:
  - name: "Active"
    cf_my_field: "a value"
```

#### Fields that cannot be selected

The Job fails, with an error naming the entry at fault, rather than quietly writing a file that is missing what you asked for. This happens if a selection:

- names a field the object type does not have, or a custom field that is not defined for it
- names a field that exists only for input rather than output, such as the singular `location` field on VLANs and Prefixes - export the `locations` many-to-many field instead
- attempts to traverse a many-to-many field, or a field that is not a relation at all
- traverses more than three relations in a single path
- names a field on a related model that the user does not have at least some form of `view` permission for, with the exception of the `id` field which is always permitted.

#### Effect on re-importing the file

A file containing only some of an object type's fields may not contain enough information to identify the objects it describes. When the selected fields do not cover every field of the model's match key, the `match_fields` metadata is therefore omitted from the export (see [The self-describing file](#the-self-describing-file)), as in the `model,manufacturer__name` example above had `manufacturer__name` been left out.

Such a file can still be imported - you just have to say what to match on, either by [specifying match fields](#match-fields) as an input to the `Import Objects` Job or by adding the metadata to the file yourself.

### Scoping the exported objects

TODO - add documentation when this is implemented

## The self-describing file

Each exported file produced by Nautobot includes metadata describing *how it should be re-imported* - specifically, the following metadata:

- `nautobot_import_version`: the version of Nautobot export/import data this file conforms to. Currently `3`, as there have been two previous styles of Nautobot export/import data, although neither of those styles ever included an explicit version-number string.
- `model`: the Nautobot data model / content-type, such as "dcim.device".
- `match_fields`: the [set of fields](#match-fields) (sometimes also referred to as a "match key") that should be used, when importing this file, to pair records in the file with existing Nautobot objects, in order to determine whether a given record should be used to create a new object or update an existing one.

CSV exports carry the metadata as a directive on the first line:

```csv
# nautobot_import_version=3; model=extras.status; match_fields=name
name,color
Active,00ff00
```

while JSON and YAML exports carry the metadata at the document root:

```yaml
nautobot_import_version: 3
model: "extras.status"
match_fields:
  - "name"
records:
  - name: "Active"
    color: "00ff00"
```

## Importing

TODO - add documentation when this is implemented

### Match fields

All Nautobot data models define their default match fields, which are either a "natural key" (field or set of fields that uniquely identify an object, for example a Status's `name` field), or if no unique natural key is possible, simply use the object's `id` as its match field. This default set of match fields is added to the exported file as metadata, as described [above](#the-self-describing-file).

When importing, you can override the match fields for a particular file either by editing the metadata directly before uploading the file, or by explicitly specifying match fields as an input to the "Import Objects" Job. This can be powerful for in-place updates where you know that a given field(s), even though not actually enforced unique by Nautobot itself, happen in your particular use case to be unique identifiers for the existing objects in the system. Overriding the match fields in this case can allow you to specify records in a simpler or more portable way than using a full natural-key field set or using the raw `id` values would.

!!! warning "You own the uniqueness"
    When setting a custom set of match fields, *you are responsible* for ensuring that the fields you choose do in fact uniquely identify objects in Nautobot. Nautobot does not enforce that your chosen fields are backed by a database-level uniqueness constraint, a data validation rule, or anything of the sort. If two rows in your file share the same match field values, you'll get a clear "does not uniquely identify each row" error, and if any row in your file matches more than one existing object, the import will refuse to row rather than guess which object you meant.

## Permissions

| Action | Permissions required |
|--------|----------------------|
| Export | Run permission for the `Export Object List` job, plus *view* permission on the model. |
| Import (create rows) | Run permission for the `Import Objects` job, plus *add* permission on the model. |
| Import (update rows) | Run permission for the `Import Objects` job, plus *change* permission on the model. |
