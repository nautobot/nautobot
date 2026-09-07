# Conditions

+++ 3.3.0

A condition narrows *which changes* a Webhook or Job Hook reacts to. Without conditions, an action fires for every change to every object of its selected types. With conditions, it fires only when the change looks a certain way: a device's status went from `Staged` to `Active`, an interface's MTU went above 9000, a change was made by anyone other than the sync account.

Conditions are a list of rows. Every row must pass for the action to fire; an empty list passes. Each row is either a **preset** chosen from a catalog and filled in, or a **raw expression** written in Jinja2. Either kind can be negated.

## The event payload

Every condition is checked against the same payload a webhook body template receives. Its variables are:

| Variable | Description |
|----------|-------------|
| `event` | `created`, `updated`, or `deleted`. |
| `model` | The model name of the changed object, e.g. `device`. |
| `timestamp` | When the change was recorded. |
| `username` | The user who made the change. |
| `request_id` | Shared by every change made in one request. |
| `data` | The object as recorded for this change: its state after a create or update, its last known state on a delete. |
| `snapshots` | `prechange`, `postchange`, and `differences`. `prechange` is `None` on a create, `postchange` is `None` on a delete. |

### Fields and relations

A field is addressed by name: `mtu`, `name`. A related object is serialized as a mapping, so it is addressed by the key inside it, separated by a dot: `status.name`, `primary_ip4.address`, `location.name`. Naming the relation alone, `status`, yields the whole mapping, which no comparison matches.

A dot only reaches inside a mapping. A many-valued field such as `tags` is a list, so `tags.name` yields nothing. Use the list as a whole, or a raw expression.

## Presets

A preset is a ready-made condition with a fixed meaning. You choose it and fill in its parameters.

| Preset | Fires when |
|--------|-----------|
| **Field transition** | the field went from one value to another, within an update |
| **Field changed** | the field's value changed, whatever it changed to, within an update |
| **Field compare** | the field compares as chosen against a value |
| **User is** | a specific user made the change |

### Field transition

| Parameter | Description |
|-----------|-------------|
| `field` | Field to watch, e.g. `status.name`. |
| `from` | Value the field must have had before the change. |
| `to` | Value the field must have after the change. |

### Field changed

| Parameter | Description |
|-----------|-------------|
| `field` | Field to watch, e.g. `mtu` or `status.name`. |

### Field compare

| Parameter | Description |
|-----------|-------------|
| `field` | Field to compare, e.g. `mtu` or `status.name`. |
| `operator` | One of the [operators](#operators). |
| `value` | The value to compare against. |

### User is

| Parameter | Description |
|-----------|-------------|
| `username` | Username that must have made the change. |

## Operators

Used by **Field compare**. What a comparison does depends on the type of the field's value:

| Value type | `=` | `gt` `gte` `lt` `lte` | `in` | `contains` | `startswith` `endswith` |
|------------|-----|-----------------------|------|------------|-------------------------|
| text, date | exact match | alphabetical | any of the set | substring | prefix / suffix |
| number | numeric | numeric | any of the set | – | – |
| boolean | true / false | – | – | – | – |
| list | same set of values | – | – | – | – |

There is no `!=` operator: negate the row instead.

## Raw expressions

When no preset fits, write the condition as a Jinja2 expression. It is an expression, not a template: no `{{ }}` and no `{% %}`, and it should evaluate to true or false.

```jinja
A and B
A or B
not A
```

The expression sees the payload variables above and the same filters as a webhook body template. Expressions run in a sandbox and cannot modify the payload.

Prefer a preset when one fits.

## How conditions are checked

When a change is recorded, Nautobot goes through the action's conditions one by one. Each row is checked on its own against the change. The action fires only if every row passes, so adding rows narrows the action down. An action with no rows fires for every change.

A row passes when what it asks is true of the change. A negated row passes when it is false. A row that cannot be checked at all, for example because of a syntax error in an expression or a value of the wrong type for the operator, fails and reports why.

All rows are checked, even after one has failed, so you can see which rows passed, which failed, and which could not be checked.

## Row format

This section is for setting conditions through the REST API. In the web UI the form builds the rows for you.

Conditions are a list. Each entry is a preset row or an expression row:

```json
[
    {"type": "preset", "preset": "field_compare", "values": {"field": "mtu", "operator": "gt", "value": 9000}},
    {"type": "expression", "source": "data.mtu > 9000 or username != 'sync-infoblox'", "negate": true}
]
```

A preset row names the preset and gives its values. The preset keys are `field_transition`, `field_changed`, `field_compare` and `user_is`, and the value names are the parameter names from the tables above. Any other name is rejected.

An expression row has the expression in `source`.

Either kind may have `"negate": true` to invert it. Without it the row is not negated.
