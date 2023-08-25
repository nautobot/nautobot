import { useEffect, useState, useMemo, useCallback } from "react";
import {
    TableRenderer,
    useTableRenderer,
    createColumnHelper,
    Button,
    EditIcon,
} from "@nautobot/nautobot-ui";

import ObjectTableItem from "./ObjectTableItem";

function getTableItemLink(idx, obj) {
    if (typeof obj !== "object" || !obj || !obj.url) {
        return null;
    }
    // Remove domain + /api prefix
    return obj.url.replace(window.location.origin + "/api", "");
}

function createTableColumn(tableHeaders, columnHelper) {
    return tableHeaders.map(({ key, title }, idx) =>
        columnHelper.accessor(key, {
            cell: (props) => {
                // Get the column data from the object
                // e.g from {status: {display: "Active", id: 1, ...}, id: ....} get => {display: "Active", id: 1}
                // In the example above it gets the col(status) value
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
    );
}

function renderActionButton({ cellContext }) {
    return (
        <Button
            leftIcon={<EditIcon size="sm" />}
            size="xs"
            variant="table"
            onClick={() => alert(`Clicked ${cellContext.row.original.name}!`)}
        />
    );
}

// A standard Nautobot Object table. This _may_ be beneficial to move into nautobot-ui
export default function ObjectTable({
    defaultHeaders,
    tableHeaders,
    tableData,
}) {
    const columnHelper = useMemo(() => createColumnHelper(), []);
    const [columnVisibility, setColumnVisibility] = useState({});
    const columns = useMemo(
        () => createTableColumn(tableHeaders, columnHelper),
        [columnHelper, tableHeaders]
    );
    const ActionMenu = useCallback(renderActionButton, []);

    useEffect(() => {
        let allNames = tableHeaders.map((e) => e.key);
        let defaultNames = defaultHeaders.map((e) => e.key);

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

    const table = useTableRenderer({
        columns: columns,
        data: tableData,
        enableMultiRowSelection: true,
        state: { columnVisibility },
        onColumnVisibilityChange: setColumnVisibility,
        actionMenu: ActionMenu,
    });

    return (
        <TableRenderer table={table} containerProps={{ overflow: "auto" }} />
    );
}
