# Config Context Schemas

+++ 1.1.0

While config contexts allow for arbitrary data structures to be stored within Nautobot, at scale it is desirable to apply validation constraints to that data to ensure its consistency and to avoid data entry errors. To service this need, Nautobot supports optionally backing config contexts with [JSON Schemas](https://json-schema.org/) for validation. These schema are managed via the config context schema model and are optionally linked to config context instances, in addition to devices and virtual machines for the purpose of validating their local context data.

A JSON Schema is capable of validating the structure, format, and type of your data, and acts as a form of documentation useful in a number of automation use cases.

A config context is linked to a single schema object and thus they are meant to model individual units of the overall context. In this way, they validate each config context object, not the fully rendered context as viewed on a particular device or virtual machine.

When a config context schema is employed on a config or local context, the data therein is validated when the object in question is saved. Should validation against the schema fail, a relevant error message is returned to the user and they are prevented from saving the data until the validation issue has been resolved.

Here is an example JSON Schema which can be used to validate an NTP server config context:

```json
{
    "type": "object",
    "properties": {
        "ntp-servers": {
            "type": "array",
            "minItems": 2,
            "maxItems": 2,
            "items": {
                "type": "string",
                "format": "ipv4"
            }
        }
    },
    "additionalProperties": false
}
```

This schema would allow a config context with this data to pass:

```json
{
    "ntp-servers": [
        "172.16.10.22",
        "172.16.10.33"
    ]
}
```

However it would not allow any of these examples to be saved:

```json
{
    "ntp-servers": [
        "172.16.10.22"
    ]
}
```

```json
{
    "ntp": "172.16.10.22,172.16.10.22"
}
```

```json
{
    "ntp-servers": [
        "172.16.10.22",
        "172.16.10.33",
        "5.5.4"
    ]
}
```

For more information on JSON Schemas and specifically type formats for specialized objects like IP addresses, hostnames, and more see the JSON Schema [docs](https://json-schema.org/understanding-json-schema/reference/string.html#format).

!!! note
    Config Context Schemas currently support the JSON Schema draft 7 specification.
