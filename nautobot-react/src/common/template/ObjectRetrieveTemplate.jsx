import { useState, useEffect } from "react";
//react-bootstrap
import Card from "react-bootstrap/Card";
import CardHeader from "react-bootstrap/CardHeader";
import Tab from "react-bootstrap/Tab";
import Table from "react-bootstrap/Table";
import Tabs from "react-bootstrap/Tabs";
//utils
import { axios_instance } from "common/utils/utils";
//icons
import * as Icon from "react-feather";


export default function ObjectRetrieveTemplate({ pageTitle, ...props }) {
  const [pageConfig, setPageConfig] = useState({
    buttons: {
      configure: {
        label: "Configure",
        icon: <Icon.Settings size={15} />,
        color: "outline-dark",
      },
      add: {
        label: "Add",
        icon: <Icon.Plus size={15} />,
        color: "primary",
        link: "add",
      },
      import: {
        label: "Import",
        icon: <Icon.Cloud size={15} />,
        color: "info",
        link: "import",
      },
      export: {
        label: "Export",
        icon: <Icon.Database size={15} />,
        color: "success",
      },
    },
  });
  const [objectData, setObjectData] = useState([]);

  useEffect(() => {
    async function fetchData(props) {
      const data_url = "/api" + window.location.pathname;
      // const header_url = "/api" + window.location.pathname + "table-fields/";
      const object_data = await axios_instance.get(data_url);
      // const table_header = await axios_instance.get(header_url);
      setObjectData(object_data.data);

      let newPageConfig = pageConfig;
      if (props.config) {
        if (props.config.buttons) {
          let pageButtons = props.config.buttons;
          newPageConfig = {
            ...newPageConfig,
            buttons: { ...newPageConfig.buttons, ...pageButtons },
          };
        }
        // TODO: incase a different api is passed for table data and header
      }
      setPageConfig(newPageConfig);
    }
    fetchData(props);
  }, []);

  return (
    <div>
      <h1>{objectData.name}</h1>
      <p>
        <small className="text-muted">
          {objectData.created &&
            <>Created {objectData.created} &middot; </>
          }
          <> Updated <span title={objectData.last_updated}>xyz seconds</span> ago</>
        </small>
      </p>
      <div className="pull-right noprint">

      </div>
      <Tabs defaultActiveKey="site">
        <Tab eventKey="site" title="Site">
          <br />
          <Card>
            <CardHeader>
              <strong>Site</strong>
            </CardHeader>
            <Table hover>
              <tbody>
                <tr>
                  <td>Status</td>
                  <td>
                    <span className="label">Active</span>
                  </td>
                </tr>
                <tr>
                  <td>Region</td>
                  <td>
                    {objectData.region ? <>{objectData.region}</> : "—"}
                  </td>
                </tr>
                <tr>
                  <td>Tenant</td>
                  <td>
                    {objectData.tenant ? <>{objectData.tenant}</> : "—"}
                  </td>
                </tr>
                <tr>
                  <td>Facility</td>
                  <td>
                    {objectData.facility ? <>{objectData.facility}</> : "—"}
                  </td>
                </tr>
                <tr>
                  <td>AS Number</td>
                  <td>
                    {objectData.asn ? <>{objectData.asn}</> : "—"}
                  </td>
                </tr>
                <tr>
                  <td>Time Zone</td>
                  <td>
                    {objectData.time_zone ? <>{objectData.time_zone}</> : "—"}
                  </td>
                </tr>
                <tr>
                  <td>Description</td>
                  <td>
                    {objectData.description ? <>{objectData.description}</> : "—"}
                  </td>
                </tr>
              </tbody>
            </Table>
          </Card>
        </Tab>
        <Tab eventKey="advanced" title="Advanced" />
        <Tab eventKey="notes" title="Notes" />
        <Tab eventKey="change_log" title="Change Log" />
      </Tabs>
    </div>
  );
}



/*
<div class="row noprint">
{% with list_url=object|validated_viewname:"list" %}
<div class="col-sm-8 col-md-9">
    <ol class="breadcrumb">
    {% block breadcrumbs %}
        {% if list_url %}
        <li><a href="{% url list_url %}">
            {{ verbose_name_plural|bettertitle }}
        </a></li>
        {% endif %}
        {% block extra_breadcrumbs %}{% endblock extra_breadcrumbs %}
        <li>{{ object|hyperlinked_object }}</li>
    {% endblock breadcrumbs %}
    </ol>
</div>
{% if list_url %}
<div class="col-sm-4 col-md-3">
    <form action="{% url list_url %}" method="get">
        <div class="input-group">
            <input type="text" name="q" class="form-control" placeholder="Search {{ verbose_name_plural }}" />
            <span class="input-group-btn">
                <button type="submit" class="btn btn-primary">
                    <span class="mdi mdi-magnify" aria-hidden="true"></span>
                </button>
            </span>
        </div>
    </form>
</div>
{% endif%}
{% endwith %}
</div>

<div class="pull-right noprint">
{% block buttons %}
{% plugin_buttons object %}
{% block extra_buttons %}{% endblock extra_buttons %}
{% if object.clone_fields and user|can_add:object %}
    {% clone_button object %}
{% endif %}
{% if user|can_change:object %}
    {% edit_button object %}
{% endif %}
{% if user|can_delete:object %}
    {% delete_button object %}
{% endif %}
{% endblock buttons %}
</div>

{% block masthead %}
<h1>{% block title %}{{ object }}{% endblock %}</h1>
{% endblock masthead %}
{% include 'inc/created_updated.html' %}
<div class="pull-right noprint">
{% custom_links object %}
{% block panel_buttons %}{% endblock panel_buttons %}
</div>

<ul id="tabs" class="nav nav-tabs">
{% block nav_tabs %}
<li role="presentation"{% if active_tab == "main" or request.GET.tab == "main" %} class="active"{% endif %}>
    <a href="{{ object.get_absolute_url }}#main" onclick="switch_tab(this.href)" aria-controls="main" role="tab" data-toggle="tab">
        {{ verbose_name|bettertitle }}
    </a>
</li>
<li role="presentation"{% if request.GET.tab == 'advanced' %} class="active"{% endif %}>
    <a href="{{ object.get_absolute_url }}#advanced" onclick="switch_tab(this.href)" aria-controls="advanced" role="tab" data-toggle="tab">
        Advanced
    </a>
</li>
{% block extra_nav_tabs %}{% endblock extra_nav_tabs %}
{% if perms.extras.view_note %}
    {% if active_tab != 'notes' and object.get_notes_url or active_tab == 'notes' %}
        <li role="presentation"{% if active_tab == 'notes' %} class="active"{% endif %}>
            <a href="{{ object.get_notes_url }}">Notes</a>
        </li>
    {% endif %}
{% endif %}
{% if perms.extras.view_dynamicgroup and object.get_dynamic_groups_url %}
    {% if active_tab != 'dynamic-groups' and object.get_dynamic_groups_url or active_tab == 'dynamic-groups' %}
        <li role="presentation"{% if active_tab == 'dynamic-groups' %} class="active"{% endif %}>
            <a href="{{ object.get_dynamic_groups_url }}">Dynamic Groups</a>
        </li>
    {% endif %}
{% endif %}
{% if perms.extras.view_objectchange %}
    {% if active_tab != 'changelog' and object.get_changelog_url or active_tab == 'changelog' %}
        <li role="presentation"{% if active_tab == 'changelog' %} class="active"{% endif %}>
            <a href="{{ object.get_changelog_url }}">Change Log</a>
        </li>
    {% endif %}
{% endif %}
{% endblock nav_tabs %}
{% plugin_object_detail_tabs object %}
</ul>
{% endblock header %}

{% block content %}
<div class="tab-content">
<div id="main" role="tabpanel" class="tab-pane {% if active_tab == "main" or request.GET.tab == "main" %}active{% else %}fade{% endif %}">
    <div class="row">
        <div class="col-md-6">
            {% block content_left_page %}{% endblock content_left_page %}
            {% include 'inc/custom_fields/panel.html' with custom_fields=object.get_custom_field_groupings_basic computed_fields_advanced_ui=False %}
            {% include 'inc/relationships_panel.html' %}
            {% include 'extras/inc/tags_panel.html' %}
            {% plugin_left_page object %}
        </div>
        <div class="col-md-6">
            {% block content_right_page %}{% endblock content_right_page %}
            {% plugin_right_page object %}
        </div>
    </div>
    <div class="row">
        <div class="col-md-12">
            {% block content_full_width_page %}{% endblock content_full_width_page %}
            {% plugin_full_width_page object %}
        </div>
    </div>
</div>
<div id="advanced" role="tabpanel" class="tab-pane {% if request.GET.tab == 'advanced' %}active{% else %}fade{% endif %}">
    <div class="row">
        <div class="col-md-6">
            {% include 'inc/object_details_advanced_panel.html' %}
        </div>
        <div class="col-md-6">
            {% block advanced_content_right_page %}{% endblock advanced_content_right_page %}
        </div>
    </div>
    <div class="row">
        <div class="col-md-12">
            {% block advanced_content_full_width_page %}{% endblock advanced_content_full_width_page %}
        </div>
    </div>
</div>
{% block extra_tab_content %}{% endblock extra_tab_content %}
</div>
*/
