import { Box } from "@nautobot/nautobot-ui";
import { useLocation } from "react-router-dom";

import NautobotTable from "@components/Table";
import Paginator from "@components/paginator";

// A composite component for displaying a object list table. Just the data!
export default function ObjectListTableNoButtons({
    tableData,
    tableHeader,
    totalCount,
    active_page_number,
    page_size,
    gridColumn,
}) {
    let location = useLocation();
    return (
        <Box
            background="white-0"
            borderRadius="md"
            gridColumn={gridColumn}
            padding="md"
        >
            <NautobotTable data={tableData} headers={tableHeader} />
            <Paginator
                url={location.pathname}
                data_count={totalCount}
                page_size={page_size}
                active_page={active_page_number}
            ></Paginator>
        </Box>
    );
}
