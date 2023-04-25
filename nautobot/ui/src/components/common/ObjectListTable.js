import { Box, Heading } from "@nautobot/nautobot-ui";
import { RouterButton } from "./RouterButton";
import { ButtonGroup } from "@chakra-ui/react";
import * as Icon from "react-icons/tb";
import { useLocation } from "react-router-dom";

import NautobotTable from "@components/core/Table";
import Paginator from "@components/common/paginator";

// A composite component for displaying a object list table. Just the data!
export default function ObjectListTable({
    tableData,
    tableHeader,
    totalCount,
    active_page_number,
    page_size,
    gridColumn,
    model_name = "Model Name",
}) {
    let location = useLocation();
    return (
        <Box
            background="white-0"
            borderRadius="md"
            gridColumn={gridColumn}
            padding="md"
        >
            <Box display="flex" justifyContent="space-between">
                <Heading>&gt; &gt; &gt; {model_name}</Heading>
                <ButtonGroup pb="sm">
                    <RouterButton to={`${location.pathname}add`} mr={2}>
                        <Icon.TbPlus /> Add
                    </RouterButton>
                    <RouterButton to="#" variant="secondary" mr={2}>
                        <Icon.TbDatabaseImport /> Import
                    </RouterButton>
                    <RouterButton to="#" variant="secondary" mr={2}>
                        <Icon.TbDatabaseExport /> Export
                    </RouterButton>
                </ButtonGroup>
            </Box>
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
