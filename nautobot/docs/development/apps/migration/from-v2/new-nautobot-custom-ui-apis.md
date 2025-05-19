# New Nautobot custom UI APIs

## Nautobot custom HTML data attributes and CSS classes

Up until v3.x, Nautobot has been *"smuggling"* its own CSS classes along with other 3rd party libraries. In v3.x we decided that it is only fair to be transparent about which of these are exclusive to Nautobot.

From now on, all HTML data attributes and CSS classes which refer to Nautobot custom functionalities are prefixed with `nb-*`.

## Table configuration button

Configurable table columns are no novelty for Nautobot. However, when we redesigned user interface in v3.x, we also changed the way table configuration buttons are rendered, and as result they are now more coupled with tables they manage. Table configuration buttons are no longer standalone buttons on the page, instead they are rendered in the top right header cell of any **configurable** table.

!!! note
    Generic Nautobot list views provide this feature out of the box and do not require you to do anything. This guide is relevant only for templates other than generic Nautobot list views.

1. You are no longer responsible for rendering table configuration buttons in templates, and you should remove existing `{% table_config_button ... %}` template tag usages.
2. Tables with customizable columns are now explicitly **configurable**. You are required to do one of the following to enable table configurability:
    - Pass `configurable=True` keyword argument to constructor of a standard table which inherits from `BaseTable`.
    - Set `self.configurable = True` property in custom table class object utilizing core `table.html` template under the hood.
    - Manually include `{% table_config_button table %}` in top right header cell if table class has its own custom template.

## Table action buttons

In v3.x we moved table action buttons to dropdown menus. It does not affect the way buttons work, but impacts the way they are presented. Tables using standard core `ButtonsColumn` ship with this feature already implemented.

In case you provided your own HTML in `prepend_template`, you need to migrate flat buttons to dropdown menu items. Below is an example of how has `prepend_template` changed, for more details see [how to upgrade Dropdowns](./upgrading-from-bootstrap-v3-to-v5.md#dropdowns).

!!! warning
    If you used `TemplateColumn` to render table action buttons, you are not required to do anything, and they will continue operating the way they did. However, since v3.x it is Nautobot design system recommendation to display table action buttons within dropdown menus.

Nautobot v2.x:

```html
<button
    data-url="{% url 'extras:gitrepository_sync' pk=record.pk %}"
    type="submit" class="btn btn-primary btn-xs sync-repository"
    title="Sync" {% if not perms.extras.change_gitrepository %}disabled="disabled"{% endif %}
>
    <i class="mdi mdi-source-branch-sync" aria-hidden="true"></i>
</button>
```

Nautobot v3.x:

```html
<li>
    <button
        data-url="{% url 'extras:gitrepository_sync' pk=record.pk %}"
        type="submit"
        class="dropdown-item sync-repository{% if perms.extras.change_gitrepository %} text-primary"{% else %}" disabled="disabled"{% endif %}
    >
        <span class="mdi mdi-source-branch-sync" aria-hidden="true"></span>
        Sync
    </button>
</li>
```

## Drawer

In addition to [Bootstrap v5.x Offcanvas](https://getbootstrap.com/docs/5.3/components/offcanvas/), Nautobot v3.x ships with its own Drawer component. These are the most notable differences between them:

| Offcanvas                                                              | Drawer                                                                             |
|------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| Generic Bootstrap v5.x component with many configurable options.       | Tailored for specific use cases without much configurability involved.             |
| Renders in front of everything else overlaying given side of the page. | Occupies right-hand side of the page pushing the rest of its content further left. |

In Nautobot we use Drawer more often than Offcanvas but as usual, there is no one-size-fits-all and both components have their strengths and weaknesses.

The best place to see how to use Offcanvas is Bootstrap v5.x documentation. For Drawer, let's take a look example below:

```html
<!-- Drawer toggle button -->
<button
    type="button"
    class="btn btn-secondary"
    data-nb-toggle="drawer"
    data-nb-target="#myDrawer"
    aria-expanded="false"
    aria-controls="myDrawer"
>
    <span class="mdi mdi-view-compact-outline" aria-hidden="true"></span>
    <span class="visually-hidden">Saved Views</span>
</button>

<!-- Drawer -->
{% block drawer %}
    <section class="nb-drawer" tabindex="-1" id="myDrawer">
        <div class="nb-drawer-header">
            <h1>My drawer</h1>
            <button type="button" class="btn-close" data-nb-dismiss="drawer" aria-label="Close"></button>
        </div>
        <div class="nb-drawer-body">
            My drawer body.
        </div>
    </section>
{% endblock %}
```
