import { createApi, fetchBaseQuery, retry } from "@reduxjs/toolkit/query/react";
import {
    API_BASE,
    API_OBJECT_COUNTS,
    API_USER_SESSION_INFO,
    API_UI_MENU_INFO,
    API_UI_READY_ROUTES,
    API_USER_AUTHENTICATE,
    AUTH_LOGOUT,
} from "@constants/apiPath";

/*
  The one true API!

  Using Redux's RTK Query making fetching and caching a breeze! This will provide hooks and wires automagically.

  A standardized convention for retrieving data which should make developer's lives easier and is already extensively documented
  in React and Redux's sites.
*/

/**
 * A custom baseQuery that will retry requests that fail with a 5xx error code.
 *
 * @param {Object} args - The arguments passed to the query.
 * @param {Object} api - The API object.
 * @param {Object} extraOptions - Extra options passed to the query.
 * @returns {Object} - The result of the query.
 */
const smartRetryBaseQuery = retry(
    async (args, api, extraOptions) => {
        const result = await fetchBaseQuery({ baseUrl: "" })(
            args,
            api,
            extraOptions
        );
        const dontRetryHeaders = [400, 401, 403, 404, 405, 406, 407];
        if (dontRetryHeaders.includes(result.error?.status)) {
            retry.fail(result.error);
        }
        return result;
    },
    {
        maxRetries: 5,
    }
);

/** The base RTK Query API object that will be used to create the endpoints. */
export const baseApi = createApi({
    baseQuery: smartRetryBaseQuery,
    endpoints: (builder) => ({
        /** The query to retrieve the session data. */
        getSession: builder.query({
            query: () => API_USER_SESSION_INFO,
            providesTags: ["Session"],
            invalidatesTags: ["APIData", "AppData"],
        }),
        /** The query to retrieve the menu data. */
        getUIMenu: builder.query({
            query: () => API_UI_MENU_INFO,
            providesTags: ["AppData"],
        }),
        /** The query to retrieve object counts (used on the homepage). */
        getObjectCounts: builder.query({
            query: () => API_OBJECT_COUNTS,
            providesTags: ["ObjectCounts"],
        }),
        /** The query to retrieve object data from RESTful API. */
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
        /** The mutation to log in */
        login: builder.mutation({
            query: ({ username, password }) => ({
                url: API_USER_AUTHENTICATE,
                method: "POST",
                body: { username, password },
            }),
        }),
        /** The mutation to log out. While is a GET, it changes data on the back-end */
        logout: builder.mutation({
            query: () => ({
                url: AUTH_LOGOUT,
                method: "GET",
            }),
        }),
        getNewUIReadyRoutes: builder.query({
            query: () => ({
                url: API_UI_READY_ROUTES,
                method: "GET",
            }),
        }),
    }),
});

export const fetcher = (url) =>
    fetch(url, { credentials: "include" }).then((res) => {
        // We have to do this here because 4xx and 5xx errors
        // are considered as a successful request.
        if (!res.ok) {
            throw new Error("Something Went Wrong");
        } else {
            return res.json();
        }
    });

export const {
    useGetSessionQuery,
    useGetUIMenuQuery,
    useGetRESTAPIQuery,
    useGetObjectCountsQuery,
    useGetNewUIReadyRoutesQuery,
    useLoginMutation,
    useLogoutMutation,
} = baseApi;
