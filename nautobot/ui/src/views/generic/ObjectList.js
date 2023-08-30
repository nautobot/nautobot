import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { useLocation, useParams } from "react-router-dom";
import { NautobotGridItem, Text } from "@nautobot/nautobot-ui";

import { ObjectListTable } from "@components";
import GenericView from "@views/generic/GenericView";
import { useGetRESTAPIQuery } from "@utils/api";
import {
    updateCurrentContext,
    getCurrentAppContextSelector,
} from "@utils/store";

export default function GenericObjectListView() {
    const { app_label, model_name } = useParams();
    const dispatch = useDispatch();
    const location = useLocation();
    const currentAppContext = useSelector(
        getCurrentAppContextSelector(app_label, model_name)
    );
    const isPluginView = location.pathname.includes("/plugins/");
    useEffect(() => {
        dispatch(updateCurrentContext(currentAppContext));
    }, [dispatch, currentAppContext]);

    // const { 0: searchParams } = useSearchParams(); // import { useSearchParams } from "react-router-dom";

    const {
        data: headerData,
        isLoading: headerDataLoading,
        isFetching: headerDataFetching,
    } = useGetRESTAPIQuery(
        {
            app_label: app_label,
            model_name: model_name,
            schema: true,
            plugin: isPluginView,
        },
        { keepUnusedDataFor: 600 } // Let's keep the header schema cached for longer than the default 60 seconds
    );
    let [searchParams] = useSearchParams();

    // What page are we on?
    // TODO: Pagination handling should be it's own function so it's testable
    let page_size = 50;
    let active_page_number = 0;
    let searchQuery = {
        app_label: app_label,
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

    let data_loaded = !(
        listDataLoading ||
        headerDataLoading ||
        headerDataFetching
    );
    let data_fetched = !listDataFetching;

    if (!data_loaded) {
        return (
            <GenericView gridBackground="white-0">
                {(menuPath) => (
                    <NautobotGridItem>
                        <ObjectListTable
                            tableData={{}}
                            defaultHeaders={[]}
                            tableHeaders={[]}
                            totalCount={0}
                            active_page_number={active_page_number}
                            page_size={page_size}
                            tableTitle={menuPath[menuPath.length - 1]}
                            data_loaded={data_loaded}
                            data_fetched={data_fetched}
                        />
                    </NautobotGridItem>
                )}
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
        <GenericView gridBackground="white-0">
            {(menuPath) => (
                <NautobotGridItem>
                    {/* TODO(timizuo): Use @component/ObjectTable instead, after pagination control has been added to @component/ObjectTable */}
                    <ObjectListTable
                        tableData={listData.results}
                        defaultHeaders={defaultHeaders}
                        tableHeaders={tableHeaders}
                        totalCount={listData.count}
                        active_page_number={active_page_number}
                        page_size={page_size}
                        tableTitle={menuPath[menuPath.length - 1]}
                        data_loaded={data_loaded}
                        data_fetched={data_fetched}
                    />
                </NautobotGridItem>
            )}
        </GenericView>
    );
}
