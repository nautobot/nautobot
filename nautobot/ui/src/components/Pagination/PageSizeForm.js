import React from "react";
import { Flex, Text, Select } from "@nautobot/nautobot-ui";
import { useSearchParams } from "react-router-dom";

export default function PageSizeForm({ scroll_ref }) {
    let [searchParams, setSearchParams] = useSearchParams();
    function onPageSizeChange(event) {
        let initialOffset = parseInt(searchParams.get("offset"));

        let newLimit = event.target.value;
        let newOffset;

        let offsetModulo = initialOffset % newLimit;

        // Properly sets the new offset based on the new limit and old offset
        if (offsetModulo !== 0) {
            newOffset = initialOffset - offsetModulo;
        } else {
            newOffset = initialOffset;
        }

        // Scroll to the top of the ObjectListTable Container on table reload
        scroll_ref.current.scrollIntoView({
            alignToTop: true,
            behavior: "smooth",
        });

        setSearchParams({
            limit: newLimit,
            offset: newOffset ? newOffset : 0,
        });
    }

    return (
        <Flex align="center">
            <Text color="gray-3" pr="sm">
                Show
            </Text>
            <Select
                value={
                    searchParams.get("limit") ? searchParams.get("limit") : "50"
                }
                onChange={onPageSizeChange}
            >
                {/*
                    TODO: we need a REST API endpoint to query get_settings_or_config("PER_PAGE_DEFAULTS")
                    rather than hard-coding this.
                */}
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
                <option value="200">200</option>
                <option value="500">500</option>
            </Select>
            <Text color="gray-3" pl="sm" whiteSpace="nowrap">
                rows per page
            </Text>
        </Flex>
    );
}
