import { Box, Flex } from "@nautobot/nautobot-ui";
import { Spacer } from "@chakra-ui/react";
import React from "react";

import PageNumberForm from "@components/Pagination/PageNumberForm";
import PageSizeForm from "@components/Pagination/PageSizeForm";

class Pagination extends React.Component {
    constructor(props) {
        super(props);
        this.state = {};
    }

    render() {
        let data_count;
        let scroll_ref;
        let active_page;
        let page_size;
        let num_pages;

        data_count = this.props.data_count;
        scroll_ref = this.props.scroll_ref;
        active_page = this.props.active_page;
        if (!active_page) {
            active_page = 0;
        }

        // trueCurrentPage increments active_page (which starts at 0) by 1 to get the accurate human-form page number
        let trueCurrentPage = ~~active_page + 1;

        if (Object.keys(this.state).length === 0) {
            page_size = this.props.page_size;
        } else {
            page_size = this.state.page_size;
        }

        if (data_count % page_size === 0) {
            num_pages = data_count / page_size;
        } else {
            num_pages = data_count / page_size + 1;
        }
        // convert float to int
        num_pages = ~~num_pages;

        // const pages = [];

        // let list_url = url.split("?")[0]; // strip the query parameters to retain the original list url

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
}
export default Pagination;
