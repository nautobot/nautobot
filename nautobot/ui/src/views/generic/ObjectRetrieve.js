import { useLocation, useParams } from "react-router-dom";
import { SkeletonText } from "@chakra-ui/react"; // TODO: use nautobot-ui when available
import { Box } from "@nautobot/nautobot-ui";

import { useGetRESTAPIQuery } from "@utils/api";
import GenericView from "@views/generic/GenericView";
import { AppComponents, RenderHeader, RenderTabs } from "@components";

export default function ObjectRetrieve({ api_url }) {
    const { app_label, model_name, object_id } = useParams();
    const location = useLocation();
    const isPluginView = location.pathname.includes("/plugins/");
    const { data, isLoading, isError } = useGetRESTAPIQuery({
        app_label,
        model_name,
        uuid: object_id,
        plugin: isPluginView,
    });
    const {
        data: schemaData,
        isLoading: schemaIsLoading,
        isError: schemaIsError,
    } = useGetRESTAPIQuery({
        app_label,
        model_name,
        uuid: object_id,
        schema: true,
        plugin: isPluginView,
    });

    const route_name = `${app_label}:${model_name}`;

    if (isLoading || schemaIsLoading) {
        return (
            <GenericView>
                <SkeletonText
                    endColor="gray.300"
                    noOfLines={10}
                    skeletonHeight="25"
                    spacing="3"
                    mt="3"
                ></SkeletonText>
            </GenericView>
        );
    }

    if (isError || schemaIsError) {
        return (
            <GenericView objectData={data}>
                <div>Failed to load {api_url}</div>
            </GenericView>
        );
    }

    if (
        AppComponents.CustomViews?.[route_name] &&
        "retrieve" in AppComponents.CustomViews?.[route_name]
    ) {
        const CustomView = AppComponents.CustomViews[route_name].retrieve;
        return <CustomView {...data} />;
    }

    // NOTE: This acts as a schema that would be gotten form an OPTIONS call,
    // which loads the tabs and its layout schema.
    const objectRetrieveTabSchema = {
        tabs: {
            [`${schemaData.name}`]: schemaData.view_options.retrieve,
            Advanced: schemaData.view_options.advanced,
        },
    };

    return (
        <GenericView objectData={data} key={window.location.pathname}>
            <Box background="white-0" borderRadius="md">
                <RenderHeader data={data} />
                <RenderTabs
                    schema={schemaData.schema.properties}
                    layoutSchema={objectRetrieveTabSchema}
                    data={data}
                    app_label={app_label}
                    model_name={model_name}
                    object_id={object_id}
                    isPluginView={isPluginView}
                />
            </Box>
        </GenericView>
    );
}
