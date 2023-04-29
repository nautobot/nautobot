import React from "react";
import { Box, Text, Select } from "@nautobot/nautobot-ui";
import { useSearchParams } from "react-router-dom";

export default function PaginatorForm({ start, end, total_count }) {
    let [searchParams, setSearchParams] = useSearchParams();
    let paginator_string = `Showing ${start} - ${end} of ${total_count}`;
    // const { setType } = useState("PaginatorForm");
    function onPageSizeChange(event) {
      setSearchParams({limit: event.target.value});
    }

    return (
        <Box width="200px">
            <Select value={searchParams.get("limit")?(searchParams.get("limit")):("50")} onChange={onPageSizeChange}>
                <option value="50">50</option>
                <option value="100">100</option>
                <option value="200">200</option>
                <option value="500">500</option>
            </Select>
            <Text>{paginator_string}</Text>
        </Box>
    );
}