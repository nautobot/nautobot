import { useState, useEffect } from "react";
//react-bootstrap
import Card from "react-bootstrap/Card";
import CardHeader from "react-bootstrap/CardHeader";
import Tab from "react-bootstrap/Tab";
import Table from "react-bootstrap/Table";
import Tabs from "react-bootstrap/Tabs";
//utils
import API from "common/utils/utils";
//icons
import * as Icon from "react-feather";
import { Link } from "react-router-dom";


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
      const object_data = await API.get(data_url);
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
                    <span className="label">
                      {objectData.status ? <>{objectData.status.label}</> : "—"}
                    </span>
                  </td>
                </tr>
                <tr>
                  <td>Region</td>
                  <td>
                    {objectData.region ?
                      <Link to={objectData.region.url}>{objectData.region.display}</Link> : "—"}
                  </td>
                </tr>
                <tr>
                  <td>Tenant</td>
                  <td>
                    {objectData.tenant ?
                      <Link to={objectData.tenant.url}>{objectData.tenant.display}</Link> : "—"}
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
