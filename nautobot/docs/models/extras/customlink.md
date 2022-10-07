# Custom Links

Custom links allow users to display arbitrary hyperlinks to external content within Nautobot object views. These are helpful for cross-referencing related records in systems outside of Nautobot. For example, you might create a custom link on the device view which links to the current device in a network monitoring system.

Custom links can be created under the admin UI or web UI located in the navbar under Extensibility > Miscellaneous > Custom Links. Each link is associated with a particular Nautobot object type (site, device, prefix, etc.) and will be displayed on relevant views. Each link is assigned text and a URL, both of which support Jinja2 templating. The text and URL are rendered with the context variable `obj` representing the current object.

For example, you might define a link like this:

* Text: `View NMS`
* URL: `https://nms.example.com/nodes/?name={{ obj.name }}`

When viewing a device named Router4, this link would render as:

```no-highlight
<a href="https://nms.example.com/nodes/?name=Router4">View NMS</a>
```

Custom links appear as buttons at the top right corner of the page. Numeric weighting can be used to influence the ordering of links.

## Context Data

The following context data is available within the template when rendering a custom link's text or URL.

| Variable | Description |
|----------|-------------|
| `obj`      | The Nautobot object being displayed |
| `debug`    | A boolean indicating whether debugging is enabled |
| `request`  | The current WSGI request |
| `user`     | The current user (if authenticated) |
| `perms`    | The [permissions](https://docs.djangoproject.com/en/stable/topics/auth/default/#permissions) assigned to the user |

All [built-in Jinja2 filters](../../additional-features/template-filters.md) are available and it's also possible to [develop and register a custom Jinja2 filters](../../plugins/development.md#including-jinja2-filters).

## Conditional Rendering

Only links which render with non-empty text are included on the page. You can employ conditional Jinja2 logic to control the conditions under which a link gets rendered.

For example, if you only want to display a link for active devices, you could set the link text to

```jinja2
{% if obj.status.slug == 'active' %}View NMS{% endif %}
```

The link will not appear when viewing a device with any status other than "active."

As another example, if you wanted to show only devices belonging to a certain manufacturer, you could do something like this:

```jinja2
{% if obj.device_type.manufacturer.name == 'Cisco' %}View NMS{% endif %}
```

The link will only appear when viewing a device with a manufacturer name of "Cisco."

## Link Groups

Group names can be specified to organize links into groups. Links with the same group name will render as a dropdown menu beneath a single button bearing the name of the group.
