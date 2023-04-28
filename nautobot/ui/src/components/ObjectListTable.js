import { RouterButton } from "./RouterButton";
import { ButtonGroup } from "@chakra-ui/react";
import * as Icon from "react-icons/tb";
import { useLocation } from "react-router-dom";
import { useState } from "react";
import {
    Box,
    Heading,
    NtcThumbnailIcon,
    MeatballsIcon,
    Button as UIButton,
    TableRenderer,
    useTableRenderer,
    createColumnHelper,
    PlusIcon,
    Button,
    EditIcon,
} from "@nautobot/nautobot-ui";
import { useCallback, useMemo } from "react";

import TableItem from "@components/TableItem";

const getTableItemLink = (idx, obj) => {
    if (idx === 0) {
        // TODO: ui-schema should be providing the name of the field used to describe the object (name)
        return window.location.pathname + obj.id;
    }
    if (typeof obj !== "object" || !obj || !obj.url) {
        return null;
    }
    // Remove domain + /api prefix
    const url = obj.url.replace(window.location.origin + "/api", "");

    // Statuses and Roles should not be linkable
    if (
        ["/extras/statuses", "/extras/roles"].some((prefix) =>
            url.startsWith(prefix)
        )
    ) {
        return null;
    }
    return url;
};

// A composite component for displaying a object list table. Just the data!
export default function ObjectListTable({
    tableData,
    defaultHeaders,
    tableHeaders,
    totalCount,
    active_page_number,
    page_size,
    gridColumn,
    tableTitle,
}) {
    let location = useLocation();
    const columnHelper = useMemo(() => createColumnHelper(), []);
    let defaultNames = defaultHeaders.map((e) => e.key);
    let allNames = tableHeaders.map((e) => e.key);
    let disabledNames = allNames.filter((v) => !defaultNames.includes(v));
    const columnState = {};
    for (const key of disabledNames) {
        columnState[key] = false;
    }

    const [columnVisibility, setColumnVisibility] = useState(columnState);
    const columns = useMemo(
        () =>
            tableHeaders.map(({ key, title }, idx) =>
                columnHelper.accessor(key, {
                    cell: (props) => {
                        // Get the column data from the object
                        // e.g from {"status": {"display": "Active"}, "id": ....} get => {"display": "Active"}
                        const column_data =
                            idx === 0
                                ? props.row.original
                                : props.row.original[props.column.id];
                        return (
                            <TableItem
                                name={key}
                                obj={props.getValue()}
                                url={getTableItemLink(idx, column_data)}
                            />
                        );
                    },
                    header: title,
                })
            ),
        [columnHelper, tableHeaders]
    );
    const onRowSelectionChange = useCallback(() => {
        // Do something.
    }, []);

    const ActionMenu = useCallback(
        ({ cellContext }) => (
            <Button
                leftIcon={<EditIcon size="sm" />}
                size="xs"
                variant="table"
                onClick={() =>
                    alert(`Clicked ${cellContext.row.original.name}!`)
                }
            />
        ),
        []
    );

    const table = useTableRenderer({
        columns: columns,
        data: tableData,
        enableMultiRowSelection: true,
        onRowSelectionChange,
        state: { columnVisibility },
        onColumnVisibilityChange: setColumnVisibility,
        actionMenu: ActionMenu,
    });

    return (
        <Box
            background="white-0"
            borderRadius="md"
            gridColumn={gridColumn}
            padding="md"
        >
            <Box display="flex" justifyContent="space-between" mb="sm">
                <Heading
                    as="h1"
                    size="H1"
                    display="flex"
                    alignItems="center"
                    gap="5px"
                    pb="sm"
                >
                    <NtcThumbnailIcon width="25px" height="30px" /> {tableTitle}
                </Heading>
                <ButtonGroup pb="sm" alignItems="center">
                    <UIButton size="sm" variant="secondary">
                        Filters
                    </UIButton>
                    <UIButton
                        size="sm"
                        variant="primary"
                        leftIcon={<MeatballsIcon />}
                    >
                        Actions
                    </UIButton>
                    <Icon.TbMinusVertical />
                    <RouterButton
                        to={`${location.pathname}add`}
                        size="sm"
                        leftIcon={<PlusIcon />}
                    >
                        Add {tableTitle}
                    </RouterButton>
                </ButtonGroup>
            </Box>

            <TableRenderer
                table={table}
                containerProps={{ overflow: "auto" }}
            />
            {/* <Paginator
                url={location.pathname}
                data_count={totalCount}
                page_size={page_size}
                active_page={active_page_number}
            ></Paginator> */}
        </Box>
    );
}
