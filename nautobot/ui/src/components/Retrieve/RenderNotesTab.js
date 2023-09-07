import useSWR from "swr";
import {
    Heading,
    NautobotGrid,
    NautobotGridItem,
    NtcThumbnailIcon,
} from "@nautobot/nautobot-ui";
import { SkeletonText } from "@chakra-ui/react";

import { useGetRESTAPIQuery, fetcher } from "@utils/api";
import { ObjectTable } from "../ObjectTable";

export default function RenderNotesTab(props) {
    const { app_label, model_name, object_id, isPluginView } = props;
    const pluginPrefix = isPluginView ? "plugins/" : "";
    const notes_url = `/api/${pluginPrefix}${app_label}/${model_name}/${object_id}/notes/`;
    const { data, isLoading, isFetching, error } = useSWR(
        () => notes_url,
        fetcher
    );
    const {
        data: schema,
        isFetching: schemaIsFetching,
        isLoading: schemaIsLoading,
        isError: schemaIsError,
    } = useGetRESTAPIQuery({
        app_label: "extras",
        model_name: "notes",
        schema: true,
    });

    if (isLoading || isFetching || schemaIsFetching || schemaIsLoading) {
        return (
            <SkeletonText
                endColor="gray.300"
                noOfLines={10}
                skeletonHeight="25"
                spacing="3"
                mt="3"
            />
        );
    }

    if (error || schemaIsError) {
        return <div>Failed to load Notes Data</div>;
    }

    const defaultHeaders = schema.view_options.list_display_fields;
    const tableHeaders = schema.view_options.fields;
    const tableData = data?.results || [];

    return (
        <NautobotGrid columns="4">
            <NautobotGridItem>
                <Heading display="flex" alignItems="center" gap="5px">
                    <NtcThumbnailIcon width="25px" height="30px" /> Notes
                </Heading>
                <ObjectTable
                    defaultHeaders={defaultHeaders}
                    tableHeaders={tableHeaders}
                    tableData={tableData}
                />
            </NautobotGridItem>
        </NautobotGrid>
    );
}
