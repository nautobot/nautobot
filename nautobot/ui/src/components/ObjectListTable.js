import { ButtonGroup, SkeletonText } from "@chakra-ui/react";
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
    useToast,
} from "@nautobot/nautobot-ui";
import Paginator from "@components/paginator";
import { useCallback, useMemo } from "react";

import TableItem from "@components/TableItem";
import LoadingWidget from "./LoadingWidget";

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

    const toast = useToast({
        duration: 5000,
        isClosable: true,
        position: "top-right",
        status: "success",
        description: "You have successfully made toast.",
        title: "Ta da!",
    });

    return (
        <Box background="white-0" borderRadius="md" padding="md" ref={topRef}>
            {!include_button ? null : (
                <Box display="flex" justifyContent="space-between" mb="sm">
                    <Heading
                        as="h1"
                        size="H1"
                        display="flex"
                        alignItems="center"
                        gap="5px"
                        pb="sm"
                    >
                        <NtcThumbnailIcon width="25px" height="30px" />{" "}
                        {tableTitle}
                    </Heading>
                    <ButtonGroup pb="sm" alignItems="center">
                        <UIButton size="sm" variant="secondary" onClick={toast}>
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
                                if (process.env.NODE_ENV === "production") {
                                    document.location.href += "add/";
                                }
                            }}
                        >
                            Add {tableTitle}
                        </UIButton>
                    </ButtonGroup>
                </Box>
            )}

            <SkeletonText
                endColor="gray.200"
                noOfLines={parseInt(page_size)}
                skeletonHeight="25"
                spacing="3"
                mt="3"
                isLoaded={data_loaded}
            >
                {!data_fetched && data_loaded ? (
                    <Box background="white-0" borderRadius="md" padding="md">
                        <LoadingWidget name={tableTitle} />
                    </Box>
                ) : (
                    () => {}
                )}
                <TableRenderer
                    table={table}
                    containerProps={{ overflow: "auto" }}
                />
            </SkeletonText>
            <Paginator
                url={location.pathname}
                data_count={totalCount}
                page_size={page_size}
                active_page={active_page_number}
                scroll_ref={topRef}
            ></Paginator>
        </Box>
    );
}
