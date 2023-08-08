import { Box, Flex } from "@nautobot/nautobot-ui";
import { Spacer } from "@chakra-ui/react";
import React, { useEffect, useState } from "react";

import { PageSizeForm, PageNumberForm } from "@components/Pagination";

function Pagination(props) {
    const [page_size, setPageSize] = useState(props.page_size);
    const [num_pages, setNumPages] = useState(
        calculateNumPages(props.data_count, props.page_size)
    );

    useEffect(() => {
        // This effect runs whenever the page_size prop changes
        setPageSize(props.page_size);
    }, [props.page_size]);

    useEffect(() => {
        // This effect runs whenever the page_size or data_count prop changes
        setNumPages(calculateNumPages(props.data_count, page_size));
    }, [page_size, props.data_count]);

    let data_count = props.data_count;
    let scroll_ref = props.scroll_ref;
    let active_page = props.active_page;
    if (!active_page) {
        active_page = 0;
    }

    // trueCurrentPage increments active_page (which starts at 0) by 1 to get the accurate human-form page number
    let trueCurrentPage = ~~active_page + 1;

    function calculateNumPages(data_count, page_size) {
        let num_pages;

        if (data_count % page_size === 0) {
            num_pages = data_count / page_size;
        } else {
            num_pages = data_count / page_size + 1;
        }

        // Convert float to int
        num_pages = ~~num_pages;

        return num_pages;
    }

    return (
        <Flex paddingTop={10}>
            <Box>
                <PageNumberForm
                    firstPage={1}
                    lastPage={num_pages}
                    pageSize={page_size}
                    scroll_ref={scroll_ref}
                    totalDataCount={data_count}
                    trueCurrentPage={trueCurrentPage}
                ></PageNumberForm>
            </Box>
            <Spacer />
            <Box>
                <PageSizeForm scroll_ref={scroll_ref}></PageSizeForm>
            </Box>
        </Flex>
    );
}
export default Pagination;
