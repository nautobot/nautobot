import { configureStore } from "@reduxjs/toolkit";
import { baseApi } from "@utils/api";
import {
    persistReducer,
    FLUSH,
    REHYDRATE,
    PAUSE,
    PERSIST,
    PURGE,
    REGISTER,
} from "redux-persist";
import storage from "redux-persist/lib/storage";
import { combineReducers } from "redux";

// Configure redux-persist to save state in Local Storage for performance
const persistConfig = {
    key: "root",
    version: 1,
    storage,
};

const rootReducer = combineReducers({
    [baseApi.reducerPath]: baseApi.reducer,
});

// Instantiate the persistent reducer to pull state from cache
const persistedReducer = persistReducer(persistConfig, rootReducer);

// Global Redux store for global state management
export const store = configureStore({
    reducer: persistedReducer,
    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware({
            serializableCheck: {
                ignoredActions: [
                    FLUSH,
                    REHYDRATE,
                    PAUSE,
                    PERSIST,
                    PURGE,
                    REGISTER,
                ],
            },
        }).concat(baseApi.middleware),
});

// TODO: This was a pattern to allow the dynamic store updates but doesn't seem to be working
// at the moment. Could just be a component issue.
// import dynamicMiddlewares from 'redux-dynamic-middlewares'
// import { addMiddleware } from 'redux-dynamic-middlewares'

// export const persistConfig = {
//   key: 'root',
//   version: 1,
//   storage,
// }

// export const rootReducer = combineReducers({
//   session: sessionReducer,
//   [apiSlice.reducerPath]: apiSlice.reducer,
// })

// export const persistedReducer = persistReducer(persistConfig, rootReducer)

// export const store = configureStore({
//   reducer: persistedReducer,
//   middleware: getDefaultMiddleware => getDefaultMiddleware({
//     serializableCheck: {
//       ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER],
//     },
//   }).concat(dynamicMiddlewares)
// });

// addMiddleware(apiSlice.middleware)
