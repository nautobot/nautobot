import { useParams, useLocation, useSearchParams } from "react-router-dom";
import { Text } from "@nautobot/nautobot-ui";
import { LoadingWidget } from "@components/common/LoadingWidget";

import ObjectListTable from "@components/common/ObjectListTable";

import useSWR from "swr";
const fetcher = (...urls) => {
    const f = (url) =>
        fetch(url, { credentials: "include" })
            .then((r) => r.json())
            .catch((r) => r);
    return Promise.all(urls.map((url) => f(url)));
};

export default function GenericObjectListView() {
    const { app_name, model_name } = useParams();
    const { [0]: searchParams } = useSearchParams();

    // TODO: If we can solve the dynamic API of RTK-Query we won't need to construct the API URLs
    const list_url = `/api/${app_name}/${model_name}/`;
    const headers_url = list_url + "table-fields/";

    // Current fetcher allows to be passed multiple endpoints and fetch them at once
    const urls = [list_url, headers_url];
    const {
        data = [{}, {}],
        error,
        isLoading: isLoadingData,
    } = useSWR(urls, fetcher);
    const { [0]: tableData, [1]: tableFields } = data;

    // What page are we on?
    // TODO: Pagination handling should be it's own function so it's testable
    let page_size = 50;
    let active_page_number = 0;
    if (searchParams.get("limit")) {
        list_url += `?limit=${searchParams.get("limit")}`;
        page_size = searchParams.get("limit");
    }
    if (searchParams.get("offset")) {
        list_url += `&offset=${searchParams.get("offset")}`;
        active_page_number = searchParams.get("offset") / page_size;
    }

    if (!app_name || !model_name) {
        return <LoadingWidget />;
    }

    // ===
    // TODO: This has promise for the RTK-Query Pattern and a global API and cache manager
    //   ...but has an issue when the route is changed it won't run the query for the new view
    //   something is not registering the need to make the new query and subscribe to the new
    //   query objects.
    //   Keeping this here because it's _almost_ working...
    //
    // --- Imports for the following pattern
    // import { apiNameSlugger } from "@utils/api"
    // ---
    // const sluggedName = apiNameSlugger(model_name);
    // const useDataQuery = globalApi.endpoints[sluggedName+"_fields"].useQuery
    // const useFieldsQuery = globalApi.endpoints[sluggedName+"_fields"].useQuery
    // const { data: tableData, isSuccess: isTableDataSuccess, refetch: refetchData } = useDataQuery()
    // const { data: tableFields, isSuccess: isTableFieldsSuccess, refetch: refetchFields } = useFieldsQuery()
    // ===

    // TODO: Move to RTK-Query pattern (see api.js)
    //   This doesn't currently use a global state manager which is 😭

    if (isLoadingData || !tableData.results || !tableFields.data) {
        return <LoadingWidget name={model_name} />;
    }

    if (error) {
        return <Text>Error loading.</Text>;
    }

    return (
        <ObjectListTable
            tableData={tableData.results}
            tableHeader={tableFields.data}
            totalCount={tableData.count}
            active_page_number={active_page_number}
            page_size={page_size}
        />
    );
}
