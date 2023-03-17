import {
  Button,
  Frame,
} from "@nautobot/nautobot-ui";
import { Link } from "./RouterLink";
import { ButtonGroup } from "@chakra-ui/react";
import * as Icon from "react-icons/tb";
import { useLocation } from "react-router-dom";

import NautobotTable from "@components/core/Table";
import Paginator from "@components/common/paginator";

// A composite component for displaying a object list table. Just the data!
export default function ObjectListTable({ tableData, tableHeader, totalCount, active_page_number, page_size }) {
  let location = useLocation();
  return (
    <Frame>
      <ButtonGroup>
        <Button>
          <Link to={`${location.pathname}add`}>
            <Icon.TbPlus /> Add
          </Link>
        </Button>{" "}
        <Button variant="secondary">
          <Icon.TbDatabaseImport /> Import
        </Button>{" "}
        <Button variant="secondary">
          <Icon.TbDatabaseExport /> Export
        </Button>{" "}
      </ButtonGroup>
      <NautobotTable data={tableData} headers={tableHeader} />
      <Paginator
        url={location.pathname}
        data_count={totalCount}
        page_size={page_size}
        active_page={active_page_number}
      ></Paginator>
    </Frame>
  );
}
