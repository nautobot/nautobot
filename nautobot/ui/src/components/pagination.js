import React from "react";
import { usePagination } from "./usePagination";
import { useSearchParams } from "react-router-dom";
import { Button } from "@nautobot/nautobot-ui";

export default function Pagination({
    totalDataCount,
    siblingCount = 1,
    currentPage,
    pageSize,
}) {
    let [searchParams, setSearchParams] = useSearchParams();

    const paginationRange = usePagination({
        currentPage,
        totalDataCount,
        siblingCount,
        pageSize,
    });

    // If there is only one/zero page in the pagination range, we do not render anything.
    if (paginationRange.length < 2) {
        return null;
    }
    function onPageNumberChange(pageNumber) {
        let limit = searchParams.get("limit");
        /* TODO: we need a REST API endpoint to query get_settings_or_config("PAGINATE_COUNT") rather than hard-coding this to 50. */
        setSearchParams({
            offset: pageSize * (pageNumber - 1),
            limit: limit ? limit : 50,
        });
    }
    currentPage = ~~currentPage;

    let lastPage = totalDataCount / pageSize;
    lastPage = ~~lastPage + 1;
    let firstPage = 1;

    const ul_css = {
        display: "flex",
        "list-style-type": "none",
    };
    const li_css = {
        padding: "2px",
    };

    return (
        <ul style={ul_css}>
            <li style={li_css} onClick={() => onPageNumberChange(firstPage)}>
                <Button variant="secondary">{"<"}</Button>
            </li>
            {paginationRange.map((pageNumber) => {
                if (pageNumber === "...") {
                    return (
                        <li style={li_css}>
                            <Button variant="secondary">&#8230;</Button>
                        </li>
                    );
                }
                // pageNumber (starts from 1) is always one greater than the currentPage (starts from 0)
                // we add one here to make sure that the correct pageNumber is highlighted.
                if (pageNumber === currentPage + 1) {
                    return (
                        <li
                            style={li_css}
                            onClick={() => onPageNumberChange(pageNumber)}
                        >
                            <Button variant="primary">{pageNumber}</Button>
                        </li>
                    );
                } else {
                    return (
                        <li
                            style={li_css}
                            onClick={() => onPageNumberChange(pageNumber)}
                        >
                            <Button variant="secondary">{pageNumber}</Button>
                        </li>
                    );
                }
            })}
            <li style={li_css} onClick={() => onPageNumberChange(lastPage)}>
                <Button variant="secondary">{">"}</Button>
            </li>
        </ul>
    );
}
