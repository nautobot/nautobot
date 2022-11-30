import { useState, useEffect } from "react";
//react-bootstrap
import Row from "react-bootstrap/Row";
import Col from "react-bootstrap/Col";
import Button from "react-bootstrap/Button";
import NavLink from "react-bootstrap/NavLink";
import NautobotTable from "common/shared/NautobotTable";
//utils
import API from "common/utils/utils";
//icons
import * as Icon from "react-feather";
import { LinkContainer } from "react-router-bootstrap";

import App from "App";

export default function ListViewTemplate({ pageTitle, ...props }) {
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
  const [tableData, setTableData] = useState([]);
  const [tableHeader, setTableHeader] = useState([]);

  useEffect(() => {
    async function fetchData(props) {
      const data_url = "/api" + window.location.pathname;
      const header_url = "/api" + window.location.pathname + "table-fields/";
      const table_data = await API.get(data_url);
      const table_header = await API.get(header_url);
      setTableData(table_data.data.results);
      setTableHeader(table_header.data.data);

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
      <App>
        <Row>
          <Col xs={8}>{/* <h3>{pageConfig.data.title}</h3> */}</Col>
          <Col className="text-right action-items-container">
            {Object.entries(pageConfig.buttons).map((item, idx) =>
              item[1] ? (
                <LinkContainer key={idx} to={item[1].link ? item[1].link : ""}>
                  <NavLink>
                    <Button
                      // key={idx}
                      size="sm"
                      variant={item[1].color}
                      className="mr-2 action-btn"
                    >
                      {item[1].icon} {item[1].label}
                    </Button>
                  </NavLink>
                </LinkContainer>
              ) : null
            )}
          </Col>
        </Row>
        <Row>
          <Col>
            <NautobotTable data={tableData} header={tableHeader} />
          </Col>
        </Row>
      </App>
    </div>
  );
}
