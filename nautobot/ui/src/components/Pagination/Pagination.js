import { Box, Flex } from "@nautobot/nautobot-ui";
import { Spacer } from "@chakra-ui/react";
import React, { useState } from "react";

import { PageSizeForm, PageNumberForm } from "@components/Pagination";

function Pagination(props) {
    const [page_size] = useState(props.page_size);

    let data_count = props.data_count;
    let scroll_ref = props.scroll_ref;
    let active_page = props.active_page;
    if (!active_page) {
        active_page = 0;
    }
    let num_pages;

    // trueCurrentPage increments active_page (which starts at 0) by 1 to get the accurate human-form page number
    let trueCurrentPage = ~~active_page + 1;

    if (data_count % page_size === 0) {
        num_pages = data_count / page_size;
    } else {
        num_pages = data_count / page_size + 1;
    }

    // convert float to int
    num_pages = ~~num_pages;

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
