import { ButtonGroup, Flex, SkeletonText, Spacer } from "@chakra-ui/react";
import * as Icon from "react-icons/tb";
import { useLocation } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
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
    Text,
} from "@nautobot/nautobot-ui";
import { useCallback, useMemo } from "react";

import LoadingWidget from "../LoadingWidget";
import ObjectTableItem from "./ObjectTableItem";
import { useFiltersPanel } from "@components/FiltersPanel";
import { Pagination } from "@components/Pagination";

const getTableItemLink = (idx, obj) => {
    if (idx === 0) {
        // TODO: ui-schema should be providing the name of the field used to describe the object (name)
        return window.location.pathname + obj.id + "/";
    }
    if (typeof obj !== "object" || !obj || !obj.url) {
        return null;
    }
    // Remove domain + /api prefix
    const url = obj.url.replace(window.location.origin + "/api", "");

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
    tableTitle,
    data_loaded,
    data_fetched,
    include_button = true,
}) {
    let location = useLocation();
    const columnHelper = useMemo(() => createColumnHelper(), []);
    // Reference point to scroll to on table reload
    const topRef = useRef();

    const [columnVisibility, setColumnVisibility] = useState({});
    useEffect(() => {
        let defaultNames = defaultHeaders.map((e) => e.key);
        let allNames = tableHeaders.map((e) => e.key);

        if (defaultNames.length === 0) {
            defaultNames = allNames;
        }
        let disabledNames = allNames.filter((v) => !defaultNames.includes(v));
        let columnState = {};
        for (const key of disabledNames) {
            columnState[key] = false;
        }
        setColumnVisibility(columnState);
    }, [defaultHeaders, tableHeaders]);
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
                            <ObjectTableItem
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

    const filtersPanel = useFiltersPanel({
        content: <Text>You have successfully opened filters panel.</Text>,
        id: "object-list-table-filters-panel",
        title: "Filters",
    });

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
        <Box borderRadius="md" ref={topRef}>
            {!include_button ? null : (
                <Flex align="center" height="60px">
                    <Heading
                        as="h1"
                        size="H1"
                        display="flex"
                        alignItems="center"
                        gap="5px"
                    >
                        <NtcThumbnailIcon width="25px" height="30px" />{" "}
                        {tableTitle}
                    </Heading>
                    <Spacer />
                    {!data_fetched ? (
                        <Box pr="sm">
                            <LoadingWidget name={tableTitle} />
                        </Box>
                    ) : (
                        () => {}
                    )}
                    <Box>
                        <ButtonGroup alignItems="center">
                            <UIButton
                                size="sm"
                                variant="secondary"
                                onClick={() =>
                                    filtersPanel.isOpen
                                        ? filtersPanel.close()
                                        : filtersPanel.open()
                                }
                            >
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
                            <UIButton
                                to={`${location.pathname}add/`}
                                size="sm"
                                leftIcon={<PlusIcon />}
                                onClick={(e) => {
                                    e.preventDefault();
                                    // Because there is currently no support for Add view in the new UI for production,
                                    // the code below checks if the app is running in production and redirects the user to
                                    // the Add page; after the page is reloaded, nautobot takes care of rendering the legacy UI.
                                    // TODO: Get rid of this if statement when we have a Create/Update View in the new UI
                                    if (process.env.NODE_ENV === "production") {
                                        document.location.href += "add/";
                                    }
                                }}
                            >
                                Add {tableTitle}
                            </UIButton>
                        </ButtonGroup>
                    </Box>
                </Flex>
            )}

            <SkeletonText
                endColor="gray.200"
                noOfLines={parseInt(page_size)}
                skeletonHeight="25"
                spacing="3"
                mt="3"
                isLoaded={data_fetched}
            >
                <TableRenderer
                    table={table}
                    containerProps={{ overflow: "auto" }}
                />
            </SkeletonText>
            <Pagination
                url={location.pathname}
                data_count={totalCount}
                page_size={page_size}
                active_page={active_page_number}
                scroll_ref={topRef}
            ></Pagination>
        </Box>
    );
}
