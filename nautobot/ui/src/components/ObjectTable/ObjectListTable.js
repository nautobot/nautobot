import { ButtonGroup, SkeletonText, Spacer } from "@chakra-ui/react";
import { useLocation } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import {
    Box,
    calc,
    Divider,
    Flex,
    getCssVar,
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
    Tag,
    TagLabel,
} from "@nautobot/nautobot-ui";
import { useCallback, useMemo } from "react";

import {
    FiltersPanelContent,
    NON_FILTER_QUERY_PARAMS,
    useFiltersPanel,
} from "@components/FiltersPanel";
import { Pagination } from "@components/Pagination";

import LoadingWidget from "../LoadingWidget";
import ObjectTableItem from "./ObjectTableItem";

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
    objectType,
    tableHeaders,
    filterData,
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
        content: (
            <FiltersPanelContent
                lookupFields={filterData}
                objectType={objectType}
            />
        ),
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

    const activeFiltersCount = useMemo(
        () =>
            [...new URLSearchParams(location.search)].filter(
                ([searchParam]) =>
                    !NON_FILTER_QUERY_PARAMS.includes(searchParam)
            ).length,
        [location]
    );

    useEffect(() => {
        if (filtersPanel.isOpen) {
            // This re-renders the filters panel when it is already open and the
            // current `ObjectList` view collection is changed to another.
            filtersPanel.open();
        } // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [objectType, tableHeaders]);

    useEffect(
        () => () => {
            // This closes the filters panel when users navigate away from the
            // `ObjectList` view. Use `setTimeout` in order to delay the filters
            // panel closing function by one cycle. Otherwise, if called
            // immediately, some ancestor component lifecycle will mount it
            // again, effectively cancelling the `filtersPanel.close()` call.
            setTimeout(() => filtersPanel.close());
        }, // eslint-disable-next-line react-hooks/exhaustive-deps
        [] // Keep the dependency array empty to execute only on unmount.
    );

    return (
        <Box borderRadius="md" height="full" ref={topRef}>
            {!include_button ? null : (
                <Flex align="center">
                    <Heading
                        as="h1"
                        size="H1"
                        display="flex"
                        alignItems="center"
                        gap="5px"
                    >
                        <NtcThumbnailIcon height="auto" width="24" />
                        {tableTitle}
                    </Heading>
                    <Spacer />
                    {!data_fetched ? (
                        <Box marginRight="md">
                            <LoadingWidget name={tableTitle} />
                        </Box>
                    ) : null}
                    <Box>
                        <ButtonGroup alignItems="center" spacing="md">
                            <UIButton
                                variant={
                                    activeFiltersCount > 0
                                        ? "primary"
                                        : "secondary"
                                }
                                onClick={() =>
                                    filtersPanel.isOpen
                                        ? filtersPanel.close()
                                        : filtersPanel.open()
                                }
                            >
                                {activeFiltersCount > 0 ? (
                                    <Tag
                                        background="white-0"
                                        boxShadow="none"
                                        marginRight="xs"
                                        size="sm"
                                        variant="secondary"
                                    >
                                        <TagLabel>
                                            {activeFiltersCount}
                                        </TagLabel>
                                    </Tag>
                                ) : null}
                                Filters
                            </UIButton>
                            <UIButton
                                variant="primary"
                                leftIcon={<MeatballsIcon />}
                            >
                                Actions
                            </UIButton>
                            <Divider height={10} orientation="vertical" />
                            <UIButton
                                to={`${location.pathname}add/`}
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
                borderRadius="md"
                endColor="gray-0"
                height={calc.subtract(
                    getCssVar("sizes.full"),
                    // The following compensate for the section header.
                    getCssVar("lineHeights.tall"),
                    getCssVar("space.md"),
                    // The following compensate for the pagination component.
                    getCssVar("space.md"),
                    getCssVar("sizes.40")
                )}
                isLoaded={data_fetched}
                marginTop="md"
                noOfLines={parseInt(page_size, 10)}
                overflow="hidden"
                skeletonHeight={calc.subtract(
                    calc.add(
                        getCssVar("lineHeights.normal"),
                        calc.multiply(getCssVar("space.sm"), 2)
                    ),
                    "1px"
                )}
                spacing="1px"
                startColor="gray-1"
                sx={{
                    ">": {
                        _first: data_fetched
                            ? { height: "full" }
                            : { ">": { _first: { display: "none" } } },
                    },
                }}
            >
                <TableRenderer
                    table={table}
                    containerProps={{ height: "full" }}
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
