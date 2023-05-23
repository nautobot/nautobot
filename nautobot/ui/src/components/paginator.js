import { Frame } from "@nautobot/nautobot-ui";
import React from "react";

import PaginatorForm from "@components/paginator_form";
import Pagination from "@components/pagination";

import { NautobotGrid, NautobotGridItem } from "@nautobot/nautobot-ui";

class Paginator extends React.Component {
    constructor(props) {
        super(props);
        this.state = {};
    }

    render() {
        let num_pages;
        let data_count;
        let page_size;
        let active_page;
        let scroll_ref;
        data_count = this.props.data_count;
        active_page = this.props.active_page;
        scroll_ref = this.props.scroll_ref;
        if (!active_page) {
            active_page = 0;
        }

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
        let start_range;
        let end_range;

        if (active_page === num_pages - 1) {
            start_range = active_page * page_size + 1;
            end_range = data_count;
        } else {
            start_range = active_page * page_size + 1;
            end_range = (active_page + 1) * page_size;
        }

        return (
            <Frame>
                <NautobotGrid>
                    <NautobotGridItem colSpan="4">
                        <Pagination
                            totalDataCount={data_count}
                            currentPage={active_page}
                            pageSize={page_size}
                            scroll_ref={scroll_ref}
                        ></Pagination>
                    </NautobotGridItem>
                    <NautobotGridItem colSpan="4">
                        <PaginatorForm
                            start={start_range}
                            end={end_range}
                            total_count={data_count}
                            scroll_ref={scroll_ref}
                        ></PaginatorForm>
                    </NautobotGridItem>
                </NautobotGrid>
            </Frame>
        );
    }
}
export default Paginator;
