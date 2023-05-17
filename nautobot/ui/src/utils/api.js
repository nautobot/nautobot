// Import the RTK Query methods from the React-specific entry point
import { createApi, fetchBaseQuery, retry } from "@reduxjs/toolkit/query/react";
import {
    API_BASE,
    API_OBJECT_COUNTS,
    API_USER_SESSION_INFO,
    API_UI_MENU_INFO,
    API_USER_AUTHENTICATE,
    AUTH_LOGOUT,
} from "@constants/apiPath";

/*
  The one true API!

  Using Redux's RTK Query making fetching and caching a breeze! This will provide hooks and wires automagically.

  A standardized convention for retrieving data which should make developer's lives easier and is already extensively documented
  in React and Redux's sites.
*/

// eslint-disable-next-line no-unused-vars
const staggeredBaseQuery = retry(fetchBaseQuery({ baseUrl: "" }), {
    maxRetries: 5,
}); // TODO: Make this smarter on which conditions it retries on

export const baseApi = createApi({
    baseQuery: fetchBaseQuery({ baseUrl: "" }), // TODO: Restore staggeredBaseQuery
    keepUnusedDataFor: 5,
    refetchOnMountOrArgChange: true,
    refetchOnFocus: true,
    refetchOnReconnect: true,
    endpoints: (builder) => ({
        getSession: builder.query({
            query: () => API_USER_SESSION_INFO,
            providesTags: ["Session"],
            invalidatesTags: ["APIData", "AppData"],
        }),
        getUIMenu: builder.query({
            query: () => API_UI_MENU_INFO,
            providesTags: ["AppData"],
        }),
        getObjectCounts: builder.query({
            query: () => API_OBJECT_COUNTS,
            providesTags: ["ObjectCounts"],
        }),
        getRESTAPI: builder.query({
            query: ({
                app_label,
                model_name,
                uuid = null,
                schema = false,
                plugin = false,
                limit = null,
                offset = null,
                depth = 1,
            }) => {
                let url = `${API_BASE}/${
                    plugin ? "plugins/" : ""
                }${app_label}/${model_name}/`;
                let method = "GET";
                let queryParams = null;
                if (schema) {
                    method = "OPTIONS";
                } else {
                    if (uuid) {
                        url += `${uuid}/`;
                    }
                    queryParams = new URLSearchParams([["depth", depth]]);
                    if (limit) {
                        queryParams.append("limit", limit);
                    }
                    if (offset) {
                        queryParams.append("offset", offset);
                    }
                }

                if (queryParams) {
                    url += `?${queryParams.toString()}`;
                }

                return { url: url, method: method };
            },
            providesTags: ["APIData"],
        }),
        login: builder.mutation({
            query: ({ username, password }) => ({
                url: API_USER_AUTHENTICATE,
                method: "POST",
                body: { username, password },
            }),
        }),
        logout: builder.mutation({
            query: () => ({
                url: AUTH_LOGOUT,
                method: "GET",
            }),
        }),
    }),
});

export const {
    useGetSessionQuery,
    useGetUIMenuQuery,
    useGetRESTAPIQuery,
    useGetObjectCountsQuery,
    useLoginMutation,
    useLogoutMutation,
} = baseApi;
