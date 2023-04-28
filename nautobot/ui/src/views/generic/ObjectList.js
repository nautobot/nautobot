import { useParams } from "react-router-dom";
import { Text } from "@nautobot/nautobot-ui";
import { useDispatch } from "react-redux";

import { LoadingWidget } from "@components/LoadingWidget";
import ObjectListTable from "@components/ObjectListTable";
import GenericView from "@views/generic/GenericView";
import { useGetUIMenuQuery, useGetRESTAPIQuery } from "@utils/api";
import { updateAppContext } from "@utils/store";

export default function GenericObjectListView() {
    const { app_name, model_name } = useParams();
    // const { 0: searchParams } = useSearchParams(); // import { useSearchParams } from "react-router-dom";
    const { data: listData, isLoading: listDataLoading } = useGetRESTAPIQuery({
        app_name: app_name,
        model_name: model_name,
    });
    const { data: headerData, isLoading: headerDataLoading } =
        useGetRESTAPIQuery({
            app_name: app_name,
            model_name: model_name,
            schema: true,
        });

    const {
        data: menuInfo,
        isSuccess: isMenuSuccess,
        isError: isMenuError,
    } = useGetUIMenuQuery();
    const dispatch = useDispatch();

    if (isMenuError) return <div>Failed to load menu</div>;
    if (!isMenuSuccess) return <span>Loading...</span>;

    // Construct reverse-lookup from URL patterns to menu context
    var urlPatternToContext = {};
    for (const context in menuInfo) {
        for (const group in menuInfo[context].groups) {
            for (const urlPatternOrSubGroup in menuInfo[context].groups[group]
                .items) {
                if (urlPatternOrSubGroup.startsWith("/")) {
                    // It's a URL pattern
                    let tokens = urlPatternOrSubGroup.split("/");
                    if (tokens.length === 4) {
                        let appLabel = tokens[1];
                        let modelNamePlural = tokens[2];
                        if (appLabel in urlPatternToContext === false) {
                            urlPatternToContext[appLabel] = {};
                        }
                        urlPatternToContext[appLabel][modelNamePlural] =
                            context;
                    }
                } else {
                    // It's a submenu
                    const subGroup = urlPatternOrSubGroup;
                    for (const urlPattern in menuInfo[context].groups[group]
                        .items[subGroup].items) {
                        let tokens = urlPattern.split("/");
                        if (tokens.length === 4) {
                            let appLabel = tokens[1];
                            let modelNamePlural = tokens[2];
                            if (appLabel in urlPatternToContext === false) {
                                urlPatternToContext[appLabel] = {};
                            }
                            urlPatternToContext[appLabel][modelNamePlural] =
                                context;
                        }
                    }
                }
            }
        }
    }

    // What page are we on?
    // TODO: Pagination handling should be it's own function so it's testable
    // let page_size = 50;
    // let active_page_number = 0;
    // if (searchParams.get("limit")) {
    //     list_url += `?limit=${searchParams.get("limit")}`;
    //     page_size = searchParams.get("limit");
    // }
    // if (searchParams.get("offset")) {
    //     list_url += `&offset=${searchParams.get("offset")}`;
    //     active_page_number = searchParams.get("offset") / page_size;
    // }

    if (!app_name || !model_name) {
        return (
            <GenericView>
                <LoadingWidget />
            </GenericView>
        );
    }

    dispatch(updateAppContext(urlPatternToContext[app_name][model_name]));

    if (listDataLoading || headerDataLoading) {
        return (
            <GenericView>
                <LoadingWidget name={model_name} />
            </GenericView>
        );
    }

    if (!listData || !headerData) {
        return (
            <GenericView>
                <Text>Error loading.</Text>
            </GenericView>
        );
    }

    const transformedHeaders = Object.entries(headerData.schema.properties).map(
        ([key, value]) => {
            return { name: key, label: value.title };
        }
    );
    let defaultHeaders = headerData.view_options.list_display;

    // If list_display is not defined or empty, default to showing all headers.
    if (!defaultHeaders.length) {
        defaultHeaders = transformedHeaders;
    }

    let table_name = model_name
        .split("-")
        .map((x) => (x ? x[0].toUpperCase() + x.slice(1) : ""))
        .join(" ");
    return (
        <GenericView>
            <ObjectListTable
                tableData={listData.results}
                defaultHeaders={defaultHeaders}
                tableHeaders={transformedHeaders}
                totalCount={listData.count}
                active_page_number={1}
                page_size={50}
                tableTitle={table_name}
            />
        </GenericView>
    );
}
