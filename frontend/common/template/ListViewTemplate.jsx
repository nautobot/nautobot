import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
//react-bootstrap
import Row from "react-bootstrap/Row";
import Col from "react-bootstrap/Col";
import Button from "react-bootstrap/Button";
import NavLink from "react-bootstrap/NavLink";
import NautobotTable from "@shared/NautobotTable";
//pages
import Home from "../../pages";
//utils
import { axios_instance } from "@utils/utils";
//icons
import * as Icon from "react-feather";

export default function ListViewTemplate({ pageTitle, ...props }) {
  const router = useRouter();

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

  useEffect(async () => {
    const data_url = "/api" + location.pathname + "/";
    const header_url = "/api" + location.pathname + "/table-fields/";
    const table_data = await axios_instance.get(data_url);
    const table_header = await axios_instance.get(header_url);
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
      // TODO: incase a diffrent api is passed for table daata and header
    }
    setPageConfig(newPageConfig);
  }, [setTableData, setTableHeader]);

  return (
    <Home pageTitle={pageTitle}>
      <Row>
        <Col xs={8}>{/* <h3>{pageConfig.data.title}</h3> */}</Col>
        <Col className="text-right action-items-container">
          {Object.entries(pageConfig.buttons).map((item, idx) =>
            item[1] ? (
              <NavLink
                as={Link}
                key={idx}
                href={item[1].link ? router.pathname + "/" + item[1].link : "#"}
              >
                <Button
                  // key={idx}
                  size="sm"
                  variant={item[1].color}
                  className="mr-2 action-btn"
                >
                  {item[1].icon} {item[1].label}
                </Button>
              </NavLink>
            ) : null
          )}
        </Col>
      </Row>
      <Row>
        <Col>
          <NautobotTable data={tableData} header={tableHeader} />
        </Col>
      </Row>
    </Home>
  );
}
