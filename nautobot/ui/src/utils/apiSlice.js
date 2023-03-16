// Import the RTK Query methods from the React-specific entry point
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'
import { API_BASE, API_USER_SESSION_INFO, API_UI_MENU_INFO } from '@constants/apiPath'

// Define our single API slice object
export const apiSlice = createApi({
  // The cache reducer expects to be added at `state.api` (already default - this is optional)
  reducerPath: 'api',
  // All of our requests will have URLs starting with '/fakeApi'
  baseQuery: fetchBaseQuery({ baseUrl: API_BASE }),
  // The "endpoints" represent operations and requests for this server
  endpoints: builder => ({
    // The `getPosts` endpoint is a "query" operation that returns data
    getSession: builder.query({
      // The URL for the request is '/fakeApi/posts'
      query: () => API_USER_SESSION_INFO
    }),
    getUIMenu: builder.query({
        query: () => API_UI_MENU_INFO
    })
  })
})

// Export the auto-generated hook for the `getPosts` query endpoint
export const { useGetSessionQuery, useGetUIMenuQuery } = apiSlice