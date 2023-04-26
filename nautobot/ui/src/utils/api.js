// Import the RTK Query methods from the React-specific entry point
import { createApi, fetchBaseQuery, retry } from "@reduxjs/toolkit/query/react";
import {
    API_BASE,
    API_USER_SESSION_INFO,
    API_UI_MENU_INFO,
} from "@constants/apiPath";

/*
  The one true API!

  Using Redux's RTK Query making fetching and caching a breeze! This will provide hooks and wires automagically.

  A standardized convention for retrieving data which should make developer's lives easier and is already extensively documented
  in React and Redux's sites.
*/

const staggeredBaseQuery = retry(fetchBaseQuery({ baseUrl: API_BASE }), {
    maxRetries: 5,
});

export const baseApi = createApi({
    baseQuery: staggeredBaseQuery,
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
        getRESTAPI: builder.query({
            query: ({ app_name, model_name, uuid = null, schema = false }) => {
                if (schema) {
                    return {
                        url: `${app_name}/${model_name}/`,
                        method: "OPTIONS",
                    };
                }
                if (uuid) {
                    return {
                        url: `${app_name}/${model_name}/${uuid}/?depth=1`,
                    };
                }
                return { url: `${app_name}/${model_name}/?depth=1` };
            },
            providesTags: ["APIData"],
        }),
    }),
});

// Because the Session and Menu objects in the current iteration are used extensively we can export
//   their hooks to make retrieving them easier.
// Otherwise you can retrieve them via navigating baseApi:
//   import baseApi
//   baseApi.useGetSessionQuery
//   // or
//   baseApi.endpoints.getSession.getQuery
export const { useGetSessionQuery, useGetUIMenuQuery, useGetRESTAPIQuery } =
    baseApi;

// TODO: Below is a pattern for taking the menu API and building an entire RTK-Query API for it
// Few things need to be done here:
//   - If it's not in the menu, it doesn't get registered, that's a problem
//       we should probably have an endpoint to return all APIs and useful dictionary names
//   - Also, making an API call to make API calls in an asynchronous language is weird
//       can we not generate an API object just like we do for imports on UI build/post_upgrade?
//
// export function apiNameSlugger(name) {
//   return name.toLowerCase().trim().replace(/[^\w\s-]/g, '')
//   .replace(/[\s_-]+/g, '')
//   .replace(/^-+|-+$/g, '');
// }

// export function generateFullAPI(menuInfo) {

//   if(menuInfo === undefined) {
//     return baseApi
//   }
//   function buildEndpoints(build) {
//     const routes = menuInfo.map((tl_item) => {
//       return Object.entries(tl_item.properties.groups).map((group_item) => {
//         const { [1]: group_obj } = group_item
//         return Object.entries(group_obj.items).map((menu_item) => {
//           const { [0]: menu_route, [1]: menu_obj } = menu_item
//           const apiKeyName = apiNameSlugger(menu_obj.name)
//           return [[apiKeyName, menu_route], [apiKeyName+"_fields", menu_route+"table-fields/"]]
//         }).flat()
//       }).flat()
//     }).flat()
//     return routes.reduce((a, v) => (
//       { ...a , [v[0]]: build.query({ query: () => v[1]}) }
//       ), {});
//   }

//   const extendedAPI = baseApi.injectEndpoints({
//     endpoints: buildEndpoints,
//     overrideExisting: false
//   })

//   return extendedAPI
// }
