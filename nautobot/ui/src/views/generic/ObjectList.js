import { useLocation, useParams } from "react-router-dom";
import { NautobotGridItem, Text } from "@nautobot/nautobot-ui";
import { useDispatch } from "react-redux";
import ObjectListTable from "@components/ObjectListTable";
import GenericView from "@views/generic/GenericView";
import { useGetRESTAPIQuery } from "@utils/api";
import { useEffect } from "react";
import {
    updateAppCurrentContext,
    getCurrentAppContextSelector,
} from "@utils/store";
import { toTitleCase } from "@utils/string";
import { useSelector } from "react-redux";
import { useSearchParams } from "react-router-dom";

export default function GenericObjectListView() {
    const { app_name, model_name } = useParams();
    const dispatch = useDispatch();
    const location = useLocation();
    const currentAppContext = useSelector(
        getCurrentAppContextSelector(app_name, model_name)
    );
    const isPluginView = location.pathname.includes("/plugins/");
    useEffect(() => {
        dispatch(updateAppCurrentContext(currentAppContext));
    }, [dispatch, currentAppContext]);

    // const { 0: searchParams } = useSearchParams(); // import { useSearchParams } from "react-router-dom";
    const {
        data: headerData,
        isLoading: headerDataLoading,
        isFetching: headerDataFetching,
    } = useGetRESTAPIQuery({
        app_name: app_name,
        model_name: model_name,
        schema: true,
        plugin: isPluginView,
    });
    let [searchParams] = useSearchParams();

    // What page are we on?
    // TODO: Pagination handling should be it's own function so it's testable
    let page_size = 50;
    let active_page_number = 0;
    let searchQuery = {
        app_name: app_name,
        model_name: model_name,
        plugin: isPluginView,
    };
    if (searchParams.get("limit")) {
        searchQuery.limit = searchParams.get("limit");
        page_size = searchParams.get("limit");
    }
    if (searchParams.get("offset")) {
        searchQuery.offset = searchParams.get("offset");
        active_page_number = searchParams.get("offset") / page_size;
    }
    const {
        data: listData,
        isLoading: listDataLoading,
        isFetching: listDataFetching,
    } = useGetRESTAPIQuery(searchQuery);

    // TODO when are we going to run into this?
    // if (!app_name || !model_name) {
    //     return (
    //         <GenericView>
    //             <LoadingWidget />
    //         </GenericView>
    //     );
    // }
    let data_loaded = !(
        listDataLoading ||
        headerDataLoading ||
        headerDataFetching
    );
    let data_fetched = !listDataFetching;

    let table_name = toTitleCase(model_name, "-");
    if (!data_loaded) {
        return (
            <GenericView>
                <NautobotGridItem>
                    <ObjectListTable
                        tableData={{}}
                        defaultHeaders={[]}
                        tableHeaders={[]}
                        totalCount={0}
                        active_page_number={active_page_number}
                        page_size={page_size}
                        tableTitle={table_name}
                        data_loaded={data_loaded}
                        data_fetched={data_fetched}
                    />
                </NautobotGridItem>
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
    // tableHeaders = all fields; and defaultHeaders = only the ones we want to see at first.
    const tableHeaders = headerData.view_options.fields;
    let defaultHeaders = headerData.view_options.list_display_fields;

    // If list_display_fields is not defined or empty, default to showing all headers.
    if (!defaultHeaders.length) {
        defaultHeaders = tableHeaders;
    }
    return (
        <GenericView>
            <NautobotGridItem>
                <ObjectListTable
                    tableData={listData.results}
                    defaultHeaders={defaultHeaders}
                    tableHeaders={tableHeaders}
                    totalCount={listData.count}
                    active_page_number={active_page_number}
                    page_size={page_size}
                    tableTitle={table_name}
                    data_loaded={data_loaded}
                    data_fetched={data_fetched}
                />
            </NautobotGridItem>
        </GenericView>
    );
}
