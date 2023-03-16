import { configureStore, getDefaultMiddleware } from '@reduxjs/toolkit';
import sessionReducer from '@utils/session'
import { apiSlice } from '@utils/apiSlice'

export const store = configureStore({
  reducer: {
    session: sessionReducer,
    [apiSlice.reducerPath]: apiSlice.reducer,
  },
  middleware: getDefaultMiddleware => getDefaultMiddleware().concat(apiSlice.middleware)
});